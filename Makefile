.PHONY: install
install: ## install dependencies
	uv sync --all-groups
	pre-commit install

.PHONY: lint
lint: ## lint code
	pre-commit

.PHONY: test
test: ## run all tests
	uv run pytest
