"""
Anti-Gravity Backend — Configuration
Reads settings from environment variables (with sensible dev defaults).
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App & Security
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./anti_gravity.db"

    # Game rules
    STARTING_BALANCE: int = 10_000
    MIN_BET: int = 10
    MAX_BET: int = 5_000

    # Game loop timing (all in seconds) — configurable without code changes
    GAME_LOOP_TICK_INTERVAL: float = 0.05    # Multiplier broadcast interval during running phase
    GAME_LOOP_WAITING_DURATION: float = 3.0  # Betting/waiting phase duration before round starts
    GAME_LOOP_ENDED_DURATION: float = 2.0    # Post-crash pause before next round

    # Rate Limiting (per IP / user)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 20
    RATE_LIMIT_REGISTER_PER_MINUTE: int = 15
    RATE_LIMIT_CASHOUT_PER_MINUTE: int = 60
    RATE_LIMIT_FAIRNESS_PER_MINUTE: int = 120
    RATE_LIMIT_WS_CONNECT_PER_MINUTE: int = 30
    RATE_LIMIT_WS_MESSAGES_PER_MINUTE: int = 120


settings = Settings()

