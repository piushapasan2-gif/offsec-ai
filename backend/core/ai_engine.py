"""
AI Engine — unified interface to 10+ LLM providers.

Each provider is a thin adapter exposing .chat(messages, **kwargs) -> str.
Failures are caught and surfaced so the router can fail over.
"""
from __future__ import annotations
import json
import requests
from typing import List, Dict, Optional
from backend.config import Config


class ProviderError(Exception):
    pass


# ─────────────────────────────────────────────────────────────
#  Base
# ─────────────────────────────────────────────────────────────
class BaseProvider:
    name: str = "base"
    default_model: str = ""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def chat(self, messages: List[Dict], model: Optional[str] = None,
             temperature: float = 0.7, max_tokens: int = 2048) -> str:
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────
#  OpenAI (works for OpenAI, DeepSeek, Groq, Together, xAI, OpenRouter — OpenAI-compatible)
# ─────────────────────────────────────────────────────────────
class OpenAICompatProvider(BaseProvider):
    base_url: str = "https://api.openai.com/v1"
    extra_headers: Dict = {}

    def chat(self, messages, model=None, temperature=0.7, max_tokens=2048):
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        if r.status_code >= 400:
            raise ProviderError(f"{self.name} {r.status_code}: {r.text[:200]}")
        data = r.json()
        return data["choices"][0]["message"]["content"]


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


# ─────────────────────────────────────────────────────────────
#  Anthropic (different API shape)
# ─────────────────────────────────────────────────────────────
class AnthropicProvider(BaseProvider):
    name = "anthropic"
    default_model = "claude-3-5-sonnet-20241022"

    def chat(self, messages, model=None, temperature=0.7, max_tokens=2048):
        system_msg = None
        user_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                user_msgs.append(m)
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or self.default_model,
            "messages": user_msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msg:
            payload["system"] = system_msg
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        if r.status_code >= 400:
            raise ProviderError(f"anthropic {r.status_code}: {r.text[:200]}")
        return r.json()["content"][0]["text"]


# ─────────────────────────────────────────────────────────────
#  Google Gemini
# ─────────────────────────────────────────────────────────────
class GoogleProvider(BaseProvider):
    name = "google"
    default_model = "gemini-2.0-flash-exp"

    def chat(self, messages, model=None, temperature=0.7, max_tokens=2048):
        model_id = model or self.default_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={self.api_key}"
        # Gemini uses parts/contents; system goes in systemInstruction
        system_text = None
        contents = []
        for m in messages:
            if m["role"] == "system":
                system_text = m["content"]
                continue
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        r = requests.post(url, json=payload, timeout=120)
        if r.status_code >= 400:
            raise ProviderError(f"google {r.status_code}: {r.text[:200]}")
        data = r.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise ProviderError(f"google: empty response {data}")


# ─────────────────────────────────────────────────────────────
#  Mistral
# ─────────────────────────────────────────────────────────────
class MistralProvider(OpenAICompatProvider):
    name = "mistral"
    base_url = "https://api.mistral.ai/v1"
    default_model = "mistral-large-latest"


# ─────────────────────────────────────────────────────────────
#  Cohere
# ─────────────────────────────────────────────────────────────
class CohereProvider(BaseProvider):
    name = "cohere"
    default_model = "command-r-plus-08-2024"

    def chat(self, messages, model=None, temperature=0.7, max_tokens=2048):
        # Cohere chat: separate message + chat_history
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
        url = "https://api.cohere.ai/v1/chat"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model or self.default_model,
            "message": message,
            "chat_history": chat_history,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            payload["preamble"] = system
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        if r.status_code >= 400:
            raise ProviderError(f"cohere {r.status_code}: {r.text[:200]}")
        return r.json()["text"]


# ─────────────────────────────────────────────────────────────
#  HuggingFace Inference API (uses any text-generation model)
# ─────────────────────────────────────────────────────────────
class HuggingFaceProvider(BaseProvider):
    name = "huggingface"
    default_model = "meta-llama/Meta-Llama-3-8B-Instruct"

    def chat(self, messages, model=None, temperature=0.7, max_tokens=2048):
        model_id = model or self.default_model
        url = f"https://api-inference.huggingface.co/models/{model_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        # Concat messages into prompt
        prompt = ""
        for m in messages:
            prompt += f"<|{m['role']}|>\n{m['content']}\n"
        prompt += "<|assistant|>\n"
        payload = {"inputs": prompt, "parameters": {"temperature": temperature, "max_new_tokens": max_tokens}}
        r = requests.post(url, headers=headers, json=payload, timeout=120)
        if r.status_code >= 400:
            raise ProviderError(f"hf {r.status_code}: {r.text[:200]}")
        data = r.json()
        if isinstance(data, list) and data:
            return data[0].get("generated_text", "").split("<|assistant|>")[-1].strip()
        return str(data)


# ─────────────────────────────────────────────────────────────
#  Engine factory
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


def build_providers() -> Dict[str, BaseProvider]:
    """Instantiate one provider per configured API key."""
    providers = {}
    for name, key in Config.LLM_KEYS.items():
        if key and name in PROVIDER_CLASSES:
            providers[name] = PROVIDER_CLASSES[name](key)
    return providers


# Singleton
PROVIDERS: Dict[str, BaseProvider] = build_providers()
