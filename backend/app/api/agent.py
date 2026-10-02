import json

from fastapi import APIRouter, HTTPException
from pydantic import TypeAdapter

from app.schemas.agent import AgentPreview, AgentRequest, EditOperation
from app.services.agent import AgentOperationError, apply_operations

router = APIRouter(prefix="/api/agent", tags=["agent"])
operation_adapter: TypeAdapter[EditOperation] = TypeAdapter(EditOperation)


@router.post("/preview", response_model=AgentPreview)
async def preview(request: AgentRequest) -> AgentPreview:
    operations = request.operations
    if operations is None:
        # The structured fallback is deliberately deterministic when no provider is
        # configured; callers can also submit LiteLLM-generated operations directly.
        operations = _parse_operations_from_message(request.message)
    try:
        return apply_operations(
            request.deck, operations, confirm_deletions=request.confirm_deletions
        )
    except AgentOperationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _parse_operations_from_message(message: str) -> list[EditOperation]:
    try:
        payload = json.loads(message)
        values = payload if isinstance(payload, list) else payload.get("operations", [])
        return [operation_adapter.validate_python(value) for value in values]
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Provide operations as JSON or configure a model to generate tool calls.",
        ) from exc
