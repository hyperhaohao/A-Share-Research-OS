"""LLMProvider — OpenAI-compatible access layer (整改 R3.1/R3.2).

Boundary rules (Evidence First, LLM Reasoning Second — 整改 §16):

  - the LLM layer produces *narrative* (answers, explanations, report prose);
  - it NEVER creates Evidence, Claims, Theses, prices, announcements or
    sources — those exist only in the domain;
  - every LLM call receives the frozen context (evidence ids / claims /
    theses) and every answer carries the citations it was given; the caller
    validates that the answer's citations stay within the provided context.

Provider selection: ``get_llm_provider()`` returns an OpenAI-compatible
client when ``ASRO_LLM_API_KEY`` is configured, else ``None`` — callers must
keep working without an LLM (deterministic baseline).
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from typing import Any, Iterator

import httpx

from app.config import get_settings


class LLMNotConfigured(RuntimeError):
    """Raised when an LLM call is attempted without a configured provider."""


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0

    def as_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "calls": self.calls,
        }


class BaseLLMProvider:
    def generate_text(self, prompt: str, *, system: str | None = None,
                      temperature: float = 0.2) -> str:
        raise NotImplementedError

    def generate_structured(self, prompt: str, *, schema_hint: str,
                            system: str | None = None) -> dict:
        raw = self.generate_text(prompt, system=system)
        try:
            parsed = json.loads(raw)
        except ValueError:
            # tolerate fenced JSON
            stripped = raw.strip().removeprefix("```json").removeprefix("```")
            stripped = stripped.removesuffix("```").strip()
            parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError("structured output must be a JSON object")
        return parsed

    def stream(self, prompt: str, *, system: str | None = None) -> Iterator[str]:
        yield self.generate_text(prompt, system=system)

    def model_info(self) -> dict:
        raise NotImplementedError

    def usage(self) -> dict:
        raise NotImplementedError


class OpenAICompatibleProvider(BaseLLMProvider):
    """Speaks /chat/completions — works with OpenAI, DeepSeek, GLM, Qwen,
    Doubao and any compatible gateway (NewAPI / one-api)."""

    def __init__(self, *, base_url: str, api_key: str, model: str,
                 timeout: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._usage = LLMUsage()
        self._lock = threading.Lock()

    def model_info(self) -> dict:
        return {
            "kind": "openai_compatible",
            "base_url": self._base_url,
            "model": self._model,
        }

    def usage(self) -> dict:
        return self._usage.as_dict()

    def _post_chat(self, payload: dict) -> dict:
        resp = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=self._timeout,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"llm_http_{resp.status_code}")
        return resp.json()

    def _record(self, body: dict) -> None:
        usage = body.get("usage") or {}
        with self._lock:
            self._usage.prompt_tokens += int(usage.get("prompt_tokens") or 0)
            self._usage.completion_tokens += int(usage.get("completion_tokens") or 0)
            self._usage.calls += 1

    def generate_text(self, prompt: str, *, system: str | None = None,
                      temperature: float = 0.2) -> str:
        messages = [{"role": "system", "content": system or "You are a research assistant."}]
        messages.append({"role": "user", "content": prompt})
        body = self._post_chat({
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        })
        self._record(body)
        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("llm_empty_response")
        return choices[0]["message"]["content"] or ""

    def generate_structured(self, prompt: str, *, schema_hint: str,
                            system: str | None = None) -> dict:
        messages = [{
            "role": "system",
            "content": (system or "You are a research assistant.")
            + " Respond with a single JSON object only.",
        }]
        messages.append({"role": "user", "content": f"{prompt}\n\nJSON schema hint:\n{schema_hint}"})
        body = self._post_chat({
            "model": self._model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        })
        self._record(body)
        content = (body.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        return json.loads(content)

    def stream(self, prompt: str, *, system: str | None = None) -> Iterator[str]:
        messages = [{"role": "system", "content": system or "You are a research assistant."}]
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
        }
        with httpx.stream(
            "POST",
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
            timeout=self._timeout,
        ) as resp:
            for line in resp.iter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = line[len("data:"):].strip()
                if chunk == "[DONE]":
                    break
                try:
                    delta = json.loads(chunk)["choices"][0]["delta"]
                    piece = delta.get("content") or ""
                except (ValueError, KeyError, IndexError):
                    continue
                if piece:
                    yield piece


class DeterministicStubProvider(BaseLLMProvider):
    """Offline deterministic provider for tests and LLM-less deployments.

    Summarizes the supplied context verbatim — it never invents content, so
    boundary rules can be tested without network.
    """

    def __init__(self) -> None:
        self._usage = LLMUsage()

    def model_info(self) -> dict:
        return {"kind": "deterministic_stub", "model": "stub-1"}

    def usage(self) -> dict:
        return self._usage.as_dict()

    def generate_text(self, prompt: str, *, system: str | None = None,
                      temperature: float = 0.2) -> str:
        with self._lock_guard():
            self._usage.calls += 1
        return f"[stub] {prompt[:400]}"

    def _lock_guard(self):
        import contextlib
        return contextlib.nullcontext()


def llm_configured() -> bool:
    import os

    return bool(os.environ.get("ASRO_LLM_API_KEY"))


def get_llm_provider() -> BaseLLMProvider | None:
    """Return the configured provider, or None when unconfigured.

    Callers must keep the deterministic baseline working without an LLM.
    """
    import os

    api_key = os.environ.get("ASRO_LLM_API_KEY")
    if not api_key:
        return None
    settings = get_settings()
    base_url = os.environ.get("ASRO_LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("ASRO_LLM_MODEL", "gpt-4o-mini")
    return OpenAICompatibleProvider(
        base_url=base_url, api_key=api_key, model=model
    )
