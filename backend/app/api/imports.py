from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.database import session_factory
from app.schemas.generation import GenerationSettings, Outline
from app.services.generation import create_outline
from app.services.llm.chunking import map_reduce_text
from app.services.llm.gateway import LLMClient
from app.services.llm.settings import load_call_config

router = APIRouter(prefix="/api/import", tags=["imports"])
MAX_BYTES = 10 * 1024 * 1024
TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def validate_public_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(400, "Only http and https URLs are allowed")
    try:
        addresses = {
            ipaddress.ip_address(info[4][0])
            for info in socket.getaddrinfo(
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        }
    except (socket.gaierror, ValueError):
        raise HTTPException(400, "URL host could not be resolved") from None
    if any(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
        for address in addresses
    ):
        raise HTTPException(
            400, "Private, loopback, link-local, and reserved addresses are blocked"
        )
    return value


class TextImport(BaseModel):
    text: str = Field(min_length=1, max_length=500_000)


async def _outline(text: str) -> Outline:
    # Chunking is deliberately performed before the gateway call, so large pasted
    # documents remain usable with small-context providers.
    async def summarize(chunk: str) -> str:
        async with session_factory() as session:
            config = await load_call_config(session, "ollama")
        if not config:
            return await _identity_summary(chunk)
        try:
            result = await LLMClient().complete(
                [
                    {
                        "role": "user",
                        "content": f"Summarize these notes for a presentation outline:\n{chunk}",
                    }
                ],
                config,
                max_tokens=700,
            )
            return result.content
        except Exception:
            return await _identity_summary(chunk)

    chunks = await map_reduce_text(text, summarize)
    return await create_outline(chunks, GenerationSettings())


async def _identity_summary(chunk: str) -> str:
    return chunk[:6000]


@router.post("/text", response_model=Outline)
async def import_text(payload: TextImport) -> Outline:
    return await _outline(payload.text)


@router.post("/file", response_model=Outline)
async def import_file(file: UploadFile = File(...)) -> Outline:  # noqa: B008
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Import is limited to 10 MB")
    name = (file.filename or "").lower()
    try:
        if name.endswith(".pdf"):
            from pypdf import PdfReader

            text = "\n".join(
                page.extract_text() or ""
                for page in PdfReader(__import__("io").BytesIO(data)).pages
            )
        elif name.endswith(".docx"):
            from docx import Document

            text = "\n".join(p.text for p in Document(__import__("io").BytesIO(data)).paragraphs)
        elif name.endswith((".txt", ".md")):
            text = data.decode("utf-8", errors="replace")
        else:
            raise HTTPException(415, "Supported files are PDF, DOCX, TXT, and Markdown")
    except ImportError as exc:
        raise HTTPException(503, "The optional parser for this file type is not installed") from exc
    return await _outline(text)


@router.post("/url", response_model=Outline)
async def import_url(payload: dict[str, str]) -> Outline:
    url = validate_public_url(payload.get("url", ""))
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=False) as client:
            response = await client.get(url, headers={"Accept": "text/html,text/plain"})
            response.raise_for_status()
            if len(response.content) > MAX_BYTES:
                raise HTTPException(413, "Remote import is limited to 10 MB")
            text = response.text
    except httpx.HTTPError as exc:
        raise HTTPException(400, "Unable to fetch URL") from exc
    return await _outline(text)
