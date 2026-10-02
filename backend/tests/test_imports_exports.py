import pytest
from fastapi import HTTPException

from app.api.exports import standalone_html
from app.api.imports import validate_public_url


def test_standalone_html_contains_all_cards_and_escaped_text() -> None:
    document = {
        "title": "A <deck>",
        "theme": "ocean",
        "cards": [
            {
                "title": "Intro",
                "blocks": [{"type": "paragraph", "text": "<safe>"}],
            }
        ],
    }
    rendered = standalone_html(document)
    assert "<safe>" not in rendered
    assert "&lt;safe&gt;" in rendered
    assert "Intro" in rendered


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1:8000", "http://localhost", "http://169.254.169.254"]
)
def test_ssrf_guard_blocks_local_and_link_local_urls(url: str) -> None:
    with pytest.raises(HTTPException) as error:
        validate_public_url(url)
    assert error.value.status_code == 400


def test_ssrf_guard_rejects_non_http_schemes() -> None:
    with pytest.raises(HTTPException):
        validate_public_url("file:///etc/passwd")
