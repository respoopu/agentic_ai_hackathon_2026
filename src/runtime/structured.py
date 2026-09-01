"""Optional prompt-backed structured-output seam for Bedrock execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from src.runtime.model import create_bedrock_model

ROOT = Path(__file__).resolve().parents[2]
PROMPT_FILES = {
    "planner": "planner-agent.md",
    "discovery": "discovery-engine.md",
    "guardian": "guardian-agent.md",
    "broker": "broker-agent.md",
    "observer": "observer-agent.md",
    "compliance": "compliance-agent.md",
}
T = TypeVar("T", bound=BaseModel)


def invoke_structured(
    agent: str,
    payload: dict[str, Any],
    output_schema: type[T],
    *,
    reasoning: bool = False,
) -> T:
    """Invoke one merged prompt with a Pydantic response contract.

    Deterministic policies remain the default judge/test path. This seam is the
    live Bedrock path and deliberately exposes no arbitrary tool collection.
    """

    try:
        filename = PROMPT_FILES[agent]
    except KeyError as exc:
        raise ValueError(f"unknown structured agent {agent}") from exc
    prompt = (ROOT / "docs" / "agent-system-prompts" / filename).read_text(
        encoding="utf-8"
    )
    model = create_bedrock_model(reasoning=reasoning).with_structured_output(output_schema)
    result = model.invoke(
        [
            ("system", prompt),
            (
                "user",
                "Return only the typed result for this JSON payload:\n"
                + json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str),
            ),
        ]
    )
    return result if isinstance(result, output_schema) else output_schema.model_validate(result)
