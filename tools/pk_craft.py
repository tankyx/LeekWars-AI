#!/usr/bin/env python3
"""Craft the Pumpkin target components (tools/pk_progress.py TARGETS) whenever the stock allows, and equip each
on its leek in place of the component it replaces (owner 2026-11-03: "Craft everything we need").

    python3 tools/pk_craft.py --dry-run     # what would be crafted / equipped now
    python3 tools/pk_craft.py               # craft + equip

Ingredients short in stock are crafted through every owned scheme (sand <- rock + pebble, orange <- apple, kirabo,
motherboard -> motherboard2 ...). Targets are served in TARGETS order (per account: quince, motherboard3, chestnut, each leek in its list order);
a target whose leek no longer wears the replaced component is done. The ladder-revert snapshot
(data/ladder/pk_respec_snapshot.json, used by pk_respec.py revert) gets the new component at the same index;
main's boss swaps snapshot the live components at each batch, Cure's only swap chips.
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession
import pk_progress as pp

BULK = ('sand', 'apple')       # crafted by the dozen: counted, not logged one by one
SNAP = os.path.join(ROOT, 'data', 'ladder', 'pk_respec_snapshot.json')
LEEKS = {'main': {'Kirby54': 20443, 'GTGabi': 129288, 'Zoulman': 129295, 'Payou': 129296},
         'cure': {'LeekRain': 19703, 'DawnFall': 21175, 'DuskHope': 129801, 'ProdigalSon': 130236}}


def ok(r):
    return not (isinstance(r, dict) and (r.get('error') or r.get('success') is False))


class Acct:
    def __init__(self, name):
        self.name = name; self.lw = LWSession(name)
        I = self.lw.get('/item/get-all'); I = I.get('items', I)
        self.nm = {int(k): v['name'] for k, v in I.items()}
        self.tid = {v: k for k, v in self.nm.items()}
        self.recipes, self.scheme = pp.owned_recipes(self.lw, self.nm, I)
        self.counts = {}
        self.refresh()

    def refresh(self):
        self.inv = pp.inventory(self.lw, self.nm)

    def plain_stack(self, comp):
        f = self.lw.get('/farmer/get-from-token'); f = f.get('farmer', f)
        return next((x['id'] for x in f.get('components') or [] if self.nm.get(x['template']) == comp and not x.get('stats')
                     and (x.get('quantity') or 0) > 0), None)

    def ensure(self, item, qty, dry, log, depth=0):
        """Have qty of item in stock, crafting what is short through the owned recipes. False if a raw is short."""
        have = self.inv.get(item, 0)
        if have >= qty:
            return True
        if item not in self.recipes or depth > 5:
            return False
        for _ in range(qty - have):
            for ing, k in self.recipes[item]:
                if not self.ensure(ing, k, dry, log, depth + 1):
                    return False
            if not self.craft(item, dry, log):
                return False
        return True

    def craft(self, item, dry, log):
        self.counts[item] = self.counts.get(item, 0) + 1
        if item not in BULK:
            log('craft %s (scheme %s)%s' % (item, self.scheme[item], ' [dry]' if dry else ''))
        if not dry:
            for _ in range(5):
                r = self.lw.post('/item/craft', scheme_id=self.scheme[item])
                if isinstance(r, dict) and r.get('error') == 'rate_limit':
                    time.sleep(1.5); continue
                break
            if not ok(r):
                log('   craft %s FAILED: %s' % (item, str(r)[:160]))
                self.refresh()
                return False
            time.sleep(0.2)
        # stock bookkeeping without a refetch per craft (sand x47 ...); refreshed after each equip
        for ing, k in self.recipes[item]:
            self.inv[ing] = self.inv.get(ing, 0) - k
        self.inv[item] = self.inv.get(item, 0) + 1
        return True

    def equip(self, leek, lid, comp, old, dry, log, snap):
        l = self.lw.get('/leek/get/%d' % lid); l = l.get('leek', l)
        cs = l.get('components') or []
        idx = next((i for i, c in enumerate(cs) if c and self.nm.get(c['template']) == old), None)
        if idx is None:
            log('   %s no longer wears %s: not equipped' % (leek, old)); return False
        log('equip %s on %s slot %d (replaces %s)%s' % (comp, leek, idx, old, ' [dry]' if dry else ''))
        if dry:
            return True
        new = self.plain_stack(comp)
        if new is None:
            log('   no plain %s in stock' % comp); return False
        r1 = self.lw.call('DELETE', '/leek/remove-component', leek_id=lid, component_id=cs[idx]['id'])
        r2 = self.lw.post('/leek/add-component', leek_id=lid, component_id=new, index=idx)
        l = self.lw.get('/leek/get/%d' % lid); l = l.get('leek', l)
        got = (l.get('components') or [None] * (idx + 1))[idx]
        if not got or self.nm.get(got['template']) != comp:
            log('   equip FAILED (remove %s, add %s): putting %s back' % (str(r1)[:80], str(r2)[:80], old))
            back = self.plain_stack(old) or next((x['id'] for x in (self.lw.get('/farmer/get-from-token').get('farmer') or {}).get('components') or []
                                                  if self.nm.get(x['template']) == old), None)
            if back is not None:
                self.lw.post('/leek/add-component', leek_id=lid, component_id=back, index=idx)
            return False
        if leek in snap and snap[leek].get('components') and idx < len(snap[leek]['components']):
            snap[leek]['components'][idx] = [got['template'], got['id']]
        log('   %s slot %d = %s (instance %s); total TP %s MP %s, chip slots %s' % (leek, idx, comp, got['id'], l.get('total_tp'),
                                                                                  l.get('total_mp'), l.get('max_chips')))
        return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--acct', default='', help='main or cure (default both)')
    a = ap.parse_args()
    snap = json.load(open(SNAP)) if os.path.exists(SNAP) else {}
    done = 0
    for acct, targets in pp.TARGETS.items():
        if a.acct and acct != a.acct:
            continue
        A = Acct(acct)

        def log(s):
            print('%-4s %s' % (acct, s))
        for comp, slots in targets.items():
            for leek, old in slots:
                lid = LEEKS[acct][leek]
                l = A.lw.get('/leek/get/%d' % lid); l = l.get('leek', l)
                if not any(c and A.nm.get(c['template']) == old for c in (l.get('components') or [])):
                    continue                    # done (or the slot changed): nothing to do
                short = pp.needs(A.recipes, comp, 1, A.inv) if A.inv.get(comp, 0) < 1 else {}
                if short:
                    log('%s for %s: short %s' % (comp, leek, ', '.join('%s %d' % kv for kv in short.items())))
                    continue
                if not A.ensure(comp, 1, a.dry_run, log):
                    log('%s for %s: crafting stopped' % (comp, leek)); continue
                bulk = ', '.join('%s x%d' % (k, v) for k, v in A.counts.items() if k in BULK)
                if bulk:
                    log('   (crafted %s)' % bulk)
                A.counts = {}
                if A.equip(leek, lid, comp, old, a.dry_run, log, snap):
                    done += 1
                if a.dry_run:
                    A.inv[comp] = A.inv.get(comp, 0) - 1
                else:
                    A.refresh()
    if done and not a.dry_run:
        json.dump(snap, open(SNAP, 'w'), indent=1)
    print('%d component(s) %s' % (done, 'would be equipped' if a.dry_run else 'crafted and equipped'))


if __name__ == '__main__':
    main()
