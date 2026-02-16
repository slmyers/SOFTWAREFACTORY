"""AgentState TypedDict + Pydantic v2 model + JSON checkpoint helpers.

This module implements the canonical runtime state for the graph (Issue #3).
- `AgentState` (TypedDict): structural spec used by the graph.
- `AgentStateModel` (Pydantic v2 BaseModel): validation + (de)serialization + checkpoint helpers.

Design decisions (v0):
- Core required fields: `spec_path`, `codebase`, `iteration`, `quality_score`.
- `quality_score` uses 0..100 scale.
- Checkpoint persistence: JSON file fallback (sync) — DB deferred to Issue #5.
- `plan` and `test_results` remain `list[dict]` for now.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, TypedDict, Union

from pydantic import BaseModel, Field, ValidationError, field_validator


class AgentState(TypedDict):
    spec_path: str
    spec_content: str
    spec_structure: Dict[str, Any]
    codebase: Dict[str, str]
    plan: List[Dict[str, Any]]
    test_results: List[Dict[str, Any]]
    issues: List[str]
    iteration: int
    next: str
    checkpoint: Dict[str, Any]
    mcp_servers: List[str]
    quality_score: float
    invariants: List[str]


class AgentStateModel(BaseModel):
    """Validated runtime state for the LangGraph-powered harness.

    Required (core): `spec_path`, `codebase`, `iteration`, `quality_score`.
    Other fields default to sensible empty containers or empty strings.
    """

    spec_path: str = Field(..., description="Path to the spec file")
    spec_content: str = Field("", description="Raw spec content")
    spec_structure: Dict[str, Any] = Field(default_factory=dict)
    codebase: Dict[str, str] = Field(..., description="Mapping filename -> source text")
    plan: List[Dict[str, Any]] = Field(default_factory=list)
    test_results: List[Dict[str, Any]] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    iteration: int = Field(..., ge=0, description="Non-negative run iteration")
    next: str = Field("", description="Suggested next node/action")
    checkpoint: Dict[str, Any] = Field(default_factory=dict)
    mcp_servers: List[str] = Field(default_factory=list)
    quality_score: float = Field(..., ge=0, le=100, description="0..100 percentage")
    invariants: List[str] = Field(default_factory=list)

    # Additional lightweight validators
    @field_validator("spec_path")
    @classmethod
    def _spec_path_must_not_be_empty(cls, v: str) -> str:  # type: ignore[override]
        if not isinstance(v, str) or not v.strip():
            raise ValueError("spec_path must be a non-empty string")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-compatible dict representation of the state."""
        return self.model_dump(mode="json_compatible")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentStateModel":
        """Validate and create an AgentStateModel from a plain dict."""
        return cls.model_validate(data)

    def save_checkpoint(self, path: Union[str, Path]) -> None:
        """Serialize state to JSON file (sync). Creates parent dirs if missing."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.model_dump_json())

    @classmethod
    def load_checkpoint(cls, path: Union[str, Path]) -> "AgentStateModel":
        """Load state from a JSON checkpoint file and validate it."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Checkpoint not found: {p}")
        return cls.model_validate_json(p.read_text())

    class Config:
        extra = "forbid"
        frozen = False


# Async canonical checkpoint API (DB preferred, file fallback)
import os
from datetime import datetime
from uuid import uuid4
from typing import Optional
import graph.persistence as persistence


async def save_checkpoint(state: "AgentStateModel", thread_id: str) -> dict:
    """Persist state: prefer DB, fallback to file. Returns metadata dict."""
    data = state.to_dict()
    try:
        return await persistence.save_checkpoint_db(data, thread_id)
    except Exception:
        # fallback to file-based checkpoint
        path = Path("checkpoints") / f"{thread_id}.json"
        state.save_checkpoint(path)
        return {"id": str(uuid4()), "thread_id": thread_id, "version": 1, "created_at": datetime.utcnow().isoformat()}


async def load_checkpoint(thread_id: str, version: Optional[int] = None) -> "AgentStateModel":
    """Load checkpoint: prefer DB, fallback to file."""
    try:
        data = await persistence.load_checkpoint_db(thread_id, version=version)
        return AgentStateModel.from_dict(data)
    except Exception:
        path = Path("checkpoints") / f"{thread_id}.json"
        return AgentStateModel.load_checkpoint(path)

