"""A fake LLMClient that replays prepared replies.

Used by the automated tests and by `--model scripted` demos, so the whole
benchmark can run without a real model.
"""
from __future__ import annotations

import json

from .base import LLMClient, LLMReply


class ScriptedClient(LLMClient):
    def __init__(self, replies: list, tokens_per_reply: int = 10):
        """replies: dicts (sent as JSON) or raw strings (sent as they are).

        After the last reply, the last one is repeated, which simulates an
        agent that is stuck in a loop.
        """
        if not replies:
            raise ValueError("ScriptedClient needs at least one reply")
        self._replies = [r if isinstance(r, str) else json.dumps(r) for r in replies]
        self._tokens = tokens_per_reply
        self.calls: list[list[dict]] = []

    def chat(self, messages: list[dict]) -> LLMReply:
        index = min(len(self.calls), len(self._replies) - 1)
        self.calls.append(list(messages))
        return LLMReply(text=self._replies[index], tokens=self._tokens)
