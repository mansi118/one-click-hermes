#!/usr/bin/env bash
#
# NeuralEDGE Agent — one-click installer.
#
#   curl -fsSL https://get.neuraledge.in/agent | bash
#
# Idempotent: every step is safe to re-run. The script never clobbers an
# existing ~/.hermes/config.yaml, SOUL.md, or .env — it only seeds them when
# absent.
#
# This installer is an overlay on stock Hermes Agent v2026.5.16. It does NOT
# patch upstream code — it lays the NeuralEDGE distribution (config.yaml with
# mcp_servers, SOUL.md, skin, skills) into ~/.hermes alongside the upstream
# container.

set -euo pipefail

# ── Config ─────────────────────────────────────────────────────────────────

REPO_URL="${NE_REPO_URL:-https://github.com/mansi118/one-click-hermes.git}"
REPO_BRANCH="${NE_REPO_BRANCH:-main}"
INSTALL_DIR="${NE_INSTALL_DIR:-/opt/neuraledge-agent}"
STATE_DIR="${HOME}/.hermes"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.neuraledge.yml"
UPSTREAM_TAG="${NE_UPSTREAM_TAG:-v2026.5.16}"
MIN_RAM_GB="${NE_MIN_RAM_GB:-4}"
SWAP_THRESHOLD_GB="${NE_SWAP_THRESHOLD_GB:-6}"
SWAP_SIZE_GB="${NE_SWAP_SIZE_GB:-2}"

# ── Pretty output ──────────────────────────────────────────────────────────

if [ -t 1 ]; then
  C_TEAL=$'\033[38;5;80m'; C_INK=$'\033[1m'; C_MUTED=$'\033[38;5;244m'
  C_OK=$'\033[38;5;82m'; C_WARN=$'\033[38;5;178m'; C_ERR=$'\033[38;5;167m'
  C_RESET=$'\033[0m'
else
  C_TEAL=""; C_INK=""; C_MUTED=""; C_OK=""; C_WARN=""; C_ERR=""; C_RESET=""
fi

log()   { printf "%s[neural-install]%s %s\n" "$C_TEAL" "$C_RESET" "$*"; }
ok()    { printf "%s  ✓%s %s\n"  "$C_OK"   "$C_RESET" "$*"; }
warn()  { printf "%s  !%s %s\n"  "$C_WARN" "$C_RESET" "$*"; }
err()   { printf "%s  ✗%s %s\n"  "$C_ERR"  "$C_RESET" "$*" >&2; }
hd()    { printf "\n%s━━ %s %s━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%s\n" \
            "$C_INK" "$*" "$C_MUTED" "$C_RESET"; }
die()   { err "$*"; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

# ── Step 1: pre-flight ─────────────────────────────────────────────────────

step_preflight() {
  hd "1/10  Pre-flight"

  [[ "$(uname -s)" == "Linux" ]] || die "only Linux supported; got $(uname -s)"
  [[ -r /etc/os-release ]] || die "/etc/os-release missing — unsupported distro"
  # shellcheck disable=SC1091
  . /etc/os-release
  case "$ID" in
    ubuntu) ;;
    debian) warn "Debian — should work, but Ubuntu 22.04/24.04 is the tested target" ;;
    *) warn "untested distro: $ID; continuing" ;;
  esac
  ok "OS: $PRETTY_NAME"

  if [[ "$(id -u)" -eq 0 ]]; then
    warn "running as root; will install for root and skip 'docker' group step"
    SUDO=""
  else
    require_cmd sudo
    sudo -v || die "sudo required"
    SUDO="sudo"
  fi
  ok "privilege OK"

  local ram_gb
  ram_gb=$(awk '/MemTotal/ {printf "%.0f", $2/1024/1024}' /proc/meminfo)
  [[ "$ram_gb" -ge "$MIN_RAM_GB" ]] \
    || die "RAM too low: ${ram_gb}G < ${MIN_RAM_GB}G required"
  ok "RAM: ${ram_gb}G"
  RAM_GB="$ram_gb"
}

