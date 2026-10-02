# ruff: noqa: E501
from __future__ import annotations

import asyncio
import html
import io
import json
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from app.core.config import settings
from app.database import session_factory
from app.models.deck import DeckRecord

router = APIRouter(prefix="/api/decks", tags=["exports"])


async def _deck(deck_id: str) -> dict[str, Any]:
    async with session_factory() as session:
        record = await session.get(DeckRecord, deck_id)
    if record is None:
        raise HTTPException(404, "Deck not found")
    return {**record.document, "id": record.id, "title": record.title, "theme": record.theme}


def standalone_html(deck: dict[str, Any]) -> str:
    cards = []
    for index, card in enumerate(deck["cards"], 1):
        blocks = []
        for block in card["blocks"]:
            kind = block["type"]
            if kind == "heading":
                tag = "h1" if block.get("level", 2) == 1 else "h2"
                blocks.append(f"<{tag}>{html.escape(block['text'])}</{tag}>")
            elif kind == "paragraph":
                blocks.append(f"<p>{html.escape(block['text'])}</p>")
            elif kind == "bullets":
                items = "".join(f"<li>{html.escape(item)}</li>" for item in block["items"])
                blocks.append(f"<ul>{items}</ul>")
            elif kind == "quote":
                blocks.append(f"<blockquote>{html.escape(block['text'])}</blockquote>")
            elif kind == "stat":
                blocks.append(
                    f"<p class='stat'><b>{html.escape(block['value'])}</b> "
                    f"{html.escape(block['label'])}</p>"
                )
            else:
                blocks.append(f"<pre>{html.escape(json.dumps(block, ensure_ascii=False))}</pre>")
        cards.append(
            f"<article><div>{''.join(blocks)}</div><footer>"
            f"{html.escape(card['title'])} · {index}/{len(deck['cards'])}</footer></article>"
        )
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(deck["title"])}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#eee;font-family:Arial,sans-serif;color:#17243b}}
article{{width:297mm;height:210mm;margin:10mm auto;padding:22mm;display:flex;flex-direction:column;justify-content:space-between;background:white;page-break-after:always;box-shadow:0 2px 12px #0002}}
h1{{font-size:42pt}}h2{{font-size:28pt}}p,li{{font-size:18pt;line-height:1.45}}blockquote{{font-size:26pt;border-left:5px solid #5d82bb;padding-left:20px}}footer{{color:#71809b;font-size:11pt;border-top:1px solid #dde3ee;padding-top:10px}}
@media print{{body{{background:white}}article{{margin:0;box-shadow:none}}}}@page{{size:A4 landscape;margin:0}}
</style></head><body>{"".join(cards)}</body></html>"""


@router.get("/{deck_id}/export/html")
async def export_html(deck_id: str) -> Response:
    deck = await _deck(deck_id)
    return HTMLResponse(
        standalone_html(deck),
        headers={"Content-Disposition": f'attachment; filename="{deck["title"]}.html"'},
    )


async def _playwright_bytes(deck_id: str, kind: str, base_url: str) -> bytes:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise HTTPException(
            503, "Playwright is not installed; PDF/PNG export is unavailable."
        ) from exc
    url = f"{base_url.rstrip('/')}/print/{deck_id}"
    async with async_playwright() as playwright:
        browser = None
        for channel in ("chrome", "msedge"):
            try:
                browser = await playwright.chromium.launch(channel=channel, headless=True)
                break
            except Exception:
                continue
        if browser is None:
            browsers_path = settings.resolved_data_dir() / "browsers"
            browsers_path.mkdir(parents=True, exist_ok=True)
            env = {"PLAYWRIGHT_BROWSERS_PATH": str(browsers_path)}
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    ["playwright", "install", "chromium"],
                    env={**__import__("os").environ, **env},
                    check=True,
                    capture_output=True,
                    timeout=300,
                )
                browser = await playwright.chromium.launch(
                    env={"PLAYWRIGHT_BROWSERS_PATH": str(browsers_path)}, headless=True
                )
            except Exception as exc:
                raise HTTPException(
                    503,
                    "No Chrome/Edge found and Chromium download failed. Install a browser "
                    "or Playwright Chromium.",
                ) from exc
        try:
            page = await browser.new_page(
                viewport={"width": 1123, "height": 794}, device_scale_factor=2
            )
            await page.goto(url, wait_until="networkidle", timeout=30_000)
            if kind == "pdf":
                return await page.pdf(
                    format="A4", landscape=True, print_background=True, page_ranges="1-"
                )
            return await page.screenshot(type="png", full_page=True)
        finally:
            await browser.close()


@router.get("/{deck_id}/export/{kind}")
async def export_visual(deck_id: str, kind: str, request: Request) -> Response:
    if kind not in {"pdf", "png"}:
        raise HTTPException(404, "Supported formats are pdf and png")
    data = await _playwright_bytes(deck_id, kind, str(request.base_url))
    media = "application/pdf" if kind == "pdf" else "image/png"
    return Response(
        data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{deck_id}.{kind}"'},
    )


@router.get("/{deck_id}/export/pptx")
async def export_pptx(deck_id: str) -> Response:
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
    except ImportError as exc:
        raise HTTPException(
            503, "python-pptx is not installed; PPTX export is unavailable."
        ) from exc
    deck = await _deck(deck_id)
    presentation = Presentation()
    presentation.slide_width, presentation.slide_height = Inches(13.333), Inches(7.5)
    for card in deck["cards"]:
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        box = slide.shapes.add_textbox(Inches(0.7), Inches(0.6), Inches(12), Inches(6.1))
        frame = box.text_frame
        frame.text = card["title"]
        frame.paragraphs[0].font.size = Pt(30)
        for block in card["blocks"]:
            if block["type"] in {"heading", "paragraph", "quote", "stat"}:
                p = frame.add_paragraph()
                p.text = block.get("text") or f"{block.get('value', '')} {block.get('label', '')}"
                p.font.size = Pt(18)
            elif block["type"] == "bullets":
                for item in block["items"]:
                    p = frame.add_paragraph()
                    p.text = item
                    p.level = 0
                    p.font.size = Pt(16)
    output = io.BytesIO()
    presentation.save(output)
    return Response(
        output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{deck["title"]}.pptx"'},
    )
