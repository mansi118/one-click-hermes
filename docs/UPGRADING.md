# Upgrading NeuralEDGE Agent

Two kinds of upgrade:

1. **Upstream sync** — pulling a newer Hermes Agent release from NousResearch.
2. **NeuralEDGE release** — changing something in the NeuralEDGE zone and shipping a
   new image / tag.

---

## Upstream sync

### Preconditions

- A clean working tree on the `neuraledge` branch.
- Upstream remote configured:
  ```
  git remote add upstream https://github.com/NousResearch/hermes-agent.git
  ```
- A snapshot you can roll back to (`make backup`).

### Procedure

```bash
make sync-upstream
```

Which runs:

```
git fetch upstream
git checkout main && git pull upstream main
git checkout neuraledge && git merge main
```

The merge should complete cleanly. The NeuralEDGE zone is intentionally non-overlapping
with upstream paths.

### If the merge conflicts

1. Open `NEURALEDGE_PATCHES.md`. Every active core patch is logged with a re-apply recipe.
2. Apply the recipe for the conflicting path.
3. `git add <files> && git commit` to complete the merge.
4. Rebuild and verify:

```bash
make build
make up
make doctor
```

If a conflict happens on a file **not** listed in `NEURALEDGE_PATCHES.md`, that means a
previous change leaked outside the NeuralEDGE zone. Don't paper over it:

- Identify the offending commit (`git log --follow <path>`).
- Move the change into the NeuralEDGE zone (plugin, skill, config, or MCP).
- Update `NEURALEDGE_PATCHES.md` if the move is impossible.

### Post-sync test checklist

Run the full Phase-acceptance checklist from `NEURALEDGE_BUILD.md` §"Test checklist":

```
[ ] hermes doctor — all green
[ ] cortex_status — correct for current mode
[ ] Telegram round-trip — send "ping", receive a reply
[ ] Dashboard — loads via SSH tunnel, themed, no console errors
[ ] Skills loaded — `make skills-list` shows 4 pinned NeuralEDGE skills
[ ] Persona — system prompt includes NEURAL.md content
[ ] Memory — Tier-1 recall works; Tier-2 stub-call succeeds
[ ] Ports — `ss -tlnp` shows hermes ports on 127.0.0.1 only
[ ] Logs — secrets redacted
```

Once green, tag the release:

```bash
git tag -a ne-v<upstream>-<n> -m "Sync upstream <upstream>; iteration <n>"
git push origin ne-v<upstream>-<n>
```

---

## NeuralEDGE-only release

For changes that don't involve an upstream sync (e.g. updating a skill, bumping the
bridge version):

```bash
# 1. Make changes in the NeuralEDGE zone.
# 2. Rebuild.
make build
make up
# 3. Verify against the test checklist above.
# 4. Tag and push.
git tag -a ne-v<upstream>-<n+1> -m "Skill update: tighten engagement playbook"
git push origin ne-v<upstream>-<n+1>
```

---

## Rolling out to a deployed VPS

Operator runs on the VPS:

```bash
cd /opt/neuraledge-agent
git pull origin neuraledge
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

State in `~/.hermes/` is untouched by upgrades — config and memory survive.

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

# Hard reset to the pre-merge state (only do this if no one else has the bad merge)
git reset --hard <pre-merge-sha>
make build
make up
make doctor
```

For shared remotes, prefer `git revert -m 1 <merge-sha>` so the bad merge is undone
forward in history.
