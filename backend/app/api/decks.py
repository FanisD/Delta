from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.deck import DeckRecord, utc_now
from app.schemas.deck import DeckCreate, DeckDocument, DeckUpdate

router = APIRouter(prefix="/api/decks", tags=["decks"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def to_document(record: DeckRecord) -> DeckDocument:
    return DeckDocument.model_validate(
        {
            **record.document,
            "id": record.id,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "version": record.version,
        }
    )


@router.get("", response_model=list[DeckDocument])
async def list_decks(session: SessionDependency) -> list[DeckDocument]:
    records = await session.scalars(select(DeckRecord).order_by(DeckRecord.updated_at.desc()))
    return [to_document(record) for record in records]


@router.post("", response_model=DeckDocument, status_code=status.HTTP_201_CREATED)
async def create_deck(payload: DeckCreate, session: SessionDependency) -> DeckDocument:
    now = utc_now()
    record = DeckRecord(
        id=str(uuid4()),
        title=payload.title,
        theme=payload.theme.value,
        document=payload.model_dump(mode="json"),
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return to_document(record)


@router.get("/{deck_id}", response_model=DeckDocument)
async def get_deck(deck_id: str, session: SessionDependency) -> DeckDocument:
    record = await session.get(DeckRecord, deck_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    return to_document(record)


@router.patch("/{deck_id}", response_model=DeckDocument)
async def update_deck(
    deck_id: str,
    payload: DeckUpdate,
    session: SessionDependency,
) -> DeckDocument:
    record = await session.get(DeckRecord, deck_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")

    if payload.version is not None and payload.version != record.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Deck changed on the server", "version": record.version},
        )
    patch = payload.model_dump(exclude_unset=True, mode="json")
    patch.pop("version", None)
    document = {**record.document, **patch}
    validated = DeckCreate.model_validate(document)
    record.title = validated.title
    record.theme = validated.theme.value
    record.document = validated.model_dump(mode="json")
    record.updated_at = utc_now()
    record.version += 1
    await session.commit()
    await session.refresh(record)
    return to_document(record)


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deck(deck_id: str, session: SessionDependency) -> Response:
    record = await session.get(DeckRecord, deck_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    await session.delete(record)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{deck_id}/duplicate",
    response_model=DeckDocument,
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_deck(deck_id: str, session: SessionDependency) -> DeckDocument:
    source = await session.get(DeckRecord, deck_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    now = utc_now()
    copy = DeckRecord(
        id=str(uuid4()),
        title=f"{source.title} copy",
        theme=source.theme,
        document={**source.document, "title": f"{source.title} copy"},
        version=1,
        created_at=now,
        updated_at=now,
    )
    session.add(copy)
    await session.commit()
    await session.refresh(copy)
    return to_document(copy)
