"""Small, typed image-provider boundary.

Providers return bytes and never write files; the API owns durable asset storage.
"""

from __future__ import annotations

import base64
from typing import Protocol

import httpx


class ImageProvider(Protocol):
    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes: ...


class OpenAICompatibleImageProvider:
    def __init__(self, endpoint: str, api_key: str | None = None, model: str = "dall-e-3"):
        self.endpoint, self.api_key, self.model = endpoint.rstrip("/"), api_key, model

    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.endpoint}/images/generations",
                headers=headers,
                json={
                    "prompt": prompt,
                    "size": size,
                    "model": self.model,
                    "response_format": "b64_json",
                },
            )
            response.raise_for_status()
            item = response.json()["data"][0]
            if item.get("b64_json"):
                return base64.b64decode(item["b64_json"])
            image = await client.get(item["url"])
            image.raise_for_status()
            return image.content


class A1111ImageProvider:
    def __init__(self, endpoint: str = "http://127.0.0.1:7860"):
        self.endpoint = endpoint.rstrip("/")

    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        width, height = (int(value) for value in size.split("x", 1))
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{self.endpoint}/sdapi/v1/txt2img",
                json={"prompt": prompt, "width": width, "height": height, "steps": 20},
            )
            response.raise_for_status()
            return base64.b64decode(response.json()["images"][0])


class ComfyUIProvider:
    """Adapter hook for ComfyUI deployments exposing an OpenAI-compatible endpoint."""

    def __init__(self, endpoint: str):
        self._delegate = OpenAICompatibleImageProvider(endpoint)

    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        return await self._delegate.generate(prompt, size)


class StockImageProvider:
    def __init__(self, endpoint: str, api_key: str, provider: str = "unsplash"):
        self.endpoint, self.api_key, self.provider = endpoint.rstrip("/"), api_key, provider

    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        headers = {"Authorization": self.api_key}
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(
                self.endpoint, headers=headers, params={"query": prompt, "per_page": 1}
            )
            response.raise_for_status()
            data = response.json()
            url = (
                data["results"][0]["urls"]["regular"]
                if self.provider == "unsplash"
                else data["photos"][0]["src"]["large"]
            )
            image = await client.get(url)
            image.raise_for_status()
            return image.content


def fallback_image(prompt: str) -> bytes:
    """A deterministic SVG fallback keeps image blocks useful offline."""
    import html

    label = html.escape(" ".join(prompt.split())[:90] or "Image")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675">'
        '<defs><linearGradient id="g"><stop stop-color="#19324d"/>'
        '<stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>'
        '<rect width="100%" height="100%" fill="url(#g)"/>'
        f'<text x="60" y="350" fill="white" font-size="38" '
        f'font-family="sans-serif">{label}</text></svg>'
    )
    return svg.encode()


def image_extension(content: bytes) -> str:
    return (
        "png"
        if content.startswith(b"\x89PNG")
        else "jpg"
        if content.startswith(b"\xff\xd8")
        else "svg"
    )
