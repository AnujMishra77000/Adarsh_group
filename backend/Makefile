.PHONY: compile lint test

compile:
	python -m compileall app

lint:
	ruff check app tests

test:
	pytest
