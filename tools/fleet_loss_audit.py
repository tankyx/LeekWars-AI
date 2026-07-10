#!/usr/bin/env python3
"""Fleet loss-miner: pull each leek's recent ladder history, classify every
solo loss/draw by the winning enemy's build archetype, and dump our loadouts.

This industrializes the manual loss audits that found the ED Antidote gap.

Usage:
    python3 tools/fleet_loss_audit.py                 # both accounts, all leeks
    python3 tools/fleet_loss_audit.py --account main
    python3 tools/fleet_loss_audit.py --json out.json
"""
import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"
GEN_DATA = "/home/ubuntu/leek-wars-generator/data"
SLEEP = 0.15


def load_item_names():
    """API 'template' id -> name. For chips the API template equals the
    generator chip `id`; for weapons it equals the generator `item` field."""
    names = {"chip": {}, "weapon": {}}
    for kind, fname, key in (("chip", "chips.json", "id"),
                             ("weapon", "weapons.json", "item")):
        try:
            data = json.load(open(os.path.join(GEN_DATA, fname)))
        except OSError:
            continue
        for entry in data.values():
            if entry.get(key) is not None:
                names[kind][entry[key]] = entry.get("name", "?")
    return names


def classify_archetype(lk):
    """Mirror of detectBuildType() in weight_profiles.lk, on raw API stats."""
    s = lk.get("strength", 0) or 0
    m = lk.get("magic", 0) or 0
    a = lk.get("agility", 0) or 0
    sc = lk.get("science", 0) or 0
    r = lk.get("resistance", 0) or 0
    w = lk.get("wisdom", 0) or 0
    if r >= 300 and sc >= 300:
        return "tank_sci"
    if r >= 250 and w >= 250 and s < 300 and m < 300 and sc < 300 and a < 300:
        return "sustain_support"
    if s > 400 and a > 400:
        return "bruiser_reflect"
    if m >= s + 100:
        return "hybrid_mag" if s >= 200 else "magic"
    if abs(s - m) < 100 and m >= 100 and s >= 100:
        return "hybrid"
    if a >= s and a >= m:
        return "agility"
    if m >= s:
        return "magic"
    return "strength"


class Auditor:
    def __init__(self, account):
        self.account = account
        email, password = load_credentials(account=account)
        self.session = requests.Session()
        r = self.session.post(f"{BASE_URL}/farmer/login-token",
                              data={"login": email, "password": password})
        r.raise_for_status()
        self.farmer = r.json().get("farmer", {})
        self.leek_cache = {}

    def get(self, path):
        time.sleep(SLEEP)
        r = self.session.get(f"{BASE_URL}/{path}")
        r.raise_for_status()
        return r.json()

    def get_leek(self, leek_id):
        if leek_id not in self.leek_cache:
            self.leek_cache[leek_id] = self.get(f"leek/get/{leek_id}")
        return self.leek_cache[leek_id]

    def audit_leek(self, leek_id, name):
        hist = self.get(f"history/get-leek-history/{leek_id}").get("fights", [])

        def ids(side):
            return [e["id"] if isinstance(e, dict) else e for e in side]

        solo = []
        for f in hist:
            f["leeks1"] = ids(f.get("leeks1", []))
            f["leeks2"] = ids(f.get("leeks2", []))
            if len(f["leeks1"]) == 1 and len(f["leeks2"]) == 1:
                solo.append(f)
        results = Counter()
        losses, draws = [], []
        for f in solo:
            on_side1 = leek_id in f["leeks1"]
            opp_id = (f["leeks2"] if on_side1 else f["leeks1"])[0]
            winner = f.get("winner", 0)
            if winner == 0:
                res = "D"
            elif (winner == 1) == on_side1:
                res = "W"
            else:
                res = "L"
            results[res] += 1
            if res in ("L", "D"):
                (losses if res == "L" else draws).append(
                    {"fight": f["id"], "opp_id": opp_id, "date": f.get("date")})

        # Profile every distinct opponent we lost/drew to
        opp_profiles = {}
        for rec in losses + draws:
            oid = rec["opp_id"]
            if oid in opp_profiles:
                continue
            try:
                lk = self.get_leek(oid)
            except requests.RequestException:
                continue
            opp_profiles[oid] = {
                "name": lk.get("name", "?"),
                "level": lk.get("level"),
                "talent": lk.get("talent"),
                "stats": {k: lk.get(k, 0) for k in
                          ("strength", "magic", "agility", "science",
                           "resistance", "wisdom", "life", "tp", "mp",
                           "frequency")},
                "archetype": classify_archetype(lk),
                "chips": sorted(c.get("template", c.get("id"))
                                for c in lk.get("chips", [])),
                "weapons": sorted(wp.get("template", wp.get("id"))
                                  for wp in lk.get("weapons", [])),
            }

        loss_arch = Counter(opp_profiles[r["opp_id"]]["archetype"]
                            for r in losses if r["opp_id"] in opp_profiles)
        draw_arch = Counter(opp_profiles[r["opp_id"]]["archetype"]
                            for r in draws if r["opp_id"] in opp_profiles)
        farmers = Counter(r["opp_id"] for r in losses)

        our = self.get_leek(leek_id)
        return {
            "leek_id": leek_id,
            "name": name,
            "talent": our.get("talent"),
            "stats": {k: our.get(k, 0) for k in
                      ("strength", "magic", "agility", "science",
                       "resistance", "wisdom", "life", "tp", "mp",
                       "frequency")},
            "chips": sorted(c.get("template", c.get("id"))
                            for c in our.get("chips", [])),
            "weapons": sorted(wp.get("template", wp.get("id"))
                              for wp in our.get("weapons", [])),
            "solo_sample": len(solo),
            "record": dict(results),
            "loss_archetypes": dict(loss_arch),
            "draw_archetypes": dict(draw_arch),
            "repeat_losers": {oid: n for oid, n in farmers.items() if n >= 2},
            "opponents": opp_profiles,
            "losses": losses,
            "draws": draws,
        }


