from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_int_list(value: str | list[int]) -> list[int]:
    if isinstance(value, list):
        return [int(item) for item in value]
    return [int(item.strip()) for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    proposal_bot_token: str = Field(alias="PROPOSAL_BOT_TOKEN")
    chat_bot_token: str = Field(alias="CHAT_BOT_TOKEN")
    tgk: str = Field(alias="TGK")
    admins: list[int] = Field(default_factory=list, alias="ADMINS")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    database_path: str = Field(default="/data/bots.db", alias="DATABASE_PATH")
    msk_offset: int = Field(default=3, alias="MSK_OFFSET")
    config_path: str = Field(default="config.yaml", alias="CONFIG_PATH")
    block_message: str | None = Field(default=None, alias="BLOCK_MESSAGE")
    start_message: str | None = Field(default=None, alias="START_MESSAGE")

    @field_validator("admins", mode="before")
    @classmethod
    def parse_admins(cls, value: Any) -> list[int]:
        if value is None or value == "":
            return []
        return _parse_int_list(value)


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
        default="Отправь сообщение — опубликуем его анонимно в канале.",
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
