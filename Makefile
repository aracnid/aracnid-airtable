.PHONY: release-preflight
release-preflight:
	rm -rf dist build .pytest_cache .mypy_cache .ruff_cache *.egg-info
	poetry check
	poetry run pytest -q
	poetry run pyright
	poetry build
	poetry run python -m twine check dist/*
	bash scripts/release_smoke_test.sh