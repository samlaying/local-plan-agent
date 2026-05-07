"""Database connection utilities using psycopg (psycopg3)."""
from __future__ import annotations

import re

import psycopg
import psycopg.rows

from app.core.config import settings


def _sqlalchemy_url_to_psycopg_conninfo(url: str) -> str:
    """Convert SQLAlchemy-style URL (postgresql+psycopg://...) to a psycopg conninfo string."""
    # Strip driver prefix: postgresql+psycopg:// → postgresql://
    url = re.sub(r"^postgresql\+psycopg://", "postgresql://", url)
    return url


async def get_connection() -> psycopg.AsyncConnection:
    """Open and return a single async psycopg connection.

    Callers are responsible for closing the connection (use as async context manager).
    """
    conninfo = _sqlalchemy_url_to_psycopg_conninfo(settings.database_url)
    return await psycopg.AsyncConnection.connect(conninfo, row_factory=psycopg.rows.dict_row)
