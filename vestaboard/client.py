"""Thin client for the Vestaboard Read/Write API.

Requires the VESTABOARD_TOKEN environment variable (a Read/Write API key).
API docs: https://docs.vestaboard.com/docs/read-write-api/endpoints
"""

import logging
import os
import sys

import requests

from .characters import COLS, ROWS

API_URL = "https://cloud.vestaboard.com/"
TIMEOUT = 15

log = logging.getLogger(__name__)


class MissingTokenError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("VESTABOARD_TOKEN")
    if not token:
        raise MissingTokenError(
            "VESTABOARD_TOKEN is not set. Create a Read/Write API key at "
            "https://web.vestaboard.com and export it, e.g. "
            "`export VESTABOARD_TOKEN=...` (or add it to .env)."
        )
    return token


def _headers() -> dict[str, str]:
    return {"X-Vestaboard-Token": _token(), "Content-Type": "application/json"}


def _post(body: dict) -> requests.Response:
    resp = requests.post(API_URL, json=body, headers=_headers(), timeout=TIMEOUT)
    if resp.status_code == 423:
        log.error(
            "Board is muted (HTTP 423); message rejected. "
            'Pass {"forced": true} to override — not done automatically.'
        )
        sys.exit(1)
    resp.raise_for_status()
    return resp


def post_characters(grid: list[list[int]], forced: bool = False) -> None:
    """Post a 6x22 grid of character codes to the board."""
    if len(grid) != ROWS or any(len(row) != COLS for row in grid):
        raise ValueError(f"grid must be {ROWS} rows of {COLS} character codes")
    body: dict = {"characters": grid}
    if forced:
        body["forced"] = True
    _post(body)


def post_text(text: str, forced: bool = False) -> None:
    """Post plain text; the board lays it out itself."""
    if not text.strip():
        raise ValueError("blank messages are rejected by the API")
    body: dict = {"text": text}
    if forced:
        body["forced"] = True
    _post(body)


def get_current() -> dict:
    """Return the message currently on the board."""
    resp = requests.get(API_URL, headers=_headers(), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()
