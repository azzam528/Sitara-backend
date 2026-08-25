from html import escape
from pathlib import Path
from urllib.parse import quote, urlparse

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.core.config import settings

router = APIRouter(tags=["Activation"])

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
ACTIVATION_TEMPLATE = TEMPLATES_DIR / "activation.html"
INVALID_TEMPLATE = TEMPLATES_DIR / "activation_invalid.html"


def _safe_download_url(raw_url: str | None) -> str | None:
    if raw_url is None:
        return None

    url = raw_url.strip()
    if not url:
        return None

    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        return None

    return url


def _download_section() -> str:
    download_url = _safe_download_url(settings.SITARA_APP_DOWNLOAD_URL)
    if download_url is None:
        return ""

    safe_href = escape(download_url, quote=True)
    return (
        '<p class="download">'
        f'<a href="{safe_href}">Unduh aplikasi SITARA</a>'
        "</p>"
    )


def _deep_link_href(token: str) -> str:
    encoded_token = quote(token, safe="")
    return escape(
        f"sitara://activate?token={encoded_token}",
        quote=True,
    )


@router.get("/activate", response_class=HTMLResponse)
def activation_landing(
    token: str | None = Query(default=None),
):
    if token is None or not token.strip():
        return HTMLResponse(
            content=INVALID_TEMPLATE.read_text(encoding="utf-8"),
            status_code=400,
        )

    html = ACTIVATION_TEMPLATE.read_text(encoding="utf-8")
    html = html.replace("__DEEP_LINK_HREF__", _deep_link_href(token))
    html = html.replace("__DOWNLOAD_SECTION__", _download_section())
    return HTMLResponse(content=html, status_code=200)
