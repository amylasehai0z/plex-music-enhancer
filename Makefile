.PHONY: install format lint test coverage validate benchmark clean

install:
	python -m pip install --upgrade pip
	python -m pip install ".[dev,ai,metadata]"

format:
	black .

lint:
	ruff check .

test:
	pytest

coverage:
	pytest --cov

validate: format lint test

benchmark:
	plex-enhancer benchmark

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build
