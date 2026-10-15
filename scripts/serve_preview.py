#!/usr/bin/env python3
"""Serve the experimental MiniRouter preview on a loopback interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from minirouter.api import DEFAULT_BUNDLE, LOOPBACK_HOSTS, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    if args.host.casefold() not in LOOPBACK_HOSTS:
        parser.error("--host must be localhost, 127.0.0.1, or ::1")
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    try:
        import uvicorn
    except ImportError as exc:
        parser.error(f"FastAPI preview dependencies are missing: {exc.name}; install requirements-runtime.txt")

    app = create_app(args.bundle)
    print(f"MiniRouter experimental preview: http://{args.host}:{args.port}/", flush=True)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
