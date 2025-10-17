"""CLI entry point for glisk.cli module.

Enables execution via: python -m glisk.cli.recover_events
"""

from glisk.cli.recover_events import main

if __name__ == "__main__":
    raise SystemExit(main())