# ── Step 2: docker ─────────────────────────────────────────────────────────

step_docker() {
  hd "2/10  Docker"
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    ok "docker + compose already installed"
    return
  fi

  log "installing Docker Engine + Compose"
  $SUDO apt-get update -y
  $SUDO apt-get install -y ca-certificates curl gnupg lsb-release
  $SUDO install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    $SUDO chmod a+r /etc/apt/keyrings/docker.gpg
  fi
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null
  $SUDO apt-get update -y
  $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  if [[ -n "$SUDO" ]]; then
    $SUDO usermod -aG docker "$USER" || true
    warn "added '$USER' to the 'docker' group — log out & back in for it to apply"
  fi
  ok "Docker installed"
}

# ── Step 3: swap ───────────────────────────────────────────────────────────

step_swap() {
  hd "3/10  Swap"
  if [[ "$RAM_GB" -ge "$SWAP_THRESHOLD_GB" ]]; then
    ok "RAM ≥ ${SWAP_THRESHOLD_GB}G — skipping swap"
    return
  fi
  if [[ -f /swapfile ]] && swapon --show | grep -q /swapfile; then
    ok "swapfile already active"
    return
  fi
  log "creating ${SWAP_SIZE_GB}G swapfile (RAM ${RAM_GB}G < ${SWAP_THRESHOLD_GB}G)"
  $SUDO fallocate -l "${SWAP_SIZE_GB}G" /swapfile \
    || $SUDO dd if=/dev/zero of=/swapfile bs=1M count=$((SWAP_SIZE_GB * 1024)) status=none
  $SUDO chmod 600 /swapfile
  $SUDO mkswap /swapfile >/dev/null
  $SUDO swapon /swapfile
  grep -q '^/swapfile' /etc/fstab \
    || echo '/swapfile none swap sw 0 0' | $SUDO tee -a /etc/fstab >/dev/null
  ok "swap added"
}

# ── Step 4: fetch repo + pin upstream ──────────────────────────────────────

step_fetch() {
  hd "4/10  Fetch repo (NeuralEDGE overlay + upstream Hermes pinned to $UPSTREAM_TAG)"
  require_cmd git
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    log "$INSTALL_DIR exists — pulling latest"
    $SUDO git -C "$INSTALL_DIR" fetch --tags origin "$REPO_BRANCH"
    $SUDO git -C "$INSTALL_DIR" checkout "$REPO_BRANCH"
    $SUDO git -C "$INSTALL_DIR" reset --hard "origin/$REPO_BRANCH"
  else
    $SUDO mkdir -p "$(dirname "$INSTALL_DIR")"
    $SUDO git clone --branch "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"
  fi
  $SUDO chown -R "$USER:$USER" "$INSTALL_DIR"

  # Ensure upstream Hermes is available at the pinned tag so docker-compose.yml
  # can be resolved by the overlay.
  cd "$INSTALL_DIR"
  if ! git rev-parse --verify "$UPSTREAM_TAG" >/dev/null 2>&1; then
    log "fetching upstream Hermes pinned to $UPSTREAM_TAG"
    git remote get-url upstream >/dev/null 2>&1 || \
      git remote add upstream https://github.com/NousResearch/hermes-agent.git
    git fetch --depth 1 upstream tag "$UPSTREAM_TAG"
    # Merge upstream into the working tree so docker-compose.yml and the
    # Dockerfile are present. Conflicts on README/LICENSE/CONTRIBUTING/.gitignore
    # are resolved by the documented "NeuralEDGE wins / .gitignore union" rule.
    git merge "$UPSTREAM_TAG" --allow-unrelated-histories \
      -m "sync: vendor upstream Hermes $UPSTREAM_TAG into install dir" || true
    # Auto-resolve the 4 known overrides if conflicts remain:
    for f in README.md LICENSE CONTRIBUTING.md; do
      if git diff --name-only --diff-filter=U | grep -qx "$f"; then
        git checkout --ours "$f" && git add "$f"
      fi
    done
    # .gitignore needs a union; concatenate ours + theirs, dedupe.
    if git diff --name-only --diff-filter=U | grep -qx ".gitignore"; then
      git show :2:.gitignore > /tmp/gi.ours
      git show :3:.gitignore > /tmp/gi.theirs
      sort -u /tmp/gi.ours /tmp/gi.theirs > .gitignore
      git add .gitignore
    fi
    git -c user.name="installer" -c user.email="installer@neuraledge" \
      commit -m "auto-resolve upstream-merge conflicts per NE override rule" || true
  fi
  ok "repo + upstream ready at $INSTALL_DIR"
}

