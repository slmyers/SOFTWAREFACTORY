.PHONY: lint format fix precommit-install precommit-run

lint:
	python -m ruff check .

format:
	python -m black .
	python -m isort .

fix:
	python -m ruff check --fix .
	python -m isort .
	python -m black .

precommit-install:
	pre-commit install

precommit-run:
	pre-commit run --all-files
