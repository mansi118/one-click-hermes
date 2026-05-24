# NeuralEDGE Agent — Make targets.
# All commands are also runnable directly with docker compose; the Makefile
# just gives them stable names so runbooks don't drift.

SHELL          := /usr/bin/env bash
COMPOSE_FILE   := docker-compose.neuraledge.yml
COMPOSE        := docker compose -f $(COMPOSE_FILE)
STATE_DIR      := $(HOME)/.hermes
BACKUP_DIR     := $(HOME)/hermes-backups
DATE           := $(shell date +%Y%m%d-%H%M%S)

# Tag the upstream remote sync uses. Override on CLI: `make sync-upstream UPSTREAM_BRANCH=main`
UPSTREAM_BRANCH ?= main
LOCAL_BRANCH    ?= neuraledge

.DEFAULT_GOAL := help

## ──────────────────────────────────────────────────────────────────────────
##  Lifecycle
## ──────────────────────────────────────────────────────────────────────────

.PHONY: install
install: ## Run the one-click installer (idempotent)
	bash neuraledge/install.sh

.PHONY: up
up: ## Start hermes + cortex-mcp (detached)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop and remove containers (state in ~/.hermes preserved)
	$(COMPOSE) down

.PHONY: restart
restart: ## Restart all services
	$(COMPOSE) restart

.PHONY: build
build: ## Rebuild images (use after editing branding/skills/MCP code)
	$(COMPOSE) build

.PHONY: pull
pull: ## Pull pre-built images (v1.1+; no-op when using local build)
	$(COMPOSE) pull

## ──────────────────────────────────────────────────────────────────────────
##  Observability
## ──────────────────────────────────────────────────────────────────────────

.PHONY: logs
logs: ## Follow hermes logs (secrets redacted)
	$(COMPOSE) logs -f hermes

.PHONY: logs-cortex
logs-cortex: ## Follow cortex-mcp logs
	$(COMPOSE) logs -f cortex-mcp

.PHONY: ps
ps: ## Show container status
	$(COMPOSE) ps

.PHONY: doctor
doctor: ## Run `hermes doctor` inside the agent
	$(COMPOSE) exec hermes hermes doctor

.PHONY: cortex-status
cortex-status: ## Check CORTEX-PALACE bridge health
	$(COMPOSE) exec cortex-mcp python -m cortex_mcp.healthcheck

## ──────────────────────────────────────────────────────────────────────────
##  Operator workflow
## ──────────────────────────────────────────────────────────────────────────

.PHONY: shell
shell: ## Drop into a shell inside the agent container
	$(COMPOSE) exec hermes /bin/bash || $(COMPOSE) exec hermes /bin/sh

.PHONY: setup
setup: ## Re-run the Hermes setup wizard
	$(COMPOSE) run --rm hermes hermes setup

.PHONY: skills-list
skills-list: ## List loaded skills
	$(COMPOSE) exec hermes hermes skills list

.PHONY: env-edit
env-edit: ## Open ~/.hermes/.env in $EDITOR
	$${EDITOR:-vi} $(STATE_DIR)/.env

.PHONY: config-edit
config-edit: ## Open ~/.hermes/config.yaml in $EDITOR
	$${EDITOR:-vi} $(STATE_DIR)/config.yaml

## ──────────────────────────────────────────────────────────────────────────
##  Backup / restore
## ──────────────────────────────────────────────────────────────────────────

.PHONY: backup
backup: ## Tar ~/.hermes → ~/hermes-backups/hermes-<timestamp>.tar.gz
	@mkdir -p $(BACKUP_DIR)
	@tar czf $(BACKUP_DIR)/hermes-$(DATE).tar.gz -C $(HOME) .hermes
	@echo "→ $(BACKUP_DIR)/hermes-$(DATE).tar.gz"

.PHONY: restore
restore: ## Restore latest backup from ~/hermes-backups/ (asks confirmation)
	@latest=$$(ls -1t $(BACKUP_DIR)/hermes-*.tar.gz 2>/dev/null | head -n 1); \
	if [ -z "$$latest" ]; then echo "no backup found in $(BACKUP_DIR)"; exit 1; fi; \
	read -p "restore $$latest over ~/.hermes? [y/N] " ok; \
	if [ "$$ok" = "y" ]; then tar xzf "$$latest" -C $(HOME) && echo "restored"; fi

## ──────────────────────────────────────────────────────────────────────────
##  Upstream sync
## ──────────────────────────────────────────────────────────────────────────

.PHONY: sync-upstream
sync-upstream: ## Pull upstream Hermes and merge into the neuraledge branch
	@git fetch upstream
	@git checkout $(UPSTREAM_BRANCH)
	@git pull upstream $(UPSTREAM_BRANCH)
	@git checkout $(LOCAL_BRANCH)
	@git merge $(UPSTREAM_BRANCH) || ( \
	  echo "merge had conflicts — check NEURALEDGE_PATCHES.md for re-apply recipe"; \
	  exit 1 )
	@echo "synced; rebuild with 'make build' and verify with 'make doctor'"

## ──────────────────────────────────────────────────────────────────────────
##  Dev (cortex-mcp)
## ──────────────────────────────────────────────────────────────────────────

.PHONY: cortex-test
cortex-test: ## Run cortex-mcp tests inside the container
	$(COMPOSE) exec cortex-mcp python -m pytest -q || \
	  ( cd neuraledge/mcp/cortex-palace && python -m pytest -q )

.PHONY: cortex-lint
cortex-lint: ## Lint cortex-mcp
	cd neuraledge/mcp/cortex-palace && ruff check .

## ──────────────────────────────────────────────────────────────────────────
##  Help
## ──────────────────────────────────────────────────────────────────────────

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nNeuralEDGE Agent — make targets\n"} \
	  /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 } \
	  /^##/ { sub("##", ""); printf "%s\n", $$0 }' $(MAKEFILE_LIST)
