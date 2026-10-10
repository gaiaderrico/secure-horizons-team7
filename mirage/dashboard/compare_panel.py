"""Red-card panel: what the attacker got vs what was real.

Reads generated/compare.json (python3 -m mirage.prepare.compare, after run_all)
and generated/manifest.json (for crown_jewels[].reason and category).

Use inside the dashboard:
    from dashboard.compare_panel import render_compare_panel
    render_compare_panel()

Or on its own:
    streamlit run dashboard/compare_panel.py
"""

import html
import json
from pathlib import Path

import streamlit as st

GENERATED = Path("generated")
CATEGORY_LABELS = {
    "personal_data": "Personal data",
    "credentials": "Credentials",
    "business": "Business",
}


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _files_from(compare):
    """compare.json may be a list or an object holding a list."""
    if isinstance(compare, list):
        return compare
    if isinstance(compare, dict):
        for key in ("files", "items", "crown_jewels", "compare"):
            if isinstance(compare.get(key), list):
                return compare[key]
    return []


def _changed_set(entry, n_lines):
    """changed_lines may be a list of line indexes or just a count."""
    changed = entry.get("changed_lines")
    if isinstance(changed, list):
        return {int(i) for i in changed if isinstance(i, (int, float))}, len(changed)
    if isinstance(changed, int):
        # Only a count: mark lines that differ between real and fake.
        real, fake = entry.get("real") or [], entry.get("fake") or []
        diff = {i for i in range(n_lines)
                if i >= len(real) or i >= len(fake) or real[i] != fake[i]}
        return diff, changed
    return set(), 0


def _code_block(lines, changed, highlight):
    rows = []
    for i, line in enumerate(lines):
        text = html.escape(str(line)) or "&nbsp;"
        style = f"background:{highlight};" if i in changed else ""
        rows.append(f'<div style="{style}padding:0 6px;white-space:pre;">{text}</div>')
    return (
        '<div style="font-family:monospace;font-size:13px;line-height:1.5;'
        'border:1px solid rgba(128,128,128,.35);border-radius:6px;'
        'padding:6px 0;overflow-x:auto;max-height:260px;overflow-y:auto;">'
        + "".join(rows) + "</div>"
    )


def render_compare_panel(generated_dir: Path = GENERATED):
    compare = _load_json(generated_dir / "compare.json")
    manifest = _load_json(generated_dir / "manifest.json") or {}
    files = _files_from(compare)

    st.subheader("What the attacker got vs what was real")
    if not files:
        st.info("No comparison yet. Run `python3 -m mirage.prepare.compare` after `run_all`.")
        return

    jewels = {j.get("id"): j for j in manifest.get("crown_jewels", []) if isinstance(j, dict)}

    st.caption(f"{len(files)} protected file(s). The attacker's copy is synthetic; "
               "the real file stayed in the vault.")

    for entry in files:
        jid = entry.get("id", "")
        jewel = jewels.get(jid, {})
        name = entry.get("name") or Path(jewel.get("real_path", jid)).name
        category = entry.get("category") or jewel.get("category", "")
        reason = jewel.get("reason") or entry.get("reason", "")
        real = entry.get("real") or []
        fake = entry.get("fake") or []
        beacons = entry.get("beacons") or jewel.get("beacons") or []

        n = max(len(real), len(fake))
        changed, changed_count = _changed_set(entry, n)

        with st.container(border=True):
            top = st.columns([3, 1])
            top[0].markdown(f"**{name}**")
            if category:
                top[1].markdown(f"`{CATEGORY_LABELS.get(category, category)}`")
            if reason:
                st.caption(reason)

            left, right = st.columns(2)
            with left:
                st.markdown("**Attacker got (fake)**")
                st.markdown(_code_block(fake, changed, "rgba(255,170,0,.18)"),
                            unsafe_allow_html=True)
            with right:
                st.markdown("**Real file (in vault)**")
                st.markdown(_code_block(real, changed, "rgba(0,160,90,.15)"),
                            unsafe_allow_html=True)

            bits = []
            if changed_count:
                bits.append(f"{changed_count} line(s) changed")
            if beacons:
                bits.append("beacons: " + ", ".join(f"`{b}`" for b in beacons))
            if bits:
                st.markdown(" · ".join(bits))


if __name__ == "__main__":
    st.set_page_config(page_title="MIRAGE · compare", layout="wide")
    render_compare_panel()
    