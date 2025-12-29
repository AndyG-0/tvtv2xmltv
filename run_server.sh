#!/bin/bash
# Load environment variables from .env and run the server
set -a  # automatically export all variables
source .env
set +a
uv run python src/main.py --mode serve
