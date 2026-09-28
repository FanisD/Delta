from fastapi import FastAPI
from pydantic import BaseModel

from app.core.config import settings

app = FastAPI(title=settings.app_name)


class HealthResponse(BaseModel):
    status: str


@app.get("/health")
@app.get("/api/health", include_in_schema=False)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
