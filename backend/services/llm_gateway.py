from __future__ import annotations

from abc import ABC, abstractmethod

import aiohttp


class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str) -> str:
        raise NotImplementedError


class LocalOllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434/api/generate", model: str = "qwen2.5") -> None:
        self.base_url = base_url
        self.model = model

    async def generate_response(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, json=payload, timeout=60) as response:
                response.raise_for_status()
                body = await response.json()
        return str(body.get("response", "")).strip()