def render(report, names):
    out = []
    for acct, leeks in report.items():
        out.append(f"\n{'=' * 70}\nACCOUNT: {acct}\n{'=' * 70}")
        for lr in leeks:
            rec = lr["record"]
            n = lr["solo_sample"]
            w, l, d = rec.get("W", 0), rec.get("L", 0), rec.get("D", 0)
            out.append(f"\n--- {lr['name']} (T{lr['talent']}) — last {n} solo: "
                       f"{w}W/{l}L/{d}D ---")
            st = lr["stats"]
            out.append("  stats: " + " ".join(
                f"{k[:3].upper()}:{st[k]}" for k in
                ("strength", "magic", "agility", "science", "resistance",
                 "wisdom")))
            out.append("  chips: " + ", ".join(
                names["chip"].get(c, str(c)) for c in lr["chips"]))
            out.append("  weapons: " + ", ".join(
                names["weapon"].get(wp, str(wp)) for wp in lr["weapons"]))
            if lr["loss_archetypes"]:
                out.append("  losses by archetype: " + ", ".join(
                    f"{k}:{v}" for k, v in sorted(
                        lr["loss_archetypes"].items(), key=lambda x: -x[1])))
            if lr["draw_archetypes"]:
                out.append("  draws by archetype: " + ", ".join(
                    f"{k}:{v}" for k, v in sorted(
                        lr["draw_archetypes"].items(), key=lambda x: -x[1])))
            for oid, cnt in sorted(lr["repeat_losers"].items(),
                                   key=lambda x: -x[1]):
                p = lr["opponents"].get(oid, {})
                stats = p.get("stats", {})
                out.append(f"  FARMER x{cnt}: {p.get('name', oid)} "
                           f"T{p.get('talent')} [{p.get('archetype')}] "
                           + " ".join(f"{k[:3].upper()}:{v}"
                                      for k, v in stats.items()
                                      if k in ("strength", "magic", "agility",
                                               "wisdom", "resistance",
                                               "science") and v))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", choices=["main", "cure"], default=None)
    ap.add_argument("--json", default=None,
                    help="also dump full report JSON to this path")
    args = ap.parse_args()

    names = load_item_names()
    accounts = [args.account] if args.account else ["main", "cure"]
    report = {}
    for acct in accounts:
        aud = Auditor(acct)
        leeks = aud.farmer.get("leeks", {})
        if isinstance(leeks, dict):
            leeks = list(leeks.values())
        report[acct] = []
        for lk in leeks:
            print(f"[{acct}] auditing {lk['name']}...", file=sys.stderr)
            report[acct].append(aud.audit_leek(lk["id"], lk["name"]))

    print(render(report, names))
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(report, fh, indent=1)
        print(f"\nJSON: {args.json}")


if __name__ == "__main__":
    main()
