from __future__ import annotations

from copy import deepcopy

import litellm
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from app.schemas.agent import (
    AddCardOperation,
    AgentPreview,
    DeleteCardOperation,
    EditOperation,
    MoveCardOperation,
    SetLayoutOperation,
    SetThemeOperation,
    UpdateBlockOperation,
)
from app.schemas.deck import Card, DeckDocument
from app.services.llm.gateway import LLMClient, ProviderCallConfig
from app.services.llm.structured import generate_structured

MAX_OPERATIONS = 20
operation_adapter: TypeAdapter[EditOperation] = TypeAdapter(EditOperation)


class OperationList(BaseModel):
    operations: list[EditOperation] = Field(default_factory=list, max_length=MAX_OPERATIONS)


async def generate_operations(
    message: str, deck: DeckDocument, config: ProviderCallConfig, *, client: LLMClient | None = None
) -> list[EditOperation]:
    """Ask capable models for edit tools, then use the validated JSON fallback."""
    llm_client = client or LLMClient()
    tool = {
        "type": "function",
        "function": {
            "name": "apply_edit_operations",
            "description": "Apply a bounded list of presentation edit operations.",
            "parameters": OperationList.model_json_schema(),
        },
    }
    try:
        result = await litellm.acompletion(
            model=config.litellm_model,
            messages=[
                {"role": "system", "content": "Edit only the supplied presentation."},
                {"role": "user", "content": f"{message}\nCurrent deck:\n{deck.model_dump_json()}"},
            ],
            tools=[tool],
            tool_choice="auto",
            api_key=config.api_key,
            api_base=config.base_url,
        )
        calls = getattr(result, "tool_calls", None)
        if calls:
            arguments = calls[0].function.arguments
            return OperationList.model_validate_json(arguments).operations
    except Exception:
        pass
    return (
        await generate_structured(
            OperationList,
            [{"role": "user", "content": f"{message}\nCurrent deck:\n{deck.model_dump_json()}"}],
            config,
            client=llm_client,
        )
    ).operations


class AgentOperationError(ValueError):
    pass


def apply_operations(
    deck: DeckDocument, operations: list[EditOperation], *, confirm_deletions: bool = False
) -> AgentPreview:
    if len(operations) > MAX_OPERATIONS:
        raise AgentOperationError(f"At most {MAX_OPERATIONS} operations are allowed per turn.")
    candidate = deepcopy(deck)
    warnings: list[str] = []
    requires_confirmation = False
    for operation in operations:
        if isinstance(operation, AddCardOperation):
            if len(candidate.cards) >= 100:
                raise AgentOperationError("A presentation cannot contain more than 100 cards.")
            index = (
                len(candidate.cards)
                if operation.index is None
                else min(operation.index, len(candidate.cards))
            )
            candidate.cards.insert(index, operation.card)
        elif isinstance(operation, UpdateBlockOperation):
            card = _card(candidate, operation.card_id)
            if operation.block_index >= len(card.blocks):
                raise AgentOperationError("Block index is out of range.")
            card.blocks[operation.block_index] = operation.block
        elif isinstance(operation, MoveCardOperation):
            card = _card(candidate, operation.card_id)
            candidate.cards.remove(card)
            candidate.cards.insert(min(operation.to_index, len(candidate.cards)), card)
        elif isinstance(operation, DeleteCardOperation):
            if len(candidate.cards) == 1:
                raise AgentOperationError("A presentation must keep at least one card.")
            if not (operation.confirmed or confirm_deletions):
                requires_confirmation = True
                warnings.append(f"Deleting card '{operation.card_id}' requires confirmation.")
                continue
            candidate.cards.remove(_card(candidate, operation.card_id))
        elif isinstance(operation, SetLayoutOperation):
            _card(candidate, operation.card_id).layout = operation.layout
        elif isinstance(operation, SetThemeOperation):
            candidate.theme = operation.theme
    # Re-run the complete document validators after every edit, including nested blocks.
    try:
        validated = DeckDocument.model_validate(candidate.model_dump(mode="json"))
    except ValidationError as exc:
        raise AgentOperationError(f"Operations produced an invalid presentation: {exc}") from exc
    candidate.cards = validated.cards
    candidate.theme = validated.theme
    return AgentPreview(
        deck=candidate,
        operations=operations,
        requires_confirmation=requires_confirmation,
        warnings=warnings,
    )


def _card(deck: DeckDocument, card_id: str) -> Card:
    for card in deck.cards:
        if card.id == card_id:
            return card
    raise AgentOperationError(f"Card '{card_id}' was not found.")
