.PHONY: install
install: ## install dependencies
	uv sync --all-groups
	prek install

.PHONY: lint
lint: ## lint code
	prek

.PHONY: test
test: ## run all tests
	uv run pytest
