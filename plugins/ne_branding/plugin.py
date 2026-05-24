"""NeuralEDGE branding plugin — registration entrypoint.

This plugin overlays the running Hermes agent with NeuralEDGE identity:
banner, color palette, display strings, and the persona-search path that
loads NEURAL.md.

Design contract (see NEURALEDGE_DESIGN.md §3.1):
- Zero upstream edits. The plugin attaches via Hermes' plugin hooks.
- If a hook is absent (upstream renamed/removed it), the plugin no-ops
  cleanly and logs a single warning. The branded artefact still ships
  via the asset files; only the auto-apply step is skipped.
- The fallback path of last resort is a single 1-line core patch in the
  CLI banner emitter — documented in NEURALEDGE_PATCHES.md if ever added.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Mapping

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

log = logging.getLogger("ne_branding")

REPO_ROOT = Path(__file__).resolve().parents[2]
BRANDING_DIR = REPO_ROOT / "neuraledge" / "branding"
BANNER_PATH = BRANDING_DIR / "banner.txt"
THEME_PATH = BRANDING_DIR / "theme.toml"
STRINGS_PATH = BRANDING_DIR / "strings.toml"
PERSONA_DIR = BRANDING_DIR / "persona"


# --- Asset loaders -----------------------------------------------------------


def _load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.warning("ne_branding: missing asset %s", path)
        return ""


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        log.warning("ne_branding: missing asset %s", path)
        return {}


# --- Hook attachers ---------------------------------------------------------
# Each attacher tries a few attribute names that Hermes plausibly exposes.
# The first one that exists wins; the rest are silently skipped. New upstream
# hooks can be added here without touching anything else.


def _attach_banner(host: Any, banner: str) -> bool:
    if not banner:
        return False
    for name in ("set_banner", "register_banner", "override_banner"):
        fn = getattr(host, name, None)
        if callable(fn):
            fn(banner)
            log.info("ne_branding: banner attached via host.%s", name)
            return True
    # Fallback: monkey-patch a known module-level banner constant if exposed.
    for module_name in ("hermes.cli", "hermes.banner", "cli"):
        mod = sys.modules.get(module_name)
        if mod and hasattr(mod, "BANNER"):
            setattr(mod, "BANNER", banner)
            log.info("ne_branding: banner attached via %s.BANNER", module_name)
            return True
    log.warning(
        "ne_branding: no banner hook found. If banner does not appear, add a "
        "core patch per NEURALEDGE_PATCHES.md template (target: 1 line)."
    )
    return False


def _attach_strings(host: Any, strings: Mapping[str, Any]) -> bool:
    if not strings:
        return False
    flat = _flatten(strings)
    for name in ("override_strings", "register_strings", "set_strings"):
        fn = getattr(host, name, None)
        if callable(fn):
            fn(flat)
            log.info("ne_branding: %d strings attached via host.%s", len(flat), name)
            return True
    # Fallback: place on a shared registry attribute if present.
    registry = getattr(host, "strings", None)
    if isinstance(registry, dict):
        registry.update(flat)
        log.info("ne_branding: %d strings merged into host.strings", len(flat))
        return True
    log.warning("ne_branding: no strings hook found; defaults still in effect")
    return False


def _attach_theme(host: Any, theme: Mapping[str, Any]) -> bool:
    if not theme:
        return False
    for name in ("set_theme", "register_theme", "override_theme"):
        fn = getattr(host, name, None)
        if callable(fn):
            fn(theme)
            log.info("ne_branding: theme tokens attached via host.%s", name)
            return True
    # Expose for consumers (CLI colorizer, dashboard build) to pick up via env.
    os.environ.setdefault("NEURALEDGE_THEME_PATH", str(THEME_PATH))
    log.info("ne_branding: theme path published via NEURALEDGE_THEME_PATH env")
    return False


def _attach_persona_path(host: Any) -> bool:
    if not PERSONA_DIR.is_dir():
        return False
    for name in ("add_personality_path", "register_personality_path", "add_persona_path"):
        fn = getattr(host, name, None)
        if callable(fn):
            fn(str(PERSONA_DIR))
            log.info("ne_branding: persona path attached via host.%s", name)
            return True
    # Fallback: publish via env so any persona loader can pick it up.
    existing = os.environ.get("HERMES_PERSONALITY_PATHS", "")
    if str(PERSONA_DIR) not in existing.split(os.pathsep):
        os.environ["HERMES_PERSONALITY_PATHS"] = (
            f"{existing}{os.pathsep}{PERSONA_DIR}" if existing else str(PERSONA_DIR)
        )
    log.info("ne_branding: persona path published via HERMES_PERSONALITY_PATHS env")
    return True


def _flatten(d: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, Mapping):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


# --- Entrypoint --------------------------------------------------------------


def register(host: Any = None) -> dict[str, bool]:
    """Hermes plugin entrypoint.

    `host` is the plugin-host object Hermes passes in. The shape isn't fully
    pinned across upstream versions, so we duck-type against several known
    method names and degrade gracefully.

    Returns a small status dict suitable for `hermes doctor` introspection.
    """
    banner = _load_text(BANNER_PATH)
    theme = _load_toml(THEME_PATH)
    strings = _load_toml(STRINGS_PATH)

    status = {
        "banner": _attach_banner(host, banner) if host is not None else bool(banner),
        "strings": _attach_strings(host, strings) if host is not None else bool(strings),
        "theme": _attach_theme(host, theme) if host is not None else bool(theme),
        "persona_path": _attach_persona_path(host) if host is not None else PERSONA_DIR.is_dir(),
    }
    log.info("ne_branding: registered with status %s", status)
    return status


# Allow `python -m plugins.ne_branding.plugin` to print the banner — useful
# for verifying the asset is well-formed before Hermes boot.
if __name__ == "__main__":
    sys.stdout.write(_load_text(BANNER_PATH))
    sys.stdout.write("\n")
