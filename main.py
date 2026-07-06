#!/usr/bin/env python3
"""
main.py – Entry point for the Startup Blueprint Generator.

Usage
-----
  python main.py
  python main.py --idea "An AI-powered personal finance coach for Gen-Z"
  python main.py --idea "..." --industry "FinTech" --stage "idea"
  python main.py --idea "..." --verbose
"""

from __future__ import annotations

import argparse
import logging
import sys

from startup_blueprint.config import load_config
from startup_blueprint.planner_agent import StartupPlannerAgent

# ──────────────────────────────────────────────────────────────────────────────
# Default startup idea shown when the user does not pass --idea
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_IDEA = (
    "An AI-powered personal finance coach for Gen-Z that analyses spending "
    "patterns, sets savings goals, and gamifies financial literacy through "
    "a mobile app integrated with open banking APIs."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Startup Blueprint Generator — powered by IBM watsonx Orchestrate"
    )
    parser.add_argument(
        "--idea",
        type=str,
        default=DEFAULT_IDEA,
        help="Startup idea to analyse (wrap in quotes).",
    )
    parser.add_argument(
        "--industry",
        type=str,
        default=None,
        help="Optional industry tag forwarded as context (e.g. 'FinTech').",
    )
    parser.add_argument(
        "--stage",
        type=str,
        default=None,
        choices=["idea", "mvp", "growth", "scale"],
        help="Optional startup stage forwarded as context.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=3.0,
        help="Seconds between result-polling calls (default: 3).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser.parse_args()


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )


def build_context(args: argparse.Namespace) -> dict | None:
    ctx: dict = {}
    if args.industry:
        ctx["industry"] = args.industry
    if args.stage:
        ctx["stage"] = args.stage
    return ctx or None


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║       Startup Blueprint Generator — watsonx Orchestrate  ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # ── Load config (raises EnvironmentError if .env is incomplete) ─────
    try:
        config = load_config()
    except EnvironmentError as exc:
        print(f"[CONFIG ERROR] {exc}", file=sys.stderr)
        return 1

    # ── Run the Startup Planner Agent ────────────────────────────────────
    agent = StartupPlannerAgent(config)
    context = build_context(args)

    print(f"Startup Idea: {args.idea}\n")
    if context:
        print(f"Additional Context: {context}\n")
    print("Contacting Startup Planner Agent …\n")

    try:
        result = agent.run(
            startup_idea=args.idea,
            additional_context=context,
            poll_interval=args.poll_interval,
        )
    except EnvironmentError as exc:
        print(f"[AUTH ERROR] {exc}", file=sys.stderr)
        return 1
    except TimeoutError as exc:
        print(f"[TIMEOUT] {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"[AGENT ERROR] {exc}", file=sys.stderr)
        return 3
    except Exception as exc:  # noqa: BLE001
        print(f"[UNEXPECTED ERROR] {exc}", file=sys.stderr)
        return 99

    # ── Display the result ───────────────────────────────────────────────
    print(result)

    # ── Persist to file ──────────────────────────────────────────────────
    output_file = "planner_output.txt"
    with open(output_file, "w", encoding="utf-8") as fh:
        fh.write(str(result))
    print(f"✓ Plan saved to: {output_file}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
