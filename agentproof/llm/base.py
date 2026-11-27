"""The interface every model backend implements.

The agent depends only on LLMClient, so switching from Ollama to another
provider means writing one new class, with no change to the agent loop.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMError(Exception):
    """The model could not be reached or returned something unusable."""


@dataclass(frozen=True)
class LLMReply:
    text: str
    tokens: int = 0


class LLMClient(ABC):
    @abstractmethod
    def chat(self, messages: list[dict]) -> LLMReply:
        """Send the whole conversation and return the model's next message.

        The reply text is expected to be one JSON object (one agent action).
        """
