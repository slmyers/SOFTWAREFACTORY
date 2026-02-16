"""Pytest configuration: load environment variables from .env files so tests see DATABASE_URL.

This file loads, in order, `.env.test`, `.env.local`, and `.env` from the repo root
(if present) without overriding already-set environment variables.
"""

from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
for name in (".env.test", ".env.local", ".env"):
    p = ROOT / name
    if p.exists():
        load_dotenv(dotenv_path=p, override=False)
