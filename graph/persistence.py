import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    SQLA_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    SQLA_AVAILABLE = False


async def _get_engine():
    if not SQLA_AVAILABLE:
        raise RuntimeError("SQLAlchemy not installed")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set")
    # Expect asyncpg-style URL (postgresql+asyncpg://...)
    return create_async_engine(db_url, future=True, echo=False)


async def save_checkpoint_db(
    state_dict: Dict[str, Any], thread_id: str
) -> Dict[str, Any]:
    """Save checkpoint to Postgres JSONB `checkpoints` table.

    This function intentionally raises on any DB-related error so callers can
    fallback to file-based persistence.
    """
    if not SQLA_AVAILABLE:
        raise RuntimeError("SQLAlchemy not available")

    engine = await _get_engine()
    async with engine.begin() as conn:
        # compute next version
        result = await conn.execute(
            text(
                "SELECT COALESCE(MAX(version), 0) FROM checkpoints WHERE thread_id = :tid"
            ),
            {"tid": thread_id},
        )
        maxv = result.scalar()
        version = (maxv or 0) + 1
        new_id = str(uuid4())
        # insert row; state is stored as JSONB
        await conn.execute(
            text(
                "INSERT INTO checkpoints (id, thread_id, version, state, created_at, updated_at) VALUES (:id, :tid, :ver, CAST(:state AS jsonb), now(), now())"
            ),
            {
                "id": new_id,
                "tid": thread_id,
                "ver": version,
                "state": json.dumps(state_dict),
            },
        )
        return {
            "id": new_id,
            "thread_id": thread_id,
            "version": version,
            "created_at": datetime.utcnow().isoformat(),
        }


async def load_checkpoint_db(
    thread_id: str, version: Optional[int] = None
) -> Dict[str, Any]:
    """Load checkpoint payload (state dict) from DB. Returns the state dict.

    Raises on DB errors so callers can fallback to file-based load.
    """
    if not SQLA_AVAILABLE:
        raise RuntimeError("SQLAlchemy not available")

    engine = await _get_engine()
    async with engine.begin() as conn:
        if version is None:
            q = text(
                "SELECT state FROM checkpoints WHERE thread_id = :tid ORDER BY version DESC LIMIT 1"
            )
            params = {"tid": thread_id}
        else:
            q = text(
                "SELECT state FROM checkpoints WHERE thread_id = :tid AND version = :ver LIMIT 1"
            )
            params = {"tid": thread_id, "ver": version}
        result = await conn.execute(q, params)
        row = result.first()
        if row is None:
            raise KeyError(f"Checkpoint not found: {thread_id} (version={version})")
        # row[0] contains JSON state
        state_json = row[0]
        # if driver returned a string, parse it
        if isinstance(state_json, str):
            return json.loads(state_json)
        return state_json


async def list_checkpoints_db(thread_id: str) -> List[Dict[str, Any]]:
    """List metadata for checkpoints for a thread_id."""
    if not SQLA_AVAILABLE:
        raise RuntimeError("SQLAlchemy not available")

    engine = await _get_engine()
    async with engine.begin() as conn:
        q = text(
            "SELECT id, thread_id, version, created_at FROM checkpoints WHERE thread_id = :tid ORDER BY version DESC"
        )
        result = await conn.execute(q, {"tid": thread_id})
        rows = result.fetchall()
        out = []
        for r in rows:
            out.append(
                {
                    "id": r[0],
                    "thread_id": r[1],
                    "version": r[2],
                    "created_at": (
                        r[3].isoformat() if hasattr(r[3], "isoformat") else r[3]
                    ),
                }
            )
        return out


async def delete_checkpoints_db(thread_id: str) -> int:
    """Delete all checkpoints for `thread_id`. Returns number of rows deleted.

    Intended for test teardown and cleanup.
    """
    if not SQLA_AVAILABLE:
        raise RuntimeError("SQLAlchemy not available")

    engine = await _get_engine()
    async with engine.begin() as conn:
        res = await conn.execute(
            text("DELETE FROM checkpoints WHERE thread_id = :tid"), {"tid": thread_id}
        )
        return res.rowcount or 0