# ── Step 5: state directory (seed distribution-owned files) ───────────────

step_state() {
  hd "5/10  State directory — seed distribution"
  mkdir -p "$STATE_DIR"/{sessions,workspace,logs,cron,skins,skills}
  chmod 700 "$STATE_DIR"

  # config.yaml
  if [[ -f "$STATE_DIR/config.yaml" ]]; then
    ok "config.yaml present — not overwriting"
  else
    cp "$INSTALL_DIR/neuraledge/config/config.defaults.yaml" "$STATE_DIR/config.yaml"
    chmod 600 "$STATE_DIR/config.yaml"
    ok "seeded config.yaml from NeuralEDGE defaults"
  fi

  # .env
  if [[ -f "$STATE_DIR/.env" ]]; then
    ok ".env present — not overwriting"
  else
    cp "$INSTALL_DIR/neuraledge/config/.env.template" "$STATE_DIR/.env"
    chmod 600 "$STATE_DIR/.env"
    ok "seeded .env from template (mode 600)"
  fi

  # SOUL.md — Neural's persona
  if [[ -f "$STATE_DIR/SOUL.md" ]] && ! grep -q "You are Hermes Agent" "$STATE_DIR/SOUL.md"; then
    ok "SOUL.md present and customised — not overwriting"
  else
    cp "$INSTALL_DIR/neuraledge/branding/SOUL.md" "$STATE_DIR/SOUL.md"
    chmod 600 "$STATE_DIR/SOUL.md"
    ok "seeded SOUL.md (Neural persona)"
  fi

  # MCP servers (cortex-mcp) live inside ~/.hermes/config.yaml under
  # `mcp_servers:` — already seeded above. Nothing to do here.

  # skins/neuraledge.yaml
  cp "$INSTALL_DIR/neuraledge/skins/neuraledge.yaml" "$STATE_DIR/skins/neuraledge.yaml"
  ok "installed skin: neuraledge"

  # NeuralEDGE seed skills — install (idempotent rsync-style copy)
  cp -r "$INSTALL_DIR/skills/neuraledge" "$STATE_DIR/skills/" 2>/dev/null || \
    rsync -a --delete "$INSTALL_DIR/skills/neuraledge/" "$STATE_DIR/skills/neuraledge/"
  ok "installed seed skills under ~/.hermes/skills/neuraledge/"
}

# ── Step 6: build images ──────────────────────────────────────────────────

step_build() {
  hd "6/10  Build images (upstream hermes-agent + cortex-mcp)"
  cd "$INSTALL_DIR"
  [[ -f docker-compose.yml ]] || die "upstream docker-compose.yml missing — step 4 incomplete"
  docker compose $COMPOSE_FILES build
  ok "images built"
}

# ── Step 7: setup wizard ──────────────────────────────────────────────────

step_wizard() {
  hd "7/10  Setup wizard (model + Telegram)"
  if grep -qE '^(OPENROUTER_API_KEY|ANTHROPIC_API_KEY|LLM_API_KEY)=.{8,}' "$STATE_DIR/.env" 2>/dev/null; then
    ok "LLM API key already set — skipping wizard"
    return
  fi
  if [[ ! -t 0 ]]; then
    warn "non-interactive shell — skipping wizard"
    warn "edit $STATE_DIR/.env and run 'make setup' later"
    return
  fi
  cd "$INSTALL_DIR"
  log "launching Hermes setup wizard"
  docker compose $COMPOSE_FILES run --rm gateway hermes setup || \
    warn "wizard exited non-zero — finish later with 'make setup'"
}

