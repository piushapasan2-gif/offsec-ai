"""
AI Engine — unified interface to 10+ LLM providers.
Each provider exposes .chat() and .stream() -> generator of str chunks.
"""
from __future__ import annotations
import json
import requests
from typing import List, Dict, Optional, Generator
from backend.config import Config


class ProviderError(Exception):
    pass


class BaseProvider:
    name: str = "base"
    default_model: str = ""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def chat(self, messages: List[Dict], model=None, temperature=0.7, max_tokens=2048) -> str:
        raise NotImplementedError

    def stream(self, messages: List[Dict], model=None, temperature=0.7, max_tokens=2048) -> Generator[str, None, None]:
        """Default: fall back to non-streaming (yield full response as one chunk)."""
        yield self.chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)


# ─────────────────────────────────────────────────────────────
#  OpenAI-compatible (OpenAI, Groq, DeepSeek, Together, xAI, OpenRouter, Perplexity, Mistral)
# ─────────────────────────────────────────────────────────────
class OpenAICompatProvider(BaseProvider):
    base_url: str = "https://api.openai.com/v1"
    extra_headers: Dict = {}

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }

    def chat(self, messages, model=None, temperature=0.7, max_tokens=2048):
        r = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json={"model": model or self.default_model, "messages": messages,
                  "temperature": temperature, "max_tokens": max_tokens},
            timeout=120,
        )
        if r.status_code >= 400:
            raise ProviderError(f"{self.name} {r.status_code}: {r.text[:200]}")
        return r.json()["choices"][0]["message"]["content"]

    def stream(self, messages, model=None, temperature=0.7, max_tokens=2048):
        r = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json={"model": model or self.default_model, "messages": messages,
                  "temperature": temperature, "max_tokens": max_tokens, "stream": True},
            stream=True, timeout=120,
        )
        if r.status_code >= 400:
            raise ProviderError(f"{self.name} {r.status_code}: {r.text[:200]}")
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith(b"data: "):
                data = line[6:]
                if data == b"[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    delta = obj["choices"][0]["delta"].get("content") or ""
                    if delta:
                        yield delta
                except Exception:
                    pass


class OpenAIProvider(OpenAICompatProvider):
    name = "openai"
    default_model = "gpt-4o-mini"

class DeepSeekProvider(OpenAICompatProvider):
    name = "deepseek"
    base_url = "https://api.deepseek.com/v1"
    default_model = "deepseek-chat"

class GroqProvider(OpenAICompatProvider):
    name = "groq"
    base_url = "https://api.groq.com/openai/v1"
    default_model = "llama-3.3-70b-versatile"

class TogetherProvider(OpenAICompatProvider):
    name = "together"
    base_url = "https://api.together.xyz/v1"
    default_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

class XAIProvider(OpenAICompatProvider):
    name = "xai"
    base_url = "https://api.x.ai/v1"
    default_model = "grok-2-latest"

class OpenRouterProvider(OpenAICompatProvider):
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"
    default_model = "anthropic/claude-3.5-sonnet"
    extra_headers = {"HTTP-Referer": "https://offsec-ai.local", "X-Title": "OffSec AI 2025"}

class PerplexityProvider(OpenAICompatProvider):
    name = "perplexity"
    base_url = "https://api.perplexity.ai"
    default_model = "llama-3.1-sonar-large-128k-online"

class MistralProvider(OpenAICompatProvider):
    name = "mistral"
    base_url = "https://api.mistral.ai/v1"
    default_model = "mistral-large-latest"


# ─────────────────────────────────────────────────────────────
#  Anthropic
# ─────────────────────────────────────────────────────────────
class AnthropicProvider(BaseProvider):
    name = "anthropic"
    default_model = "claude-3-5-sonnet-20241022"

    def _build_payload(self, messages, model, temperature, max_tokens):
        system_msg = None
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_msgs.append(m)
        payload = {
            "model": model or self.default_model,
            "messages": user_msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            payload["system"] = system_msg
        return payload

    def chat(self, messages, model=None, temperature=0.7, max_tokens=2048):
        payload = self._build_payload(messages, model, temperature, max_tokens)
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json=payload, timeout=120,
        )
        if r.status_code >= 400:
            raise ProviderError(f"anthropic {r.status_code}: {r.text[:200]}")
        return r.json()["content"][0]["text"]

    def stream(self, messages, model=None, temperature=0.7, max_tokens=2048):
        payload = self._build_payload(messages, model, temperature, max_tokens)
        payload["stream"] = True
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json=payload, stream=True, timeout=120,
        )
        if r.status_code >= 400:
            raise ProviderError(f"anthropic {r.status_code}: {r.text[:200]}")
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith(b"data: "):
                try:
                    obj = json.loads(line[6:])
                    if obj.get("type") == "content_block_delta":
                        text = obj.get("delta", {}).get("text", "")
                        if text:
                            yield text
                except Exception:
                    pass


