#!/usr/bin/env python3
"""Re-key V8_modules/item_database.lk:WEAPON_DATABASE from generator IDs
(weapons.json `id`) to LeekScript runtime IDs (weapons.json `item`).

Background: the runtime AI looks up weapon stats via
  getWeaponData(weaponId)  where weaponId is the LeekScript constant
  (e.g. WEAPON_DESTROYER = 40 in LeekScript). The DB shipped with the
  repo was keyed by the generator's internal id (Destroyer = 9), so the
  lookup returned the WRONG row for any weapon whose LeekScript id
  collides with a different generator id. Destroyer (LS 40) was reading
  Quantum Rifle's stats (gen 40, range 5-10) instead of its own 1-6.

This script only touches the WEAPON_DATABASE block. CHIP_DATABASE is
already correctly keyed by LeekScript IDs (chip ids and items.id match).
"""

import json
import re
import sys
from pathlib import Path

REPO = Path("/home/ubuntu/LeekWars-AI")
WEAPONS_JSON = Path("/home/ubuntu/leek-wars-generator/data/weapons.json")
# Optional argv[1]: the item_database.lk to re-key (default V8; pass
# V9_modules/item_database.lk or an absolute scratch path).
DB_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else REPO / "V8_modules" / "item_database.lk"

# WEAPON_DATABASE spans these line numbers (1-indexed, inclusive).
# Verified by inspection: opens at line 2 with `global WEAPON_DATABASE = [`
# and closes with `]` at line 327. We only remap keys WITHIN this block.
WEAPON_DB_START_LINE = 2
WEAPON_DB_END_LINE = 327


def load_id_map():
    data = json.load(open(WEAPONS_JSON))
    items = data if isinstance(data, list) else list(data.values())
    gen_to_ls = {}
    for it in items:
        gen = it["id"]
        ls = it.get("item")
        if ls is None:
            raise SystemExit(f"weapons.json entry {gen} ({it.get('name')}) missing 'item'")
        if gen in gen_to_ls and gen_to_ls[gen] != ls:
            raise SystemExit(f"duplicate gen id {gen}")
        gen_to_ls[gen] = ls
    return gen_to_ls


def main():
    gen_to_ls = load_id_map()
    lines = DB_FILE.read_text().splitlines(keepends=True)

    # Verify the boundaries are what we expect.
    # Locate the block by content: the generated file opens with a comment
    # header, so hardcoded line numbers (inspected on an older hand-edited
    # file) point at a comment and abort.
    starts = [i for i, l in enumerate(lines) if l.startswith("global WEAPON_DATABASE = [")]
    if len(starts) != 1:
        raise SystemExit("could not locate a unique 'global WEAPON_DATABASE = [' line")
    WEAPON_DB_START_LINE = starts[0] + 1
    end = next((i for i in range(starts[0] + 1, len(lines)) if lines[i].rstrip("\n") == "]"), None)
    if end is None:
        raise SystemExit("could not locate the WEAPON_DATABASE closing bracket")
    WEAPON_DB_END_LINE = end + 1

    # Match `    9: [` style key lines. Use [ \t]* (horizontal whitespace
    # only) so the regex never gobbles the trailing newline that
    # splitlines(keepends=True) leaves on each entry.
    key_re = re.compile(r"^([ \t]+)(\d+)([ \t]*:[ \t]*\[[ \t]*)$", re.MULTILINE)
    rewritten = 0
    unmapped = []
    seen_new_keys = set()

    for i in range(WEAPON_DB_START_LINE, WEAPON_DB_END_LINE):
        # Match against the line stripped of its trailing newline so
        # `$` doesn't risk swallowing it.
        stripped = lines[i].rstrip("\n")
        m = key_re.match(stripped)
        if not m:
            continue
        gen_id = int(m.group(2))
        if gen_id not in gen_to_ls:
            unmapped.append((i + 1, gen_id))
            continue
        ls_id = gen_to_ls[gen_id]
        if ls_id in seen_new_keys:
            raise SystemExit(f"collision: two gen ids would map to LS id {ls_id}")
        seen_new_keys.add(ls_id)
        lines[i] = f"{m.group(1)}{ls_id}{m.group(3)}\n"
        rewritten += 1

    if unmapped:
        print("Unmapped keys (skipped):")
        for ln, k in unmapped:
            print(f"  line {ln}: {k}")

    DB_FILE.write_text("".join(lines))
    print(f"Re-keyed {rewritten} weapon entries.")


if __name__ == "__main__":
    main()
