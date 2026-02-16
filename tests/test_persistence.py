import os
import pytest

import graph.persistence as persistence


@pytest.mark.asyncio
async def test_db_functions_raise_when_sqlalchemy_missing():
    # Simulate SQLAlchemy not being available
    persistence.SQLA_AVAILABLE = False
    with pytest.raises(RuntimeError):
        await persistence.save_checkpoint_db({"a": 1}, "tid")
    with pytest.raises(RuntimeError):
        await persistence.load_checkpoint_db("tid")
    with pytest.raises(RuntimeError):
        await persistence.list_checkpoints_db("tid")


@pytest.mark.asyncio
async def test__get_engine_raises_when_database_url_missing(monkeypatch):
    # Simulate SQLAlchemy present but DATABASE_URL not configured
    persistence.SQLA_AVAILABLE = True
    # Ensure env var is unset
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        await persistence._get_engine()
