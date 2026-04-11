import sys
import os

# Ensure the backend root (/app in container) is on sys.path so that
# `from app.services... import ...` resolves correctly regardless of
# how pytest inserts paths when __init__.py files are present.
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)
