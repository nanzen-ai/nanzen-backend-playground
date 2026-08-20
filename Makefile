.PHONY: install style test run serve reset

install:
	uv sync --all-extras

style:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

test:
	uv run pytest -v

run:
	uv run python -m challenge.runner $(ARGS)

reset:
	uv run python -m challenge.runner reset

serve:
	uv run uvicorn challenge.api:app --reload --port 8000
