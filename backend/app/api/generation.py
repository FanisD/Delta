from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, session_factory
from app.models.deck import DeckRecord, utc_now
from app.models.generation import GenerationJobRecord
from app.schemas.deck import DeckCreate
from app.schemas.generation import (
    GenerationJobCreate,
    GenerationJobStatus,
    Outline,
    OutlineRequest,
    RegenerateCardRequest,
)
from app.services.generation import create_card, create_outline, generate_cards

router = APIRouter(prefix="/api/generation", tags=["generation"])
SessionDependency = Depends(get_session)
_tasks: set[asyncio.Task[None]] = set()


def _status(job: GenerationJobRecord) -> GenerationJobStatus:
    return GenerationJobStatus(
        id=job.id,
        status=job.status,
        progress=job.progress,
        outline=job.outline,
        cards=job.cards,
        errors=job.errors,
        deck_id=job.deck_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _event(job: GenerationJobRecord, kind: str, data: object) -> None:
    job.events = [*job.events, {"event": kind, "data": data}]
    job.updated_at = utc_now()


@router.post("/outline", response_model=Outline)
async def outline(payload: OutlineRequest, session: AsyncSession = SessionDependency) -> Outline:
    return await create_outline(payload.prompt, payload.settings, session)


async def _run_job(job_id: str) -> None:
    async with session_factory() as session:
        job = await session.get(GenerationJobRecord, job_id)
        if job is None:
            return
        job.status = "running"
        _event(job, "outline", job.outline)
        await session.commit()
        try:
            from app.schemas.generation import GenerationSettings, Outline

            settings = GenerationSettings.model_validate(job.settings)
            generated_outline = (
                Outline.model_validate(job.outline)
                if job.outline
                else await create_outline(job.prompt, settings, session)
            )
            job.outline = generated_outline.model_dump(mode="json")
            _event(job, "outline", job.outline)
            await session.commit()
            cards = await generate_cards(generated_outline, settings, session)
            for card in cards:
                job.cards = [*job.cards, card.model_dump(mode="json")]
                job.progress = round(len(job.cards) / len(generated_outline.items) * 100)
                _event(job, "card", card.model_dump(mode="json"))
                await session.commit()
            deck = DeckRecord(
                id=str(uuid4()),
                title=generated_outline.title,
                theme="ocean",
                document=DeckCreate(title=generated_outline.title, cards=cards).model_dump(
                    mode="json"
                ),
            )
            session.add(deck)
            job.deck_id = deck.id
            job.status = "completed"
            job.progress = 100
            _event(job, "done", {"deck_id": deck.id})
            await session.commit()
        except Exception as exc:
            job.status = "partial" if job.cards else "failed"
            job.errors = [*job.errors, str(exc)]
            _event(job, "error", {"message": str(exc)})
            await session.commit()


def _track(task: asyncio.Task[None]) -> None:
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


@router.post("/jobs", response_model=GenerationJobStatus, status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    payload: GenerationJobCreate, session: AsyncSession = SessionDependency
) -> GenerationJobStatus:
    job = GenerationJobRecord(
        id=str(uuid4()),
        prompt=payload.prompt,
        settings=payload.settings.model_dump(mode="json"),
        outline=payload.outline.model_dump(mode="json") if payload.outline else None,
        cards=[],
        errors=[],
        events=[],
        status="queued",
        progress=0,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    _track(asyncio.create_task(_run_job(job.id)))
    return _status(job)


@router.get("/jobs/{job_id}", response_model=GenerationJobStatus)
async def get_job(job_id: str, session: AsyncSession = SessionDependency) -> GenerationJobStatus:
    job = await session.get(GenerationJobRecord, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return _status(job)


@router.post("/jobs/{job_id}/recover", response_model=GenerationJobStatus)
async def recover_job(
    job_id: str, session: AsyncSession = SessionDependency
) -> GenerationJobStatus:
    job = await session.get(GenerationJobRecord, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    if job.status in {"queued", "running"} and not any(task for task in _tasks if not task.done()):
        _track(asyncio.create_task(_run_job(job.id)))
    return _status(job)


@router.post("/jobs/{job_id}/cards/{card_id}/regenerate", response_model=GenerationJobStatus)
async def regenerate_card(
    job_id: str,
    card_id: str,
    payload: RegenerateCardRequest,
    session: AsyncSession = SessionDependency,
) -> GenerationJobStatus:
    job = await session.get(GenerationJobRecord, job_id)
    if job is None or not job.outline:
        raise HTTPException(status_code=404, detail="Generation job not found")
    from app.schemas.generation import GenerationSettings, Outline

    outline_model = Outline.model_validate(job.outline)
    item = next((item for item in outline_model.items if item.id == card_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Card not found")
    settings = payload.settings or GenerationSettings.model_validate(job.settings)
    card = await create_card(outline_model, item, settings, session)
    job.cards = [card.model_dump(mode="json") if c.get("id") == card_id else c for c in job.cards]
    job.errors = [error for error in job.errors if card_id not in error]
    job.status = "completed" if len(job.cards) == len(outline_model.items) else "partial"
    _event(job, "card", card.model_dump(mode="json"))
    await session.commit()
    return _status(job)


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str, session: AsyncSession = SessionDependency) -> StreamingResponse:
    job = await session.get(GenerationJobRecord, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")

    async def stream() -> AsyncIterator[str]:
        sent = 0
        while True:
            async with session_factory() as current:
                latest = await current.get(GenerationJobRecord, job_id)
            if latest is None:
                break
            for item in latest.events[sent:]:
                yield f"event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"
            sent = len(latest.events)
            if latest.status in {"completed", "partial", "failed"} and sent >= len(latest.events):
                break
            await asyncio.sleep(0.15)
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
