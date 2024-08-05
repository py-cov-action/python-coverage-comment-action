.PHONY: install
install: ## install dependencies
	poetry install --with dev
	pre-commit install

.PHONY: lint
lint: ## lint code
	pre-commit

.PHONY: test
test: ## run all tests
	poetry run pytest tests
