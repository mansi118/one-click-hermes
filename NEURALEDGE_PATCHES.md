# NeuralEDGE Core Patches

Any modification to upstream Hermes code (anything outside `neuraledge/`,
`skills/neuraledge/`, `plugins/ne_branding/`, `Dockerfile.neuraledge`,
`docker-compose.neuraledge.yml`, or the meta-docs) is a **core patch** and must be logged
here, with:

- **Why** the four normal extension points (plugin, skill, config, MCP) couldn't carry it.
- **What** changed — exact file paths and a unified diff or line refs.
- **Re-apply recipe** — what to do when an upstream merge wipes it.

**Target:** ≤ 2 core patches total, each ≤ 10 lines. If you're about to add a third, stop
and re-read Design §2 — the fix is probably a plugin, not a patch.

---

## Active Patches

_None yet. Phases 1–6 are designed to ship without any core patch._

---

## Intentional Overrides (not patches, but affect merges)

These are top-level files that NeuralEDGE owns despite sitting at paths that upstream
Hermes also occupies. They are **not** core patches — no upstream code is modified —
but they will conflict during `git merge upstream/main` and the merge resolution must
be deterministic.

The rule for these files: **NeuralEDGE version wins**, with the noted exceptions.
Document any change to this policy here.

| Path | Resolution at merge | Why |
|---|---|---|
| `README.md` | NeuralEDGE wins | The fork's public-facing identity. Upstream's README belongs to upstream's repo. |
| `LICENSE` | NeuralEDGE wins | NeuralEDGE LICENSE preserves NousResearch's MIT copyright line AND adds NeuralEDGE additions. Strictly informative superset. |
| `LICENSE-UPSTREAM.md` | NeuralEDGE owns (no collision) | Attribution doc that doesn't exist upstream. |
| `.gitignore` | **MERGE — union of both** | Upstream's entries protect upstream paths; ours protect NE state. Both are needed. |
| `Makefile` | NeuralEDGE wins (with care) | Wraps `docker compose -f docker-compose.neuraledge.yml`. If upstream ships a `Makefile`, port any unique targets from it into our Makefile and document them here. |
| `CONTRIBUTING.md` | NeuralEDGE wins | About contributing to *this fork*, not to upstream Hermes. Link to upstream's CONTRIBUTING if present. |
| `docs/` | Merge — both contribute files | Different filenames inside; collision only if names clash. Treat collisions case-by-case. |

If a future upstream change makes a NeuralEDGE override unnecessary (e.g., upstream
adopts a fork-friendly README shape), retire that row.

---

## Verification log (closed)

All items resolved against `v2026.5.16` / `v0.14.0` source tree on 2026-05-24. Net
result: scaffold rewritten, **zero core patches needed**.

- [x] **Branding plugin** — *Replaced entirely* by the upstream Skin system
  (`hermes_cli/skin_engine.py`). YAML at `~/.hermes/skins/neuraledge.yaml`. No Python.
  `plugins/ne_branding/` directory deleted.
- [x] **Persona** — Real name is `SOUL.md`. Single file at `$HERMES_HOME/SOUL.md`,
  seeded from `DEFAULT_SOUL_MD` on first run. Installer overrides with our SOUL.md.
  No `personality:` config key (doesn't exist).
- [x] **Plugin discovery dir** — Not applicable; we don't ship a plugin anymore.
- [x] **Config keys** — Real schema is `model:` (with `default`/`provider`/`base_url`),
  `terminal:`, `display:` (with `skin:`), `skills:` (with `disabled:`/`platform_disabled:`,
  *opt-out* not opt-in), `gateway:`, `worktree:`, **`mcp_servers:`** (snake_case;
  see the dedicated entry below). All updated in
  `neuraledge/config/config.defaults.yaml`.
- [x] **CLI subcommands** — `hermes doctor`, `hermes setup`, `hermes model` all real.
  `hermes skills` is **interactive** (curses); subcommands: `tap`, `config`. No
  `hermes skills list`. Makefile updated: `make skills` → `hermes skills config`.
- [x] **Skill format** — `skills/<category>/<slug>/SKILL.md` (directory-per-skill);
  frontmatter tags under `metadata.hermes.tags`. No `pinned:` (skills are opt-out).
  All four NE skills restructured.
- [x] **Docker compose** — Upstream uses `network_mode: host` with two services
  (`gateway` + `dashboard`). Our `docker-compose.neuraledge.yml` rewritten as a true
  overlay: adds only `cortex-mcp` (host-net, bound to `127.0.0.1:8765`) plus a
  `depends_on` link. Usage: `docker compose -f docker-compose.yml -f
  docker-compose.neuraledge.yml up -d`.
- [x] **MCP server registration** — Verified against `hermes_cli/mcp_config.py:8` and
  `cli-config.yaml.example:777`. **For fork-mode users, MCP servers live in
  `~/.hermes/config.yaml` under `mcp_servers:` (snake_case)**, NOT in a separate
  `mcp.json`. Server-entry shape: `url + transport: sse` for SSE servers (per
  `tools/mcp_tool.py:34`). Our `cortex-mcp` entry is folded into
  `neuraledge/config/config.defaults.yaml`. (The standalone `~/.hermes/mcp.json` is a
  `profile_distribution` artefact — relevant only for the v2 distribution path; see
  Design §11.)

---

## Patch Template

```
### NE-PATCH-001 — <one-line summary>

- **Added:**   <YYYY-MM-DD> by <author>
- **Phase:**   <which phase forced it>
- **File(s):** <path>:<lines>
- **Why no plugin/skill/config/MCP path:**
  <2-3 sentences>

- **Diff:**
    ```diff
    --- a/<path>
    +++ b/<path>
    @@ -<old> +<new> @@
    - <removed>
    + <added>
    ```

- **Re-apply on upstream merge:**
  1. After `git merge main`, check `git status` for conflict in <path>.
  2. <Specific commands or hunks to re-apply.>
  3. Verify by <phase acceptance check>.

- **Retire when:** <upstream PR / hook / version that obsoletes this patch>
```
