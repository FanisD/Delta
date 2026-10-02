from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.deck import DeckRecord
from app.schemas.ai import AIEditRequest, AIEditResponse
from app.schemas.deck import DeckCreate

router = APIRouter(prefix="/api/ai", tags=["ai"])
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


@router.post("/edit", response_model=AIEditResponse)
async def edit(request: AIEditRequest, session: SessionDependency) -> AIEditResponse:
    record = await session.get(DeckRecord, request.deck_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Deck not found")
    document = DeckCreate.model_validate(record.document)
    card = next((card for card in document.cards if card.id == request.card_id), None)
    if card is None or request.block_index >= len(card.blocks):
        raise HTTPException(status_code=404, detail="Block not found")
    block = card.blocks[request.block_index]
    text = getattr(block, "text", None) or getattr(block, "title", None) or card.title
    if request.action == "shorten":
        text = " ".join(text.split()[: max(3, len(text.split()) // 2)])
    elif request.action == "expand":
        text = f"{text} — {request.instruction or 'with more context and practical detail'}"
    elif request.action == "translate":
        text = f"{text} ({request.instruction or 'translated version'})"
    elif request.action == "tone":
        text = f"{text} ({request.instruction or 'a more confident tone'})"
    else:
        text = f"{text} — {request.instruction or 'a clearer rewrite'}"
    return AIEditResponse(text=text[:4000], action=request.action)
