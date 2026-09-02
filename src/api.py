"""Local JSON API and AgentCore-ready callable seam."""

from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import sqlite3
import threading
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import UTC, datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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
from src.store.personal_data import (
    PersonalDataError,
    PersonalDataStore,
)
from src.validation.orchestrator import GateValidationError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_DIR = ROOT / ".hobbi"
MAX_REQUEST_BYTES = 1_000_000
COMPLIANCE_USER_AGENT = "hobbi-compliance/1.0"


class ApiAuthorizationError(PermissionError):
    pass


class RequestTooLargeError(ValueError):
    pass


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _robots_allows(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    request = urllib.request.Request(
        robots_url, method="GET", headers={"User-Agent": COMPLIANCE_USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = response.read(MAX_REQUEST_BYTES + 1)
            if response.status >= 400 or len(body) > MAX_REQUEST_BYTES:
                return False
    except urllib.error.HTTPError as exc:
        try:
            return exc.code in {404, 410}
        finally:
            exc.close()
    except (OSError, TimeoutError, ValueError, urllib.error.URLError):
        return False
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(body.decode("utf-8", errors="replace").splitlines())
    return parser.can_fetch(COMPLIANCE_USER_AGENT, url)


def _source_status(url: str) -> str:
    if not _robots_allows(url):
        return "transient"
    request = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": COMPLIANCE_USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return "alive" if response.status < 400 else "transient"
    except urllib.error.HTTPError as exc:
        try:
            return "missing" if exc.code in {404, 410} else "transient"
        finally:
            exc.close()
    except (OSError, TimeoutError, ValueError, urllib.error.URLError):
        return "transient"


class HobbiService:
    def __init__(
        self,
        runtime_dir: str | Path = DEFAULT_RUNTIME_DIR,
        *,
        guardian_token: str | None = None,
        compliance_token: str | None = None,
        seed_artifact: str | Path | None = ROOT / "data" / "seed_ckb.json",
    ) -> None:
        directory = Path(runtime_dir)
        directory.mkdir(parents=True, exist_ok=True)
        self.personal_data = PersonalDataStore(directory / "personal-data.sqlite")
        self.guardian_token = guardian_token or os.getenv("HOBBI_GUARDIAN_API_TOKEN", "")
        self.compliance_token = compliance_token or os.getenv("HOBBI_COMPLIANCE_API_TOKEN", "")
        self.ckb = KnowledgeBase(directory / "ckb.sqlite")
        artifact = Path(seed_artifact) if seed_artifact is not None else None
        if artifact is not None and artifact.exists() and not self.ckb.all():
            self.ckb.seed_from_artifact(artifact)
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
            "rejection_history": [],
            "binding_constraint": None,
            "resume_approved_plan": False,
            "booking_records": [],
            "replan_count": 0,
            "discovery_rounds": 0,
            "guardian_rejects": 0,
            "gate_log": [gate],
            "token_usage": [],
            "unavailable_listing_ids": [],
            "outcome": None,
        }

    @staticmethod
    def _require_role(expected: str, supplied: str | None, role: str) -> None:
        if not expected or supplied is None or not hmac.compare_digest(expected, supplied):
            raise ApiAuthorizationError(f"valid {role} authorization is required")

    def _require_profile(self, teen_id: str, supplied: str | None) -> None:
        if supplied is None or not self.personal_data.authorize_profile_access(
            teen_id, supplied
        ):
            raise ApiAuthorizationError("valid teen profile authorization is required")

    def _state_for_existing_profile(self, teen_id: str, thread_id: str) -> HobbiState:
        identity = self.personal_data.profile_identity(teen_id)
        snapshot = self.personal_data.planner_snapshot(teen_id)
        return {
            "teen_id": teen_id,
            "thread_id": thread_id,
            "declared_age": identity["declared_age"],
            "intake_result": IntakeResult(eligible=True, reason="eligible"),
            "request": snapshot["request"],
            "ledger": snapshot["ledger"],
            "candidate_plan": None,
            "approved_plan": None,
            "guardian_verdict": None,
            "rejection_history": [],
            "binding_constraint": None,
            "resume_approved_plan": False,
            "booking_records": [],
            "replan_count": 0,
            "discovery_rounds": 0,
            "guardian_rejects": 0,
            "gate_log": [],
            "token_usage": [],
            "unavailable_listing_ids": [],
            "outcome": None,
        }

    def handle(
        self, payload: dict[str, Any], *, authorization: str | None = None
    ) -> dict[str, Any]:
        operation = payload.get("operation")
        if operation == "health":
            records = self.ckb.all()
            usable_real = [
                record
                for record in records
                if not record.is_fictional
                and record.verification != "retired"
                and record.freshness_state != "dead"
            ]
            return {
                "ok": True,
                "service": "hobbi",
                "ready_for_real_planning": bool(usable_real),
                "ckb_records": len(records),
                "ckb_usable_real_records": len(usable_real),
                "ckb_verified_real_records": sum(
                    record.verification == "verified" for record in usable_real
                ),
                "ckb_unverified_real_records": sum(
                    record.verification == "unverified" for record in usable_real
                ),
                "ckb_fictional_records": sum(record.is_fictional for record in records),
                "ckb_unusable_records": len(records) - len(usable_real),
            }
        if operation == "discovery_replay":
            self._require_role(self.compliance_token, authorization, "operator")
            from src.schema.plan import Plan

            plan = Plan.model_validate(payload["plan"])
            result = Discovery().cached_replay(
                plan, ROOT / "data" / "discovery_replay.json", self.ckb
            )
            return {"ok": True, "result": _jsonable(result)}
        if operation == "intake_and_plan":
            self._require_role(self.guardian_token, authorization, "trusted-adult")
            setup_input = SetupInput.model_validate(payload["setup"])
            intake_result = setup(setup_input, self.personal_data)
            response: dict[str, Any] = {
                "ok": intake_result.gate.passed,
                "intake": _jsonable(intake_result),
            }
            if intake_result.persisted:
                teen_access_token = secrets.token_urlsafe(32)
                self.personal_data.set_profile_access_token(
                    setup_input.teen_id, teen_access_token
                )
                final = self.runtime.invoke(
                    self._initial_state(
                        setup_input, intake_result.intake, intake_result.gate
                    )
                )
                response["state"] = _jsonable(final)
                response["teen_access_token"] = teen_access_token
                response["ok"] = final["outcome"] not in {
                    "no_viable_plan",
                    "cap_breached",
                }
                if not response["ok"]:
                    response["notification_required"] = ["trusted_adult"]
            return response
        if operation == "guardian_approve":
            self._require_role(self.guardian_token, authorization, "trusted-adult")
            teen_id = str(payload["teen_id"])
            plan_id = str(payload["plan_id"])
            self.personal_data.issue_plan_approvals(
                teen_id=teen_id,
                plan_id=plan_id,
                provider_approval_ids={
                    str(key): str(value)
                    for key, value in payload.get("provider_approval_ids", {}).items()
                },
                attendance_approval_id=payload.get("attendance_approval_id"),
                spend_approval_id=payload.get("spend_approval_id"),
                spend_ceiling_sgd=(
                    Decimal(str(payload["spend_ceiling_sgd"]))
                    if payload.get("spend_ceiling_sgd") is not None
                    else None
                ),
            )
            rerun_thread = f"approval:{teen_id}:{plan_id}:{secrets.token_hex(8)}"
            approved_plan = self.personal_data.get_plan(teen_id, plan_id)
            rerun_state = self._state_for_existing_profile(teen_id, rerun_thread)
            rerun_state["candidate_plan"] = approved_plan
            rerun_state["resume_approved_plan"] = True
            final = self.runtime.invoke(rerun_state)
            response = {
                "ok": final["outcome"] not in {"no_viable_plan", "cap_breached"},
                "state": _jsonable(final),
            }
            if not response["ok"]:
                response["notification_required"] = ["trusted_adult"]
            return response
        if operation == "attendance":
            teen_id = str(payload["teen_id"])
            self._require_profile(teen_id, authorization)
            event = AttendanceEvent.model_validate(payload["event"])
            submission = (
                DebriefSubmission.model_validate(payload["debrief"])
                if payload.get("debrief") is not None
                else None
            )
            snapshot = self.personal_data.planner_snapshot(teen_id)
            booking = self.personal_data.require_booking_owner(teen_id, event.booking_id)
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
            self._require_role(self.compliance_token, authorization, "compliance")
            result = Compliance().scan(
                ckb=self.ckb,
                personal_data=self.personal_data,
                source_status=_source_status,
                now=datetime.now(UTC),
            )
            replans: list[dict[str, Any]] = []
            if payload.get("replan_flagged"):
                for flagged in result.flagged_plans:
                    teen_id = flagged["teen_id"]
                    state = self._state_for_existing_profile(
                        teen_id,
                        f"compliance:{teen_id}:{secrets.token_hex(8)}",
                    )
                    state["unavailable_listing_ids"] = result.retired_listing_ids
                    replanned = self.runtime.invoke(state)
                    replans.append(
                        {
                            "teen_id": teen_id,
                            "state": _jsonable(replanned),
                            "notification_required": ["teen", "trusted_adult"],
                        }
                    )
            return {"ok": True, "result": _jsonable(result), "replans": replans}
        return {
            "ok": False,
            "error": "unknown_operation",
            "action": (
                "use health, discovery_replay, intake_and_plan, guardian_approve, "
                "attendance, or compliance_scan"
            ),
        }


_service: HobbiService | None = None
_service_lock = threading.Lock()


def app_entrypoint(
    payload: dict[str, Any], *, authorization: str | None = None
) -> dict[str, Any]:
    """Callable seam suitable for wrapping with ``@app.entrypoint`` in AgentCore."""

    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = HobbiService(
                    os.getenv("HOBBI_RUNTIME_DIR", str(DEFAULT_RUNTIME_DIR))
                )
    try:
        return _service.handle(payload, authorization=authorization)
    except sqlite3.IntegrityError:
        return {
            "ok": False,
            "error": "stored_state_conflict",
            "action": "request conflicts with existing stored state",
        }
    except (
        ApiAuthorizationError,
        GateValidationError,
        KeyError,
        PermissionError,
        PersonalDataError,
        ValidationError,
        ValueError,
    ) as exc:
        return {"ok": False, "error": type(exc).__name__, "action": str(exc)}


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > MAX_REQUEST_BYTES:
                raise RequestTooLargeError
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path != "/":
                response = {"ok": False, "error": "not_found", "action": "POST JSON to /"}
                status = 404
            else:
                header = self.headers.get("Authorization", "")
                authorization = header.removeprefix("Bearer ") or None
                response = app_entrypoint(payload, authorization=authorization)
                status = 200 if response.get("ok") else (
                    401 if response.get("error") == "ApiAuthorizationError" else 400
                )
        except RequestTooLargeError:
            response = {
                "ok": False,
                "error": "request_too_large",
                "action": f"limit the request body to {MAX_REQUEST_BYTES} bytes",
            }
            status = 413
        except ValueError:
            response = {
                "ok": False,
                "error": "invalid_request",
                "action": "send a valid JSON object with an exact Content-Length",
            }
            status = 400
        except Exception:  # noqa: BLE001 - HTTP boundary must not leak internals
            response = {
                "ok": False,
                "error": "internal_error",
                "action": "inspect server logs and retry with a valid typed request",
            }
            status = 500
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
