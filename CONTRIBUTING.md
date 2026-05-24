# Contributing to NeuralEDGE Agent

This fork is small and internally maintained. The most likely change you will make is
either syncing the upstream Hermes Agent or extending the NeuralEDGE zone. This guide
covers both.

---

## 1. Repo topology

Two branches, hard seam:

- `main` — tracks NousResearch upstream **verbatim**. Never commit NeuralEDGE files here.
- `neuraledge` — production branch. All NeuralEDGE customisation lives here. Tagged
  releases use the `ne-v<upstream>-<n>` scheme (e.g. `ne-v0.14.0-1`).

The seam is enforced by **what lives where**, not by code review alone:

| Zone | Paths |
|---|---|
| **Upstream** (don't edit) | `agent/`, `gateway/`, `providers/`, `tools/`, `cron/`, `cli.py`, `hermes_*.py`, root `Dockerfile`, `web/` (except `web/themes/neuraledge.css`) |
| **NeuralEDGE** (extend freely) | `neuraledge/`, `skills/neuraledge/`, `plugins/ne_branding/`, `web/themes/neuraledge.css`, `Dockerfile.neuraledge`, `docker-compose.neuraledge.yml`, `NEURALEDGE_*.md`, `docs/`, `Makefile` |

If you find yourself wanting to edit something in the upstream zone, **stop and re-read**
`NEURALEDGE_DESIGN.md` §2. The fix is almost always:

1. A new file under `plugins/ne_branding/` or a sibling plugin.
2. A new skill under `skills/neuraledge/`.
3. A config knob in `neuraledge/config/config.defaults.yaml`.
4. A new MCP server registered in config.

Only if none of those four can carry it — log it in `NEURALEDGE_PATCHES.md` and add the
smallest possible core patch.

---

## 2. Local dev

```bash
git clone -b neuraledge git@github.com:neuraledge/hermes-agent.git
cd hermes-agent
git remote add upstream https://github.com/NousResearch/hermes-agent.git

# Build and run
docker compose -f docker-compose.neuraledge.yml build
cp neuraledge/config/.env.template ~/.hermes/.env   # fill in LLM key
docker compose -f docker-compose.neuraledge.yml up -d
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
make sync-upstream
```

This runs:

```
git fetch upstream
git checkout main && git pull upstream main
git checkout neuraledge && git merge main
```

**Expected outcome:** clean merge. The NeuralEDGE zone is non-overlapping with upstream
files, so unless someone added a core patch (logged in `NEURALEDGE_PATCHES.md`), there's
nothing to conflict on.

**If there's a conflict:**

1. Open `NEURALEDGE_PATCHES.md` and look up the patch ID covering the conflicting file.
2. Apply the re-apply recipe documented there.
3. `git add` the resolved files, complete the merge.
4. `make build && make doctor`.

If a conflict is in a file *not* listed in `NEURALEDGE_PATCHES.md`, something violated
the seam since the last sync — find the offending commit, move the change into the
NeuralEDGE zone, and update the patches log.

---

## 4. Adding a feature

| Goal | Add this |
|---|---|
| Change a string the user sees | `neuraledge/branding/strings.toml` |
| Add a NeuralEDGE color, font, asset | `neuraledge/branding/theme.toml` + reference in `web/themes/neuraledge.css` |
| Tweak Neural's persona | `neuraledge/branding/persona/NEURAL.md` |
| Teach Neural a procedure or domain fact | New skill in `skills/neuraledge/` |
| Add a CORTEX-PALACE tool / change a tool shape | `neuraledge/mcp/cortex-palace/cortex_mcp/` + bump version |
| Wire in a new external service | Register as an MCP server in `config.defaults.yaml` |
| Change the install flow | `neuraledge/install.sh` |
| Add a make target | `Makefile` |

Commit messages: `<area>: <imperative subject>`, e.g. `branding: add brand-voice
acceptance line to NEURAL.md`. Keep PR diffs scoped to one zone.

---

## 5. Release checklist

Before tagging `ne-v<upstream>-<n>`:

- [ ] `make sync-upstream` clean.
- [ ] `make build && make doctor` green.
- [ ] All 6 phase acceptances in `NEURALEDGE_BUILD.md` pass.
- [ ] `NEURALEDGE_PATCHES.md` reflects current patches (or is still empty).
- [ ] README install one-liner copy-pastes and works on a fresh VPS.

Tag, push, update the `get.neuraledge.in/agent` redirect if pinning a specific tag.
