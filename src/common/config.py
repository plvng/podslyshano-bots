from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import BeforeValidator, Field, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _parse_admins(value: Any) -> list[int]:
    if value is None or value == "":
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, list):
        return [int(item) for item in value]
    if isinstance(value, str):
        return [int(item.strip()) for item in value.split(",") if item.strip()]
    raise ValueError(f"Invalid ADMINS value: {value}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    proposal_bot_token: str = Field(alias="PROPOSAL_BOT_TOKEN")
    chat_bot_token: str = Field(alias="CHAT_BOT_TOKEN")
    tgk: str = Field(alias="TGK")
    admins: Annotated[list[int], BeforeValidator(_parse_admins), NoDecode] = Field(
        default_factory=list,
        alias="ADMINS",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    database_path: str = Field(default="/data/bots.db", alias="DATABASE_PATH")
    msk_offset: int = Field(default=3, alias="MSK_OFFSET")
    config_path: str = Field(default="config.yaml", alias="CONFIG_PATH")
    block_message: str | None = Field(default=None, alias="BLOCK_MESSAGE")
    start_message: str | None = Field(default=None, alias="START_MESSAGE")
    admin_web_url: str = Field(default="http://127.0.0.1:8080", alias="ADMIN_WEB_URL")

    @model_validator(mode="after")
    def apply_platform_defaults(self) -> "Settings":
        domain = os.getenv("DOMAIN", "").strip()
        if domain and self.admin_web_url in ("http://127.0.0.1:8080", ""):
            self.admin_web_url = f"https://{domain.rstrip('/')}"

        if Path("/app/data").is_dir() and self.database_path == "/data/bots.db":
            self.database_path = "/app/data/bots.db"

        if Path("/app/data").is_dir() and self.redis_url == "redis://redis:6379/0":
            self.redis_url = "redis://127.0.0.1:6379/0"

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_yaml_config() -> dict[str, Any]:
    settings = get_settings()
    config_path = Path(settings.config_path)
    if not config_path.is_absolute():
        for candidate in (Path.cwd() / config_path, Path(__file__).resolve().parents[2] / config_path):
            if candidate.exists():
                config_path = candidate
                break

    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def get_config_value(*keys: str, default: Any = None) -> Any:
    data: Any = get_yaml_config()
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return default
        data = data[key]
    return data


def get_block_message() -> str:
    settings = get_settings()
    return settings.block_message or get_config_value("block_message", default="Ты заблокирован.")


def get_start_message() -> str:
    settings = get_settings()
    return settings.start_message or get_config_value(
        "start_message",
        default="Выбери режим кнопкой ниже. Обычное сообщение публикуется в канал анонимно.",
    )


def get_keywords() -> list[str]:
    return list(get_config_value("keywords", default=[]))


def get_badwords() -> list[str]:
    return list(get_config_value("badwords", default=[]))


def get_emoji(mood: str) -> list[str]:
    return list(get_config_value("emoji", mood, default=[]))


def get_effects(mood: str) -> list[str]:
    return list(get_config_value("effect", mood, default=[]))


def get_chat_message(key: str, default: str = "") -> str:
    settings = get_settings()
    template = get_config_value("chat", key, default=default)
    return template.replace("{TGK}", settings.tgk)


def get_rate_limit_seconds() -> int:
    return int(get_config_value("proposal", "rate_limit_seconds", default=30))
