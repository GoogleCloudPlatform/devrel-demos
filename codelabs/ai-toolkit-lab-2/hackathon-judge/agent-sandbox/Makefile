# Python parameters
UV=uv

.PHONY: all test setup run lint clean

all: setup lint test

setup:
	$(UV) sync

test:
	$(UV) run pytest

run:
	$(UV) run uvicorn app.main:app --reload

lint:
	# Add linting command if/when a linter like ruff is added
	@echo "No linter configured for agent-sandbox yet."

clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
