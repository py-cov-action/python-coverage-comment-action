.PHONY: install
install: ## install dependencies
	uv sync
	pre-commit install

.PHONY: lint
lint: ## lint code
	pre-commit

.PHONY: test
test: ## run all tests
	uv run pytest tests
