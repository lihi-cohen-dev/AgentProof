"""LLMClient for a model served locally by Ollama (https://ollama.com)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import LLMClient, LLMError, LLMReply

DEFAULT_URL = "http://localhost:11434/api/chat"


class OllamaClient(LLMClient):
    def __init__(self, model: str, url: str = DEFAULT_URL, timeout: float = 600):
        self.model = model
        self.url = url
        self.timeout = timeout

    def chat(self, messages: list[dict]) -> LLMReply:
        payload = {"model": self.model, "messages": messages, "stream": False, "format": "json"}
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read())
        except urllib.error.HTTPError as error:
            raise LLMError(f"Ollama answered with HTTP {error.code}. Is the model '{self.model}' pulled?") from error
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            raise LLMError(f"Could not reach Ollama at {self.url}. Is Ollama running?") from error
        except json.JSONDecodeError as error:
            raise LLMError("Ollama returned a response that is not JSON.") from error

        try:
            text = body["message"]["content"]
        except (KeyError, TypeError) as error:
            raise LLMError(f"Unexpected response from Ollama: {str(body)[:200]}") from error
        return LLMReply(text=text, tokens=int(body.get("eval_count", 0)))