# ── Step 8: NeuralEDGE-specific secrets ────────────────────────────────────

step_secrets() {
  hd "8/10  NeuralEDGE secrets (CORTEX-PALACE / n8n)"
  if [[ ! -t 0 ]]; then
    warn "non-interactive shell — leaving CORTEX_MODE=stub. Edit $STATE_DIR/.env later."
    return
  fi

  printf "\n%sNEOS / CORTEX-PALACE%s\n" "$C_INK" "$C_RESET"
  printf "  Leave blank to keep CORTEX_MODE=stub (works fine; canned long-term memory).\n"
  read -r -p "  CORTEX_ENDPOINT (https://…) : " cortex_ep || true
  if [[ -n "${cortex_ep:-}" ]]; then
    read -r -p "  CORTEX_TOKEN (bearer)       : " cortex_tok || true
    sed -i "s|^CORTEX_MODE=.*|CORTEX_MODE=live|"           "$STATE_DIR/.env"
    sed -i "s|^CORTEX_ENDPOINT=.*|CORTEX_ENDPOINT=$cortex_ep|" "$STATE_DIR/.env"
    sed -i "s|^CORTEX_TOKEN=.*|CORTEX_TOKEN=$cortex_tok|"   "$STATE_DIR/.env"
    ok "CORTEX live mode configured"
  else
    ok "leaving CORTEX_MODE=stub (default)"
  fi

  printf "\n%sn8n.neuraledge.in (optional)%s\n" "$C_INK" "$C_RESET"
  read -r -p "  N8N_WEBHOOK_URL (leave blank to skip) : " n8n || true
  if [[ -n "${n8n:-}" ]]; then
    sed -i "s|^N8N_WEBHOOK_URL=.*|N8N_WEBHOOK_URL=$n8n|" "$STATE_DIR/.env"
    ok "n8n webhook configured"
  fi
}

# ── Step 9: launch ─────────────────────────────────────────────────────────

step_launch() {
  hd "9/10  Launch"
  cd "$INSTALL_DIR"
  docker compose $COMPOSE_FILES up -d
  ok "containers running"
}

# ── Step 10: verify + report ───────────────────────────────────────────────

step_verify() {
  hd "10/10 Verify"
  cd "$INSTALL_DIR"
  local tries=0
  until docker compose $COMPOSE_FILES ps --status running | grep -q hermes; do
    tries=$((tries + 1))
    [[ "$tries" -gt 12 ]] && die "hermes container did not start; check 'docker compose ... logs gateway'"
    sleep 2
  done

  if docker compose $COMPOSE_FILES exec -T gateway hermes doctor >/dev/null 2>&1; then
    ok "hermes doctor: green"
  else
    warn "hermes doctor reported issues — run 'make logs' to investigate"
  fi

  cat <<EOF

${C_TEAL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}
${C_INK}NeuralEDGE Agent is up.${C_RESET}

  Dashboard:    ssh -L 9119:localhost:9119 $USER@$(hostname -I | awk '{print $1}')
                then open http://localhost:9119

  Telegram:     send your bot a message; if no reply, re-run setup:
                make setup

  Logs:         make logs
  Health:       make doctor          ${C_MUTED}(THE green/red signal)${C_RESET}
  Backup:       make backup
  Stop:         make down

${C_WARN}Reminder:${C_RESET} restrict SSH (port 22) to your operator IP in the AWS Security
Group. Nothing else should be reachable from the public internet.
${C_TEAL}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${C_RESET}
EOF
}

# ── Main ───────────────────────────────────────────────────────────────────

main() {
  cat <<EOF
${C_TEAL}
  NeuralEDGE Agent · Neural
  one-click installer (overlay on Hermes ${UPSTREAM_TAG})
${C_RESET}
EOF
  step_preflight
  step_docker
  step_swap
  step_fetch
  step_state
  step_build
  step_wizard
  step_secrets
  step_launch
  step_verify
}

main "$@"
