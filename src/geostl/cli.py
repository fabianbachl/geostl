"""Command-line entry point (``geostl``). A thin wrapper over the library API."""
from __future__ import annotations

import argparse
from typing import Optional, Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="geostl",
        description="Turn public elevation data into 3D-printable terrain STL.",
    )
    parser.add_argument(
        "--version", action="store_true", help="print the geostl version and exit"
    )
    # Full `section` / `grid` subcommands are upcoming.
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.version:
        from geostl import __version__

        print(__version__)
        return 0
    print("geostl CLI is not implemented yet. See the geostl documentation for the roadmap.")
    return 0
