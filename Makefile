.DEFAULT_GOAL := help
SHELL = bash


.PHONY: help
help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## install dependencies
	poetry install --with dev
	poetry run pre-commit install

.PHONY: lint
lint: ## lint code
	poetry run ruff check --fix coverage_comment tests
	poetry run ruff format coverage_comment tests

.PHONY: test
test: ## run all tests
	poetry run pytest tests -vv --cov-report term-missing --cov=coverage_comment
