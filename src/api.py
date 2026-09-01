"""Local JSON API and AgentCore-ready callable seam."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from src.agents.compliance import Compliance
from src.agents.discovery import Discovery
from src.agents.observer import Observer
from src.ckb.store import KnowledgeBase
from src.graph import HobbiRuntime
from src.intake import SetupInput, setup
from src.schema.events import AttendanceEvent, DebriefSubmission
from src.schema.plan import IntakeResult
from src.schema.state import HobbiState
from src.store.personal_data import PersonalDataError, PersonalDataStore

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = ROOT / ".hobbi"


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _source_alive(url: str) -> bool:
    request = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": "hobbi-compliance/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status < 400
    except (OSError, TimeoutError, ValueError, urllib.error.URLError):
        return False


class HobbiService:
    def __init__(self, runtime_dir: str | Path = DEFAULT_RUNTIME_DIR) -> None:
        directory = Path(runtime_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self.personal_data = PersonalDataStore(directory / "personal-data.sqlite")
        self.ckb = KnowledgeBase(directory / "ckb.sqlite")
        seed_artifact = ROOT / "data" / "seed_ckb.json"
        if seed_artifact.exists() and not self.ckb.all():
            self.ckb.seed_from_artifact(seed_artifact)
        self.runtime = HobbiRuntime(
            personal_data=self.personal_data,
            ckb=self.ckb,
            checkpoint_path=directory / "checkpoints.sqlite",
            discovery_replay_path=ROOT / "data" / "discovery_replay.json",
        )

    def close(self) -> None:
        self.runtime.close()
        self.ckb.close()
        self.personal_data.close()

    def _initial_state(self, setup_input: SetupInput, intake: IntakeResult, gate: Any) -> HobbiState:
        return {
            "teen_id": setup_input.teen_id,
            "thread_id": setup_input.thread_id,
            "declared_age": setup_input.declared_age,
            "intake_result": intake,
            "request": setup_input.request,
            "ledger": setup_input.ledger,
            "candidate_plan": None,
            "approved_plan": None,
            "guardian_verdict": None,
            "booking_records": [],
            "replan_count": 0,
            "discovery_rounds": 0,
            "guardian_rejects": 0,
            "gate_log": [gate],
            "token_usage": [],
            "unavailable_listing_ids": [],
            "outcome": None,
        }

    def handle(self, payload: dict[str, Any]) -> dict[str, Any]:
        operation = payload.get("operation")
        if operation == "health":
            return {"ok": True, "service": "hobbi", "ckb_records": len(self.ckb.all())}
        if operation == "discovery_replay":
            from src.schema.plan import Plan

            plan = Plan.model_validate(payload["plan"])
            result = Discovery().cached_replay(
                plan, ROOT / "data" / "discovery_replay.json", self.ckb
            )
            return {"ok": True, "result": _jsonable(result)}
        if operation == "intake_and_plan":
            setup_input = SetupInput.model_validate(payload["setup"])
            intake_result = setup(setup_input, self.personal_data)
            response: dict[str, Any] = {
                "ok": intake_result.gate.passed,
                "intake": _jsonable(intake_result),
            }
            if intake_result.persisted:
                final = self.runtime.invoke(
                    self._initial_state(
                        setup_input, intake_result.intake, intake_result.gate
                    )
                )
                response["state"] = _jsonable(final)
            return response
        if operation == "attendance":
            teen_id = str(payload["teen_id"])
            event = AttendanceEvent.model_validate(payload["event"])
            submission = (
                DebriefSubmission.model_validate(payload["debrief"])
                if payload.get("debrief") is not None
                else None
            )
            snapshot = self.personal_data.planner_snapshot(teen_id)
            booking = self.personal_data.get_booking(event.booking_id)
            listing = self.ckb.get(booking.listing_id)
            result = Observer().observe(
                teen_id=teen_id,
                event=event,
                preferences=snapshot["preferences"],
                store=self.personal_data,
                listing=listing,
                debrief=submission,
            )
            return {"ok": True, "result": _jsonable(result)}
        if operation == "compliance_scan":
            result = Compliance().scan(
                ckb=self.ckb,
                personal_data=self.personal_data,
                source_is_alive=_source_alive,
                now=datetime.now(UTC),
            )
            replans: list[dict[str, Any]] = []
            if payload.get("replan_flagged"):
                for flagged in result.flagged_plans:
                    teen_id = flagged["teen_id"]
                    identity = self.personal_data.profile_identity(teen_id)
                    snapshot = self.personal_data.planner_snapshot(teen_id)
                    state: HobbiState = {
                        "teen_id": teen_id,
                        "thread_id": identity["thread_id"],
                        "declared_age": identity["declared_age"],
                        "intake_result": IntakeResult(eligible=True, reason="eligible"),
                        "request": snapshot["request"],
                        "ledger": snapshot["ledger"],
                        "candidate_plan": None,
                        "approved_plan": None,
                        "guardian_verdict": None,
                        "booking_records": [],
                        "replan_count": 0,
                        "discovery_rounds": 0,
                        "guardian_rejects": 0,
                        "gate_log": [],
                        "token_usage": [],
                        "unavailable_listing_ids": result.retired_listing_ids,
                        "outcome": None,
                    }
                    replanned = self.runtime.invoke(state)
                    replans.append(
                        {
                            "teen_id": teen_id,
                            "path": ["retire", "Planner", "G2", "Guardian", "G3", "Broker"],
                            "state": _jsonable(replanned),
                            "notified": ["teen", "parent"],
                        }
                    )
            return {"ok": True, "result": _jsonable(result), "replans": replans}
        return {
            "ok": False,
            "error": "unknown_operation",
            "action": "use health, discovery_replay, intake_and_plan, attendance, or compliance_scan",
        }


_service: HobbiService | None = None


def app_entrypoint(payload: dict[str, Any]) -> dict[str, Any]:
    """Callable seam suitable for wrapping with ``@app.entrypoint`` in AgentCore."""

    global _service
    if _service is None:
        _service = HobbiService(os.getenv("HOBBI_RUNTIME_DIR", str(DEFAULT_RUNTIME_DIR)))
    try:
        return _service.handle(payload)
    except (KeyError, ValueError, ValidationError, PersonalDataError) as exc:
        return {"ok": False, "error": type(exc).__name__, "action": str(exc)}


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path != "/":
                response = {"ok": False, "error": "not_found", "action": "POST JSON to /"}
                status = 404
            else:
                response = app_entrypoint(payload)
                status = 200 if response.get("ok") else 400
        except Exception as exc:  # noqa: BLE001 - local HTTP trust boundary
            response = {"ok": False, "error": type(exc).__name__, "action": str(exc)}
            status = 400
        body = json.dumps(response, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Hobbi JSON API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), _Handler)
    print(f"Hobbi listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
