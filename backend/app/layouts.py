import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

LAYOUTS_PATH = Path(__file__).resolve().parents[2] / "shared" / "layouts.json"
LAYOUTS_ADAPTER = TypeAdapter(list[dict[str, Any]])


def load_layouts() -> list[dict[str, Any]]:
    with LAYOUTS_PATH.open(encoding="utf-8") as layout_file:
        return LAYOUTS_ADAPTER.validate_python(json.load(layout_file))
