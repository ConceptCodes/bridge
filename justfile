set shell := ["zsh", "-cu"]

default: check

run:
    uv run python main.py

lint:
    uv run ruff check .

format:
    uv run ruff format .

check:
    uv run ruff check .
    uv run ruff format --check .