# ─────────────────────────────────────────────────────────────
#  Google Gemini
# ─────────────────────────────────────────────────────────────
class GoogleProvider(BaseProvider):
    name = "google"
    default_model = "gemini-2.0-flash-exp"

    def _build_contents(self, messages):
        system_text = None
        contents = []
        for m in messages:
            if m["role"] == "system":
                system_text = m["content"]
                continue
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        return system_text, contents

    def chat(self, messages, model=None, temperature=0.7, max_tokens=2048):
        model_id = model or self.default_model
        system_text, contents = self._build_contents(messages)
        payload = {"contents": contents,
                   "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={self.api_key}",
            json=payload, timeout=120,
        )
        if r.status_code >= 400:
            raise ProviderError(f"google {r.status_code}: {r.text[:200]}")
        try:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise ProviderError(f"google: empty response")

    def stream(self, messages, model=None, temperature=0.7, max_tokens=2048):
        model_id = model or self.default_model
        system_text, contents = self._build_contents(messages)
        payload = {"contents": contents,
                   "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:streamGenerateContent?alt=sse&key={self.api_key}",
            json=payload, stream=True, timeout=120,
        )
        if r.status_code >= 400:
            raise ProviderError(f"google {r.status_code}: {r.text[:200]}")
        for line in r.iter_lines():
            if not line or not line.startswith(b"data: "):
                continue
            try:
                obj = json.loads(line[6:])
                text = obj["candidates"][0]["content"]["parts"][0]["text"]
                if text:
                    yield text
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────
#  Cohere
# ─────────────────────────────────────────────────────────────
class CohereProvider(BaseProvider):
    name = "cohere"
    default_model = "command-r-plus-08-2024"

    def chat(self, messages, model=None, temperature=0.7, max_tokens=2048):
        chat_history = []
        message = ""
        system = None
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            elif m == messages[-1] and m["role"] == "user":
                message = m["content"]
            else:
                role = "USER" if m["role"] == "user" else "CHATBOT"
                chat_history.append({"role": role, "message": m["content"]})
        payload = {"model": model or self.default_model, "message": message,
                   "chat_history": chat_history, "temperature": temperature, "max_tokens": max_tokens}
        if system:
            payload["preamble"] = system
        r = requests.post("https://api.cohere.ai/v1/chat",
                          headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                          json=payload, timeout=120)
        if r.status_code >= 400:
            raise ProviderError(f"cohere {r.status_code}: {r.text[:200]}")
        return r.json()["text"]


# ─────────────────────────────────────────────────────────────
#  HuggingFace
# ─────────────────────────────────────────────────────────────
class HuggingFaceProvider(BaseProvider):
    name = "huggingface"
    default_model = "meta-llama/Meta-Llama-3-8B-Instruct"

    def chat(self, messages, model=None, temperature=0.7, max_tokens=2048):
        model_id = model or self.default_model
        prompt = "".join(f"<|{m['role']}|>\n{m['content']}\n" for m in messages) + "<|assistant|>\n"
        r = requests.post(
            f"https://api-inference.huggingface.co/models/{model_id}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"inputs": prompt, "parameters": {"temperature": temperature, "max_new_tokens": max_tokens}},
            timeout=120,
        )
        if r.status_code >= 400:
            raise ProviderError(f"hf {r.status_code}: {r.text[:200]}")
        data = r.json()
        if isinstance(data, list) and data:
            return data[0].get("generated_text", "").split("<|assistant|>")[-1].strip()
        return str(data)


# ─────────────────────────────────────────────────────────────
#  Factory
# ─────────────────────────────────────────────────────────────
PROVIDER_CLASSES = {
    "openai":      OpenAIProvider,
    "anthropic":   AnthropicProvider,
    "google":      GoogleProvider,
    "groq":        GroqProvider,
    "deepseek":    DeepSeekProvider,
    "mistral":     MistralProvider,
    "openrouter":  OpenRouterProvider,
    "huggingface": HuggingFaceProvider,
    "together":    TogetherProvider,
    "cohere":      CohereProvider,
    "perplexity":  PerplexityProvider,
    "xai":         XAIProvider,
}

def build_providers():
    return {name: PROVIDER_CLASSES[name](key)
            for name, key in Config.LLM_KEYS.items()
            if key and name in PROVIDER_CLASSES}

PROVIDERS: Dict[str, BaseProvider] = build_providers()
