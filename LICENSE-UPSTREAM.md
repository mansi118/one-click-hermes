# Upstream Attribution

NeuralEDGE Agent ("Neural") is a fork of **Hermes Agent** by **NousResearch**,
released under the MIT License.

- Upstream repo: https://github.com/NousResearch/hermes-agent
- Upstream version baseline: `v0.14.0`
- Upstream license: MIT (see `LICENSE`)

All files under the following paths are upstream code, preserved unmodified
unless documented in `NEURALEDGE_PATCHES.md`:

- `agent/`
- `gateway/`
- `providers/`
- `tools/`
- `cron/`
- `web/` (structure; theme overlay added under `web/themes/neuraledge.css` only)
- `cli.py`
- `hermes_*.py`
- top-level `Dockerfile` (the upstream image)

The NeuralEDGE additions live in:

**Strictly non-overlapping (will never collide on merge):**

- `neuraledge/branding/SOUL.md`
- `neuraledge/skins/neuraledge.yaml`
- `neuraledge/mcp/cortex-palace/`
- `neuraledge/config/{config.defaults.yaml, .env.template}`
- `neuraledge/install.sh`
- `skills/neuraledge/<slug>/SKILL.md` (4 skills)
- `web/themes/neuraledge.css`
- `docker-compose.neuraledge.yml` (overlay)
- `NEURALEDGE_*.md`, `docs/`

**Intentional overrides at upstream-shared paths (resolved per
`NEURALEDGE_PATCHES.md` → "Intentional Overrides"):**

- `README.md` — NeuralEDGE wins
- `LICENSE` — NeuralEDGE wins (informative superset of upstream MIT)
- `.gitignore` — union of both
- `Makefile` — NeuralEDGE wins; port any unique upstream targets
- `CONTRIBUTING.md` — NeuralEDGE wins
- `docs/` — both contribute; collision only on filename clash

To sync upstream:

```
git checkout main && git pull upstream main
git checkout neuraledge && git merge main
# expect conflicts only on files listed in NEURALEDGE_PATCHES.md (target: zero)
```
