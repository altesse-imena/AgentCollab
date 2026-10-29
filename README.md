# AgentCollab

A multi-agent coding assistant. Specialized AI agents (CodeWriter, CodeReviewer, TestGenerator and SecurityAnalyzer) work together on software tasks, orchestrated with LangGraph.

> **Status: week 1 of 6.** CodeWriter works on its own from the command line. Every model call is logged with its token counts and cost.

## Architecture (target)

```
Intake ─► ContextGatherer ─► CodeWriter ─┬─► TestGenerator ──┐
                                         ├─► CodeReviewer ───┼─► TestRunner ─► Judge ─► Finalize
                                         └─► SecurityAnalyzer┘    (sandbox)      │
                    ◄──── feedback to CodeWriter (max 3 rounds) ◄─── fail ───────┘
```

## Quick start

```bash
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp .env.example .env            # pick a provider and add its API key
.venv/bin/agentcollab run "Add a function that reverses a string" --repo ../path/to/repo
.venv/bin/agentcollab run "..." --repo ../path/to/repo --apply   # write the changes
.venv/bin/pytest -q             # tests use a fake model and cost nothing
```

### Switching model providers

Set `AGENTCOLLAB_PROVIDER` in `backend/.env`. No code changes are needed.

| Provider | Setting | Key |
|---|---|---|
| OpenAI (default) | `openai` | `OPENAI_API_KEY` |
| Anthropic Claude | `anthropic` | `ANTHROPIC_API_KEY` |
| Any OpenAI-compatible API (OpenRouter, Groq, Together, Ollama...) | `openai_compatible` + `AGENTCOLLAB_BASE_URL` | `AGENTCOLLAB_API_KEY` |

Each agent can use its own model (`AGENTCOLLAB_MODEL_WRITER`, `..._REVIEWER`, `..._TESTER`, `..._SECURITY`). Adding a provider means writing one adapter in `backend/agentcollab/llm/providers/`. Add the model's prices to `llm/pricing.py` so costs are tracked.

SQLite is used by default. To use Postgres, run `docker compose up -d db` and set `DATABASE_URL` in `.env`.

API server: `.venv/bin/uvicorn agentcollab.main:create_app --factory --reload`.

## Layout

| Path | Purpose |
|---|---|
| `backend/agentcollab/llm/` | The only code that calls a model: retries, JSON validation with one repair attempt, per-run budget, cost logging |
| `backend/agentcollab/agents/` | Agents and their prompts |
| `backend/agentcollab/repo/` | Reading repo files, safe paths, diffs |
| `backend/agentcollab/db/` | `runs` and `llm_calls` tables |
| `evals/tasks/` | Benchmark tasks (week 3) |

## Roadmap

1. ✅ Setup, LLM client with cost logging, CodeWriter from the command line
2. All four agents, LangGraph workflow, sandboxed test runs, feedback rounds
3. Failure handling, saved progress, benchmark, baseline costs
4. Cost optimizations (measured against the baseline), live event streaming
5. React UI: live agent graph, timeline, diff viewer, cost meter
6. GitHub App, deployment, replay mode
