.PHONY: install format lint test coverage validate benchmark docs pdf handbook clean

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

docs:
	./docs/pdf/build.sh

pdf:
	./docs/pdf/build.sh

handbook:
	./docs/pdf/build.sh

clean:
	./docs/pdf/clean.sh
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build
