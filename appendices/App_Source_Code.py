"""Appendix reference for the implemented application.

The executable and authoritative application is ../app.py. Keeping a second copy
would allow the submitted appendix to drift from the tested implementation.
"""

from pathlib import Path

CANONICAL_SOURCE = Path(__file__).resolve().parents[1] / "app.py"


def read_canonical_source() -> str:
    """Return the exact source code used by the submitted Streamlit application."""
    return CANONICAL_SOURCE.read_text(encoding="utf-8")


if __name__ == "__main__":
    print(read_canonical_source())
