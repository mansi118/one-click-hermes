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

## To verify on first real merge

Items the scaffold encoded *defensively* against guessed upstream contracts. None of
them are patches today, but each may demand one once we see the real Hermes code.

1. **Branding plugin hook names** (`plugins/ne_branding/plugin.py`).
   The plugin duck-types against likely hook attribute names — `set_banner`,
   `register_banner`, `override_banner`; `override_strings`, etc. If none match, the
   plugin no-ops and logs a warning. Verify by reading the real Hermes plugin host
   and either:
   - Confirming a hook matches → no action needed.
   - Finding the actual hook name(s) → add them to the plugin's lookup list (still no
     core patch).
   - Confirming no hook exists at all → add the smallest possible core patch in the
     CLI banner emitter and the strings registry, log here as NE-PATCH-001 / -002.

2. **Personality search path env var** (`HERMES_PERSONALITY_PATHS`).
   Used in `Dockerfile.neuraledge` ENV and by the plugin's `_attach_persona_path`
   fallback. Verify Hermes actually reads this env name; if it uses a different one,
   update both spots.

3. **Plugin discovery directory** (`plugins/`).
   Design §3.1 says Hermes loads plugins from `plugins/`. Verify on merge that the
   real loader picks up `plugins/ne_branding/` automatically. If it requires an
   explicit registration call instead, do that registration in `config.defaults.yaml`.

4. **Config key shape** in `neuraledge/config/config.defaults.yaml`.
   `personality:`, `plugins.enabled:`, `skills.paths:`, `mcp_servers:`, etc. — these
   keys are inferred from the design doc, not the real Hermes config schema. Verify
   against the real `hermes setup` / `hermes config` output; rename keys here as
   needed (no core patch — just config alignment).

5. **`hermes doctor`, `hermes setup`, `hermes skills list`, `hermes model`** —
   commands referenced by the Makefile and install.sh. If the real CLI uses different
   subcommand names, update the Makefile targets and install.sh wizard step.

Track each item with `[ ]` here as you verify; flip to `[x]` once confirmed.

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
