#!/usr/bin/env python3
"""Compatibility wrapper for the refactored verifier package."""
# The socket and urllib imports also keep those module names available on verify_recruiter for existing tests.
import socket
import urllib

from verifier import *  # noqa: F401,F403
from verifier.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
