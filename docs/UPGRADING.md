# Upgrading NeuralEDGE Agent

Two kinds of upgrade:

1. **Upstream sync** — pulling a newer Hermes Agent release tag from NousResearch.
2. **NeuralEDGE release** — changing something in the NeuralEDGE zone and shipping a
   new image / tag.

---

## Upstream sync

### Preconditions

- A clean working tree on the `main` branch.
- Upstream remote configured: `git remote add upstream https://github.com/NousResearch/hermes-agent.git`
- A snapshot you can roll back to (`make backup`).
- A **release tag** to pin to (e.g. `v2026.5.16`, `v2026.6.x`). **Don't chase
  `upstream/main` HEAD** — pin to a tag for reproducibility.

### Procedure

```bash
make sync-upstream UPSTREAM_TAG=v2026.6.x
```

Which runs:

```
git fetch upstream --tags
git checkout main
git merge v2026.6.x --allow-unrelated-histories -m "sync: merge upstream v2026.6.x"
```

The merge will conflict on **exactly 4 files**: `README.md`, `LICENSE`, `CONTRIBUTING.md`,
`.gitignore` — these are the documented overrides. NeuralEDGE-zone files
(`neuraledge/`, `skills/neuraledge/`, `docker-compose.neuraledge.yml`, etc.) never collide.

### Resolving the 4 conflicts

```bash
# 3 files where NeuralEDGE wins:
git checkout --ours README.md LICENSE CONTRIBUTING.md
git add README.md LICENSE CONTRIBUTING.md

# .gitignore: union of both
git show :2:.gitignore > /tmp/ours
git show :3:.gitignore > /tmp/theirs
sort -u /tmp/ours /tmp/theirs > .gitignore
git add .gitignore

git commit -m "sync: resolve upstream merge per override rule"
```

The installer's `step_fetch` does this automatically on a fresh install.

### Post-sync test checklist

```
[ ] hermes doctor — all green
[ ] cortex_status — correct for current CORTEX_MODE
[ ] Telegram round-trip — send "ping", receive a reply
[ ] Dashboard — loads via SSH tunnel, themed (skin: neuraledge), no console errors
[ ] Skills loaded — `hermes skills config` shows the 4 NeuralEDGE skills as enabled
[ ] Persona — system prompt matches ~/.hermes/SOUL.md content
[ ] Memory — Tier-1 recall works; Tier-2 cortex_recall returns shaped results
[ ] Ports — `ss -tlnp` shows hermes ports on 127.0.0.1 only
[ ] Logs — secrets redacted in `docker compose logs gateway`
```

Once green, tag the release:

```bash
git tag -a ne-v0.14.0-2 -m "Sync upstream v2026.5.16; iteration 2"
git push origin ne-v0.14.0-2
```

---

## NeuralEDGE-only release

For changes that don't involve an upstream sync (e.g. updating a skill, tweaking the
skin, bumping the bridge version):

```bash
make build && make up && make doctor
git tag -a ne-v0.14.0-<n+1> -m "Skill update: tighten engagement playbook"
git push origin ne-v0.14.0-<n+1>
```

---

## Rolling out to a deployed VPS

Operator runs on the VPS:

```bash
cd /opt/neuraledge-agent
git pull origin main
make build
make up      # rolls the containers
make doctor
```

If anything is off, rollback:

```bash
git checkout <previous-tag>
make build
make up
make doctor
```

State in `~/.hermes/` is untouched by upgrades — config, SOUL.md, memory, and mcp.json
all survive.

---

## When to bump the cortex-mcp version

`neuraledge/mcp/cortex-palace/cortex_mcp/__init__.py` `__version__`:

- **Patch** (0.1.x): bug fixes, no tool contract changes.
- **Minor** (0.x.0): new tool or new arg (additive); existing tools unchanged.
- **Major** (x.0.0): removed/renamed tool, removed/renamed field. **Breaking change for
  Neural's tool surface.** Update the `neos-operations` skill in the same commit.

Always also bump the version label in `pyproject.toml`.

---

## Disaster: rolling back a sync that broke things

```bash
# Identify the merge commit
git log --merges --first-parent -n 5

# Hard reset to the pre-merge state (only if no one else has the bad merge)
git reset --hard <pre-merge-sha>
make build
make up
make doctor
```

For shared remotes, prefer `git revert -m 1 <merge-sha>` so the bad merge is undone
forward in history.
