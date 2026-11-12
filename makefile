# Makefile for Forge Application
APP_NAME := $(shell grep '^name' pyproject.toml | head -1 | cut -d '"' -f2)
APP_ALIAS := 武穆
APP_VERS := $(shell grep '^version' pyproject.toml | head -1 | cut -d '"' -f2)
APP_PATH := $(abspath .)
ENV_NAME := $(APP_NAME)
ENV_FILE := environment.yml


env:
	@echo "[$(APP_NAME)@$(APP_ALIAS)] setting up env '$(ENV_NAME)' from '$(ENV_FILE)' ..."
	@if ! conda env list | grep -qE "^$(ENV_NAME)[[:space:]]"; then \
		echo "[$(APP_NAME)@$(APP_ALIAS)] create env '$(ENV_NAME)'"; \
		conda env create -f $(ENV_FILE); \
	else \
		echo "[$(APP_NAME)@$(APP_ALIAS)] update env '$(ENV_NAME)'"; \
		conda env update -n $(ENV_NAME) -f $(ENV_FILE); \
	fi
	@echo "[$(APP_NAME)@$(APP_ALIAS)] env setup OK ✅ "
	@echo "[$(APP_NAME)@$(APP_ALIAS)] activate by 'conda activate $(ENV_NAME)'"

install:
	@echo "[$(APP_NAME)@$(APP_ALIAS)] installing (pyproject.toml) ..."
	@conda run -n $(ENV_NAME) python -m pip install --upgrade pip
	@conda run -n $(ENV_NAME) sh -c 'python -m pip install ".[dev]"'
	@pip install .
	@pip install .[dev]
	@echo "[$(APP_NAME)@$(APP_ALIAS)] 'dependencies' installed ✅ "

upgrade:
	@echo "[$(APP_NAME)@$(APP_ALIAS)] upgrading (pyproject.toml) ..."
	@conda run -n $(ENV_NAME) python -m pip install --upgrade pip
	@conda run -n $(ENV_NAME) sh -c 'python -m pip install --upgrade ".[dev]"'
	@pip install --upgrade .
	@pip install --upgrade .[dev]
	@echo "[$(APP_NAME)@$(APP_ALIAS)] 'dependencies' upgraded ✅ "

clean:
	@rm -rf build dist *.egg-info
	@echo "[$(APP_NAME)@$(APP_ALIAS)] 'build artifacts' cleaned ✅ "

	@rm -rf .pytest_cache
	@echo "[$(APP_NAME)@$(APP_ALIAS)] 'pytest caches' cleaned ✅ "

	@rm -rf .ruff_cache
	@rm -rf .benchmarks
	@rm -rf .mypy_cache
	@echo "[$(APP_NAME)@$(APP_ALIAS)] 'ruff/benchmarks caches' cleaned ✅ "

	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".DS_Store" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@echo "[$(APP_NAME)@$(APP_ALIAS)] 'python caches' cleaned ✅ "

lint:
	@ruff format .
	@ruff check . --fix
	@ruff check .
	@echo "[$(APP_NAME)@$(APP_ALIAS)] 'library' lint checked ✅"


start:
	@echo "[$(APP_NAME)@$(APP_ALIAS)] starting node ..."
	@forge up
	@echo "[$(APP_NAME)@$(APP_ALIAS)] node started ✅ "
