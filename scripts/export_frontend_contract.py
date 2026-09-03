"""Export the browser-facing OpenAPI contract from the canonical Pydantic models."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.schema.api import (
    ApiErrorView,
    AttendanceStepResponse,
    BookingStepResponse,
    DemoApproveRequest,
    DemoAttendanceRequest,
    DemoNextPlanRequest,
    DemoSetupRequest,
    HealthView,
    PlanStepResponse,
    ShortlistStepResponse,
)

DEFAULT_OUTPUT = ROOT / "contracts" / "frontend-api.openapi.json"

MODELS: tuple[type[BaseModel], ...] = (
    ApiErrorView,
    AttendanceStepResponse,
    BookingStepResponse,
    DemoApproveRequest,
    DemoAttendanceRequest,
    DemoNextPlanRequest,
    DemoSetupRequest,
    HealthView,
    PlanStepResponse,
    ShortlistStepResponse,
)


def _reference(name: str) -> dict[str, str]:
    return {"$ref": f"#/components/schemas/{name}"}


def _request(name: str) -> dict[str, Any]:
    return {
        "required": True,
        "content": {"application/json": {"schema": _reference(name)}},
    }


def _responses(name: str) -> dict[str, Any]:
    return {
        "200": {
            "description": "Successful demo operation",
            "content": {"application/json": {"schema": _reference(name)}},
        },
        "default": {
            "description": "Safe frontend error",
            "content": {
                "application/json": {"schema": _reference("ApiErrorView")}
            },
        },
    }


def build_contract() -> dict[str, Any]:
    _, schema = models_json_schema(
        [(model, "validation") for model in MODELS],
        title="Hobbi frontend API",
    )
    components = schema["$defs"]
    encoded = json.dumps(components).replace("#/$defs/", "#/components/schemas/")
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Hobbi demo frontend API",
            "version": "1.0.0",
            "description": (
                "A same-origin browser contract. Trusted-adult credentials stay in "
                "the Next.js server layer; the teen access token is held in an "
                "HttpOnly cookie."
            ),
        },
        "servers": [{"url": "http://127.0.0.1:3000"}],
        "paths": {
            "/api/health": {
                "get": {
                    "operationId": "getHealth",
                    "responses": _responses("HealthView"),
                }
            },
            "/api/plan": {
                "post": {
                    "operationId": "createPlan",
                    "requestBody": _request("DemoSetupRequest"),
                    "responses": _responses("ShortlistStepResponse"),
                }
            },
            "/api/approve": {
                "post": {
                    "operationId": "approvePlan",
                    "requestBody": _request("DemoApproveRequest"),
                    "responses": _responses("BookingStepResponse"),
                }
            },
            "/api/attendance": {
                "post": {
                    "operationId": "recordAttendance",
                    "requestBody": _request("DemoAttendanceRequest"),
                    "responses": _responses("AttendanceStepResponse"),
                }
            },
            "/api/next-plan": {
                "post": {
                    "operationId": "createNextPlan",
                    "requestBody": _request("DemoNextPlanRequest"),
                    "responses": _responses("PlanStepResponse"),
                }
            },
        },
        "components": {"schemas": json.loads(encoded)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_contract(), indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.out.exists() or args.out.read_text() != rendered:
            raise SystemExit(f"frontend contract is stale: regenerate {args.out}")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(rendered)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
