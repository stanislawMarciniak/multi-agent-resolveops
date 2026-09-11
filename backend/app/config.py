from functools import lru_cache
from pathlib import Path

from pydantic import (
    Field,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "ResolveOps AI"
    environment: str = "development"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    frontend_origin: str = (
        "http://localhost:5173"
    )

    def cors_allow_origins(self) -> list[str]:
        """Expand FRONTEND_ORIGIN for local Vite (localhost vs 127.0.0.1)."""
        configured = [
            origin.strip()
            for origin in self.frontend_origin.split(",")
            if origin.strip()
        ]

        origins = set(configured)

        for origin in list(origins):
            if "://localhost" in origin:
                origins.add(
                    origin.replace(
                        "://localhost",
                        "://127.0.0.1",
                        1,
                    )
                )
            if "://127.0.0.1" in origin:
                origins.add(
                    origin.replace(
                        "://127.0.0.1",
                        "://localhost",
                        1,
                    )
                )

        if self.environment == "development":
            origins.update(
                {
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "http://localhost:4173",
                    "http://127.0.0.1:4173",
                }
            )

        return sorted(origins)

    database_url: str = (
        "sqlite:///./data/app.db"
    )

    crm_base_url: str = (
        "http://localhost:8101"
    )

    billing_base_url: str = (
        "http://localhost:8102"
    )

    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8200
    mcp_server_url: str = (
        "http://127.0.0.1:8200/mcp"
    )

    investigation_max_llm_calls: int = Field(
        default=8,
        ge=1,
        le=30,
    )

    investigator_max_tool_calls: int = Field(
        default=8,
        ge=1,
        le=30,
    )

    google_api_key: str

    embedding_model: str = (
    "gemini-embedding-2"
    )

    embedding_dimensions: int = 768

    policy_documents_dir: Path = Path(
        "documents/policies"
    )

    policy_index_path: Path = Path(
        "data/policy_index.json"
    )

    policy_search_top_k: int = 3

     # ADK / Gemini
    adk_app_name: str = "resolveops-ai"

    adk_model: str = "gemini-3.6-flash"

    model_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
    )

    model_timeout_ms: int = Field(
        default=30_000,
        gt=0,
    )

    model_retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
    )

    max_llm_calls_per_run: int = Field(
        default=5,
        ge=1,
        le=50,
    )

    planner_max_llm_calls: int = Field(
        default=2,
        ge=1,
        le=10,
    )

    reviewer_max_llm_calls: int = Field(
        default=2,
        ge=1,
        le=10,
    )

    max_plan_revisions: int = Field(
        default=1,
        ge=0,
        le=3,
    )

    google_oauth_client_id: str = ""

    operator_emails: str = ""

    otel_enabled: bool = True

    otel_service_name: str = (
        "resolveops-backend"
    )

    otel_exporter_otlp_endpoint: str = ""

    otel_console_exporter: bool = False

    model_input_cost_per_million: float = Field(
        default=1.50,
        ge=0.0,
    )

    model_output_cost_per_million: float = Field(
        default=7.50,
        ge=0.0,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings() # pyright: ignore[reportCallIssue]