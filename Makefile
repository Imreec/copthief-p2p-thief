# Quality gates — mirror of .github/workflows/quality.yml. Run `make grade` before every PR.

.PHONY: lint format-check type test sizes patterns hardcoded sync-verify submission grade

lint:
	uv run ruff check .

format-check:
	uv run ruff format --check .

type:
	uv run mypy src/

test:
	uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=85

sizes:
	uv run python scripts/check_file_sizes.py

patterns:
	uv run python scripts/check_anti_patterns.py

hardcoded:
	uv run python scripts/check_no_hardcoded.py

sync-verify:
	uv run python scripts/sync_core.py --verify

submission:
	uv run python scripts/check_submission.py

grade: lint format-check type sizes patterns hardcoded sync-verify test submission
	uv run python scripts/self_grade.py --validate
	@echo "ALL GATES GREEN"
