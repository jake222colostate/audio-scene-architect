#!/usr/bin/env bash
set -e

# Check Python version
python_version=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
required_version=3.8
if [[ $(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1) != "$required_version" ]]; then
  echo "Python $required_version or higher is required. Current version: $python_version" >&2
  exit 1
fi

# Create virtual environment if not exists
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r backend/requirements.txt

echo "Dependencies installed into .venv"

