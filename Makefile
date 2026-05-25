# NeuralEDGE Agent — Make targets.
# Thin wrappers around `docker compose` so runbook commands stay stable.
#
# Compose is invoked as an overlay: upstream's docker-compose.yml defines
# gateway+dashboard; docker-compose.neuraledge.yml adds cortex-mcp.

SHELL          := /usr/bin/env bash
COMPOSE_FILES  := -f docker-compose.yml -f docker-compose.neuraledge.yml
COMPOSE        := docker compose $(COMPOSE_FILES)
STATE_DIR      := $(HOME)/.hermes
BACKUP_DIR     := $(HOME)/hermes-backups
DATE           := $(shell date +%Y%m%d-%H%M%S)

# Upstream tag we pin to. Override on CLI: `make sync-upstream UPSTREAM_TAG=v2026.7.x`
UPSTREAM_TAG    ?= v2026.5.16
# Production branch (carries the NeuralEDGE overlay).
LOCAL_BRANCH    ?= neuraledge
# Pure-upstream mirror branch. Always reset to UPSTREAM_TAG; never holds NE files.
UPSTREAM_BRANCH ?= main

.DEFAULT_GOAL := help

## ──────────────────────────────────────────────────────────────────────────
##  Lifecycle
## ──────────────────────────────────────────────────────────────────────────

.PHONY: install
install: ## Run the one-click installer (idempotent)
	bash neuraledge/install.sh

.PHONY: up
up: ## Start gateway + dashboard + cortex-mcp (detached)
	$(COMPOSE) up -d

.PHONY: down
down: ## Stop and remove containers (state in ~/.hermes preserved)
	$(COMPOSE) down

.PHONY: restart
restart: ## Restart all services
	$(COMPOSE) restart

.PHONY: build
build: ## Rebuild images (use after editing skill content or MCP bridge code)
	$(COMPOSE) build

.PHONY: pull
pull: ## Pull pre-built images where available
	$(COMPOSE) pull

## ──────────────────────────────────────────────────────────────────────────
##  Observability
## ──────────────────────────────────────────────────────────────────────────

.PHONY: logs
logs: ## Follow gateway logs (secrets redacted by Hermes)
	$(COMPOSE) logs -f gateway

.PHONY: logs-cortex
logs-cortex: ## Follow cortex-mcp logs
	$(COMPOSE) logs -f cortex-mcp

.PHONY: logs-dashboard
logs-dashboard: ## Follow dashboard logs
	$(COMPOSE) logs -f dashboard

.PHONY: ps
ps: ## Show container status
	$(COMPOSE) ps

.PHONY: doctor
doctor: ## Run `hermes doctor` inside the gateway — the only green/red signal that counts
	$(COMPOSE) exec gateway hermes doctor

.PHONY: cortex-status
cortex-status: ## Check CORTEX-PALACE bridge health
	$(COMPOSE) exec cortex-mcp python -m cortex_mcp.healthcheck

## ──────────────────────────────────────────────────────────────────────────
##  Operator workflow
## ──────────────────────────────────────────────────────────────────────────

.PHONY: shell
shell: ## Drop into a shell inside the gateway container
	$(COMPOSE) exec gateway /bin/bash || $(COMPOSE) exec gateway /bin/sh

.PHONY: setup
setup: ## Re-run the Hermes setup wizard
	$(COMPOSE) run --rm gateway hermes setup

.PHONY: skills
skills: ## Interactive skill enable/disable (curses UI)
	$(COMPOSE) exec gateway hermes skills config

.PHONY: env-edit
env-edit: ## Open ~/.hermes/.env in $$EDITOR
	$${EDITOR:-vi} $(STATE_DIR)/.env

.PHONY: config-edit
config-edit: ## Open ~/.hermes/config.yaml in $$EDITOR
	$${EDITOR:-vi} $(STATE_DIR)/config.yaml

.PHONY: soul-edit
soul-edit: ## Open ~/.hermes/SOUL.md (Neural's persona) in $$EDITOR
	$${EDITOR:-vi} $(STATE_DIR)/SOUL.md

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
##  Upstream sync (pinned to release tag for reproducibility)
## ──────────────────────────────────────────────────────────────────────────

.PHONY: sync-upstream
sync-upstream: ## Pin $(UPSTREAM_BRANCH) to $(UPSTREAM_TAG); merge into $(LOCAL_BRANCH)
	@git fetch upstream --tags
	@git checkout $(UPSTREAM_BRANCH)
	@git reset --hard $(UPSTREAM_TAG)
	@echo "→ $(UPSTREAM_BRANCH) pinned to $(UPSTREAM_TAG). Push with:"
	@echo "    git push --force-with-lease origin $(UPSTREAM_BRANCH)"
	@git checkout $(LOCAL_BRANCH)
	@git merge $(UPSTREAM_BRANCH) --allow-unrelated-histories \
	  -m "sync: merge upstream $(UPSTREAM_TAG) into $(LOCAL_BRANCH)" \
	  || ( echo "merge conflicts — see NEURALEDGE_PATCHES.md override rule"; exit 1 )
	@echo "→ $(LOCAL_BRANCH) now contains $(UPSTREAM_TAG); rebuild with 'make build' and verify with 'make doctor'"

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
