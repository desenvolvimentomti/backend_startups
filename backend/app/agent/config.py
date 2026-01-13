"""
Agent configuration and settings.
Manages OpenAI API keys and agent parameters.
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    openai_api_key: str = ""
    agent_model: str = "gpt-4o"
    agent_temperature: float = 0.1  # Low for accuracy
    agent_max_tokens: int = 4096
    search_result_limit: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_agent_settings() -> AgentSettings:
    return AgentSettings()
