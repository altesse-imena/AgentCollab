"""The only place that calls a model.

Handles retries, output validation, per-run budgets and cost logging.
"""

import hashlib
import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .pricing import cost_usd
from .providers import ChatProvider, ProviderResponse, TransientProviderError

_FENCE = re.compile(r"^```(?:json)?\s*\n(.*)\n```\s*$", re.DOTALL)


def parse_json(text: str):
    """Parse a JSON reply, tolerating a surrounding ```json fence."""
    text = text.strip()
    match = _FENCE.match(text)
    return json.loads(match.group(1) if match else text)


class BudgetExceeded(Exception):
    pass


class InvalidModelOutput(Exception):
    pass


@dataclass
class RunBudget:
    """Tracks spend for one run and stops new calls once the limit is reached."""

    run_id: str
    limit_usd: float
    spent_usd: float = 0.0

    def check(self) -> None:
        if self.spent_usd >= self.limit_usd:
            raise BudgetExceeded(
                f"run {self.run_id} spent ${self.spent_usd:.4f} of ${self.limit_usd:.2f}"
            )


@dataclass
class CallRecord:
    run_id: str
    agent: str
    model: str
    prompt_tokens: int
    cached_tokens: int
    completion_tokens: int
    cost_usd: float | None
    latency_ms: int
    attempt: int
    cache_hit: bool = False


class ResponseCache(Protocol):
    """Stores validated replies by request, so an identical request is answered for free."""

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, model: str, text: str) -> None: ...


def cache_key(model: str, messages: list[dict]) -> str:
    payload = json.dumps({"model": model, "messages": messages}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass
class LLMResult[T: BaseModel]:
    output: T
    calls: list[CallRecord] = field(default_factory=list)


Recorder = Callable[[CallRecord], None]


class LLMClient:
    def __init__(
        self,
        provider: ChatProvider,
        recorder: Recorder | None = None,
        max_attempts: int = 4,
        wait_max_s: float = 20.0,
        cache: ResponseCache | None = None,
    ):
        self._provider = provider
        self._record = recorder or (lambda _: None)
        self._cache = cache
        # wait_max_s=0 disables the backoff wait (used by tests)
        self._chat = retry(
            retry=retry_if_exception_type(TransientProviderError),
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, max=wait_max_s),
            reraise=True,
        )(self._provider.chat)

    def structured[T: BaseModel](
        self,
        *,
        agent: str,
        model: str,
        messages: list[dict],
        schema: type[T],
        budget: RunBudget,
    ) -> LLMResult[T]:
        """Ask for JSON matching `schema`. A malformed reply gets one repair attempt."""
        calls: list[CallRecord] = []
        key = cache_key(model, messages) if self._cache else None
        if key and (cached := self._from_cache(key, schema, agent, model, budget, calls)):
            return cached
        convo = list(messages)
        for attempt in (1, 2):
            resp = self._call(agent, model, convo, budget, attempt, calls)
            try:
                output = schema.model_validate(parse_json(resp.text))
            except (json.JSONDecodeError, ValidationError) as e:
                if attempt == 2:
                    raise InvalidModelOutput(f"{agent} returned invalid output twice: {e}") from e
                convo += [
                    {"role": "assistant", "content": resp.text},
                    {
                        "role": "user",
                        "content": "That reply was not valid JSON for the required schema. "
                        f"Error: {e}\nReply again with only the corrected JSON object.",
                    },
                ]
                continue
            if key:
                self._cache.set(key, model, resp.text)
            return LLMResult(output=output, calls=calls)
        raise AssertionError("unreachable")

    def _from_cache[T: BaseModel](
        self, key: str, schema: type[T], agent: str, model: str, budget: RunBudget, calls: list
    ) -> LLMResult[T] | None:
        text = self._cache.get(key)
        if text is None:
            return None
        try:
            output = schema.model_validate(parse_json(text))
        except (json.JSONDecodeError, ValidationError):
            return None  # schema changed since it was cached; ask the model again
        record = CallRecord(budget.run_id, agent, model, 0, 0, 0, 0.0, 0, 1, cache_hit=True)
        calls.append(record)
        self._record(record)
        return LLMResult(output=output, calls=calls)

    def _call(
        self,
        agent: str,
        model: str,
        messages: list[dict],
        budget: RunBudget,
        attempt: int,
        calls: list[CallRecord],
    ) -> ProviderResponse:
        budget.check()
        start = time.perf_counter()
        resp = self._chat(model, messages, True)
        served = resp.model or model
        cost = cost_usd(
            served,
            resp.prompt_tokens,
            resp.cached_tokens,
            resp.completion_tokens,
            resp.cache_write_tokens,
        )
        budget.spent_usd += cost or 0.0
        record = CallRecord(
            run_id=budget.run_id,
            agent=agent,
            model=served,
            prompt_tokens=resp.prompt_tokens,
            cached_tokens=resp.cached_tokens,
            completion_tokens=resp.completion_tokens,
            cost_usd=cost,
            latency_ms=int((time.perf_counter() - start) * 1000),
            attempt=attempt,
        )
        calls.append(record)
        self._record(record)
        return resp
