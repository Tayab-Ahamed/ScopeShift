#!/usr/bin/env python3
"""ScopeShift Demo Launcher.

Starts the ScopeShift demo server, waits for /api/health to confirm
successful initialization, opens the interface in the default web browser,
and monitors the server process.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def wait_for_health(host: str, port: int, timeout: float = 15.0) -> bool:
    """Polls /api/health until the server is responsive or timeout expires."""
    url = f"http://{host}:{port}/api/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ScopeShift-Launcher/1.0"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    if data.get("status") == "ok":
                        return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def run_demo(
    host: str = "127.0.0.1",
    port: int = 8765,
    no_browser: bool = False,
    safe_mode: bool = False,
) -> int:
    env = os.environ.copy()
    env["HOST"] = host
    env["PORT"] = str(port)
    if safe_mode:
        env["SCOPESHIFT_SAFE_MODE"] = "1"

    print("=" * 60)
    print("           Starting ScopeShift Demo Environment")
    print("=" * 60)
    print(f"Target URL: http://{host}:{port}")
    if safe_mode:
        print("Demo Safe Mode: ACTIVE (deterministic offline route enforced)")

    cmd = [sys.executable, str(ROOT / "demo_server.py")]
    proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env)

    try:
        print("Waiting for ScopeShift server healthcheck (/api/health)...")
        healthy = wait_for_health(host, port, timeout=15.0)

        if not healthy:
            print("Error: Server failed to become healthy within 15 seconds.", file=sys.stderr)
            proc.terminate()
            return 1

        print(f"Server healthy! Ready at http://{host}:{port}")

        if not no_browser:
            print("Opening browser...")
            webbrowser.open(f"http://{host}:{port}")

        print("\nScopeShift is running. Press Ctrl+C to stop.")
        proc.wait()
        return proc.returncode or 0

    except KeyboardInterrupt:
        print("\nStopping ScopeShift demo server...")
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("ScopeShift demo stopped cleanly.")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Launch ScopeShift presentation demo")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Bind port (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    parser.add_argument("--safe-mode", action="store_true", help="Force deterministic safe mode")
    args = parser.parse_args()

    sys.exit(run_demo(host=args.host, port=args.port, no_browser=args.no_browser, safe_mode=args.safe_mode))
