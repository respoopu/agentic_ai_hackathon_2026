"""Start the Hobbi Python service and Next.js frontend with one command."""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def _load_dotenv(environment: dict[str, str]) -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        environment.setdefault(key.strip(), value.strip().strip("'\""))


def _configured_guardian_token(environment: dict[str, str]) -> str:
    current = environment.get("HOBBI_GUARDIAN_API_TOKEN", "")
    if current and "replace-with" not in current:
        return current
    print("Using a temporary trusted-adult key for this local demo.")
    return secrets.token_urlsafe(32)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=8080)
    parser.add_argument("--web-port", type=int, default=3000)
    parser.add_argument("--runtime-dir", type=Path, default=ROOT / ".hobbi" / "demo")
    args = parser.parse_args()

    if shutil.which("npm") is None or not (FRONTEND / "node_modules").exists():
        print("Frontend packages are missing. Run: npm --prefix frontend install")
        return 2

    environment = os.environ.copy()
    _load_dotenv(environment)
    environment["HOBBI_GUARDIAN_API_TOKEN"] = _configured_guardian_token(environment)
    environment["HOBBI_RUNTIME_DIR"] = str(args.runtime_dir)
    environment["HOBBI_API_URL"] = f"http://{args.host}:{args.api_port}"

    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "src.api",
                "--host",
                args.host,
                "--port",
                str(args.api_port),
            ],
            cwd=ROOT,
            env=environment,
        ),
        subprocess.Popen(
            [
                "npm",
                "run",
                "dev",
                "--",
                "--hostname",
                args.host,
                "--port",
                str(args.web_port),
            ],
            cwd=FRONTEND,
            env=environment,
        ),
    ]

    stopping = False

    def stop(_signum: int | None = None, _frame: object | None = None) -> None:
        nonlocal stopping
        if stopping:
            return
        stopping = True
        for process in processes:
            if process.poll() is None:
                process.terminate()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    print(f"Hobbi demo: http://{args.host}:{args.web_port}")
    try:
        while not stopping:
            for process in processes:
                if process.poll() is not None:
                    stop()
                    break
            time.sleep(0.25)
    finally:
        stop()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
    return next((process.returncode for process in processes if process.returncode), 0)


if __name__ == "__main__":
    raise SystemExit(main())
