from __future__ import annotations

from abc import ABC, abstractmethod

import aiohttp


class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, prompt: str) -> str:
        raise NotImplementedError


class LocalOllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434/api/generate", model: str = "qwen:latest") -> None:
        self.base_url = base_url
        self.model = model

    async def generate_response(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    response.raise_for_status()
                    body = await response.json()
        except (aiohttp.ClientError, TimeoutError) as error:
            raise RuntimeError(f"LLM request failed for {self.base_url}: {error}") from error
        return str(body.get("response", "")).strip()
