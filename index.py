"""Vercel serverless entry point."""
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from api.index import app  # noqa: F401, E402
