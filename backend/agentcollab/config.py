from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

ROLES = ("writer", "reviewer", "tester", "security")

# Default model per provider. Override any role with AGENTCOLLAB_MODEL_<ROLE>.
DEFAULT_MODELS = {
    "openai": "gpt-4.1",
    "anthropic": "claude-opus-5-5",
    "openai_compatible": None,  # no sensible default; set AGENTCOLLAB_MODEL
}
# Cheaper model for roles listed in AGENTCOLLAB_LIGHT_ROLES
DEFAULT_LIGHT_MODELS = {
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-sonnet-5-5",
    "openai_compatible": None,  # set AGENTCOLLAB_LIGHT_MODEL
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agentcollab_provider: str = "openai"
    agentcollab_base_url: str | None = None  # for openai_compatible
    agentcollab_model: str | None = None  # default model for every role
    agentcollab_model_writer: str | None = None
    agentcollab_model_reviewer: str | None = None
    agentcollab_model_tester: str | None = None
    agentcollab_model_security: str | None = None

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    agentcollab_api_key: str | None = None  # for openai_compatible

    # Cost optimizations; each can be switched off to measure it against a baseline
    agentcollab_response_cache: bool = False
    agentcollab_light_roles: str = ""  # e.g. "reviewer,security"
    agentcollab_light_model: str | None = None
    agentcollab_context_limit_chars: int = 200_000  # max repo text sent to each agent

    # API server
    agentcollab_allow_local_repos: bool = False  # let POST /api/runs use any path on this machine
    agentcollab_max_concurrent_runs: int = 2

    agentcollab_public_url: str | None = None  # used for links in GitHub comments
    agentcollab_static_dir: str | None = None  # built frontend to serve at /
    agentcollab_seed_file: str | None = None  # exported runs to import at startup

    # Limits for a public demo (0 means unlimited)
    agentcollab_live_runs: bool = True  # false = replays only, no model calls from visitors
    agentcollab_runs_per_ip_per_day: int = 0
    agentcollab_daily_budget_usd: float = 0.0
    agentcollab_trust_proxy: bool = False  # read the client IP from X-Forwarded-For

    # GitHub App (see docs/github-app.md)
    github_app_id: str | None = None
    github_app_private_key: str | None = None  # PEM contents; "\n" escapes are allowed
    github_webhook_secret: str | None = None
    agentcollab_github_label: str = "agentcollab"

    database_url: str = "sqlite:///./agentcollab.db"
    agentcollab_run_budget_usd: float = 0.50

    @property
    def api_key(self) -> str | None:
        return {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "openai_compatible": self.agentcollab_api_key,
        }.get(self.agentcollab_provider)

    @property
    def github_enabled(self) -> bool:
        return bool(
            self.github_app_id and self.github_app_private_key and self.github_webhook_secret
        )

    @property
    def github_private_key_pem(self) -> str:
        return (self.github_app_private_key or "").replace("\\n", "\n")

    @property
    def light_roles(self) -> set[str]:
        roles = {r.strip() for r in self.agentcollab_light_roles.split(",") if r.strip()}
        if unknown := roles - set(ROLES):
            raise ValueError(f"unknown roles in AGENTCOLLAB_LIGHT_ROLES: {sorted(unknown)}")
        return roles

    def model_for(self, role: str) -> str:
        """Role override, then the light model for light roles, then the global default."""
        light = None
        if role in self.light_roles:
            light = self.agentcollab_light_model or DEFAULT_LIGHT_MODELS.get(
                self.agentcollab_provider
            )
        model = (
            getattr(self, f"agentcollab_model_{role}")
            or light
            or self.agentcollab_model
            or DEFAULT_MODELS.get(self.agentcollab_provider)
        )
        if not model:
            raise ValueError(f"no model configured for {role}; set AGENTCOLLAB_MODEL")
        return model


@lru_cache
def get_settings() -> Settings:
    return Settings()
