# Contributing to NeuralEDGE Agent

This fork is small and internally maintained. Most changes are either syncing upstream
Hermes or extending the NeuralEDGE zone. This guide covers both.

---

## 1. Repo topology

- **`main`** — production branch. Holds the NeuralEDGE scaffold plus a merged-in
  release tag of upstream Hermes (currently `v2026.5.16`).
- **`upstream` remote** — tracks NousResearch upstream. Synced via `make sync-upstream`.

Two zones, hard seam (verified empty of leaks against `v2026.5.16`):

| Zone | Paths |
|---|---|
| **Upstream** (don't edit) | `agent/`, `gateway/`, `providers/`, `tools/`, `cron/`, `cli.py`, `hermes_*`, root `Dockerfile`, root `docker-compose.yml`, `plugins/{memory,web,…}/`, `skills/{apple,devops,…}/`, `web/` (except `web/themes/neuraledge.css`) |
| **NeuralEDGE** (extend freely) | `neuraledge/`, `skills/neuraledge/`, `web/themes/neuraledge.css`, `docker-compose.neuraledge.yml`, `NEURALEDGE_*.md`, `docs/`, `Makefile`, `README.md`, `LICENSE`, `CONTRIBUTING.md`, `.gitignore` |

If you find yourself wanting to edit something in the upstream zone, **stop and re-read**
`NEURALEDGE_DESIGN.md` §2. The fix is almost always:

1. A change to the Skin YAML (`neuraledge/skins/neuraledge.yaml`) — colors, banner, strings.
2. A change to `SOUL.md` — Neural's voice/identity/conduct.
3. A new skill under `skills/neuraledge/<slug>/SKILL.md`.
4. A new entry in `neuraledge/config/mcp.json` for an additional MCP server.
5. A config knob in `neuraledge/config/config.defaults.yaml` (real Hermes schema).

Only if none of those five can carry it — log it in `NEURALEDGE_PATCHES.md` and add the
smallest possible core patch. Target remains **0 core patches**.

---

## 2. Local dev

```bash
git clone -b main git@github.com:mansi118/one-click-hermes.git
cd one-click-hermes
git remote add upstream https://github.com/NousResearch/hermes-agent.git

# Build and run (uses both compose files)
docker compose -f docker-compose.yml -f docker-compose.neuraledge.yml build
docker compose -f docker-compose.yml -f docker-compose.neuraledge.yml up -d
make doctor
```

For cortex-mcp dev without Docker:

```bash
cd neuraledge/mcp/cortex-palace
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest && ruff check .
CORTEX_MODE=stub python -m cortex_mcp.server
```

---

## 3. Upstream sync workflow

```bash
make sync-upstream UPSTREAM_TAG=v2026.7.x   # pin to whatever release you choose
```

This runs:

```
git fetch upstream --tags
git checkout main
git merge v2026.7.x --allow-unrelated-histories
```

**Expected conflicts:** README.md, LICENSE, CONTRIBUTING.md, .gitignore. Resolution rule:

| File | Win |
|---|---|
| `README.md` / `LICENSE` / `CONTRIBUTING.md` | **NeuralEDGE wins** (ours has the override-policy preserved) |
| `.gitignore` | **union** of both |

The installer's `step_fetch` auto-resolves these on first install. For manual sync:

```bash
git checkout --ours README.md LICENSE CONTRIBUTING.md
git show :2:.gitignore > /tmp/ours; git show :3:.gitignore > /tmp/theirs
sort -u /tmp/ours /tmp/theirs > .gitignore
git add README.md LICENSE CONTRIBUTING.md .gitignore
git commit
```

If a conflict happens on a file **not** in the override list, the seam was violated.
Find the offending commit and move the change into the NeuralEDGE zone.

---

## 4. Adding a feature

| Goal | Add this |
|---|---|
| Tweak a CLI color, banner, or string Neural says | Edit `neuraledge/skins/neuraledge.yaml` |
| Tweak Neural's persona (voice, identity, boundaries) | Edit `neuraledge/branding/SOUL.md` |
| Teach Neural a procedure or domain fact | New skill: `skills/neuraledge/<slug>/SKILL.md` |
| Add a CORTEX-PALACE tool or change a tool shape | `neuraledge/mcp/cortex-palace/cortex_mcp/` + bump version + update `neos-operations` skill |
| Wire in a new external MCP server | Add entry to `neuraledge/config/mcp.json` |
| Change a Hermes config default | `neuraledge/config/config.defaults.yaml` (real schema only) |
| Change the install flow | `neuraledge/install.sh` |
| Add a make target | `Makefile` |

Commit messages: `<area>: <imperative subject>` (e.g. `skin: warm the status-bar warn
color`). Keep PR diffs scoped to one zone.

---

## 5. Release checklist

Before tagging `ne-v<upstream-tag>-<n>`:

- [ ] `make sync-upstream` clean (only the 4 override conflicts, auto-resolved).
- [ ] `make build && make doctor` green on a fresh VPS.
- [ ] All 6 phase acceptances in `NEURALEDGE_BUILD.md` pass.
- [ ] `NEURALEDGE_PATCHES.md` reflects current patches (target: still empty).
- [ ] README install one-liner copy-pastes and works on a fresh VPS.

Tag, push, update the `get.neuraledge.in/agent` redirect if pinning a specific tag.

---

## 6. v2 — distribution path

`NEURALEDGE_DESIGN.md` §11 documents a v2 candidate: ship NeuralEDGE as a Hermes
**profile distribution** instead of a fork. Don't tackle it in v1; revisit once the
fork has been stable for a few upstream cycles.
