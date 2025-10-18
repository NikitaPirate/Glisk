"""CLI entry point for glisk.cli module.

Enables execution via: python -m glisk.cli.recover_tokens
"""

from glisk.cli.recover_tokens import main

if __name__ == "__main__":
    raise SystemExit(main())
