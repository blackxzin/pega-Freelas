#!/usr/bin/env python3
"""Start the local FreelaHunter operator panel."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from freelahunter.operator_panel import serve_operator_panel


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Painel local para alternar 99Freelas e Upwork")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve_operator_panel(args.host, args.port)
