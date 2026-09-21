"""
Ladder behaviour analysis (2026-09-21). Reads data/ladder/*.json produced by
ladder_fetch_builds.py plus the solo-fight pools. Owner-normalised, first 10
turns, split by outcome and by owner / opponent archetype. See
docs/matchup_doctrine.md "What top players DO" for the findings and the
proxy caveats (denial is a proxy; condition on opponent archetype).

    python3 tools/ladder_play_analysis.py data/ladder/solo_fights_v2.json data/ladder/solo_fights_wide.json
    python3 tools/ladder_play_analysis.py data/ladder/our_solo.json
"""
import json, sys, statistics as st
from collections import Counter, defaultdict
sys.path.insert(0,'/home/ubuntu/LeekWars-AI/tools')
from lw_decode import Decoder
d=Decoder()
WIN=['manumission','jump','seven_league_boots','doping','rage','metallic_bulb','healer_bulb','soporific','reflexes','teleportation']
LOSE=['fortress','armor','remission','wall','elevation','shield','serum','armoring']
files=sys.argv[1:] or ['/home/ubuntu/LeekWars-AI/data/ladder/solo_fights_v2.json','/home/ubuntu/LeekWars-AI/data/ladder/solo_fights_wide.json']
fights={}
for f in files:
    try: fights.update(json.load(open(f)))
    except FileNotFoundError: pass
lad=json.load(open('/home/ubuntu/LeekWars-AI/data/ladder/leeks.json'))
def arch(l):
    s,m,sc=l.get('strength',0),l.get('magic',0),l.get('science',0)
    if m>max(s,sc): return 'MAG'
    if sc>=300 and sc>=s: return 'SCI'
    return 'STR'
recs=[]
for fid,f in fights.items():
    data=f['data']; ent=[l for l in data['leeks'] if l.get('name')==f['owner']]
    if not ent: continue
    me=ent[0]['id']; team=ent[0].get('team')
    ol=lad.get(str(f['owner_leek_id']))
    cur=None; t=0; c10=Counter(); myturns=0
    for a in data['actions']:
        if not isinstance(a,list) or not a: continue
        if a[0]==6: t+=1
        elif a[0]==7:
            cur=a[1] if len(a)>1 else None
            if cur==me: myturns+=1
        elif a[0]==12 and cur==me and len(a)>1 and t<=10: c10[d.chip(a[1])]+=1
    if myturns==0: continue
    recs.append({'owner':f['owner'],'arch':arch(ol) if ol else '?','won':f['winner']==team,
                 'turns':myturns,'c10':c10,'t10':min(myturns,10)})
owners=Counter(r['owner'] for r in recs)
print('fights %d   owners %d   (top-5 owner share %.0f%%)'%(len(recs),len(owners),100*sum(v for _,v in owners.most_common(5))/max(len(recs),1)))
print('overall owner win rate %.0f%%   mean turns %.1f'%(100*st.mean([r['won'] for r in recs]),st.mean([r['turns'] for r in recs])))
def owner_norm(rs,chips):
    per=defaultdict(lambda:defaultdict(float)); T=defaultdict(float)
    for r in rs:
        for c in chips: per[r['owner']][c]+=r['c10'].get(c,0)
        T[r['owner']]+=r['t10']
    out={}
    for c in chips:
        vals=[per[o][c]/T[o] for o in per if T[o]>=10]
        out[c]=st.mean(vals) if vals else 0.0
    return out, len([o for o in per if T[o]>=10])
for label,sel in (('ALL',lambda r:True),('STR builds',lambda r:r['arch']=='STR'),('MAG builds',lambda r:r['arch']=='MAG'),('SCI builds',lambda r:r['arch']=='SCI')):
    rs=[r for r in recs if sel(r)]
    if len(rs)<20: continue
    w=[r for r in rs if r['won']]; l=[r for r in rs if not r['won']]
    rw,nw=owner_norm(w,WIN+LOSE); rl,nl=owner_norm(l,WIN+LOSE)
    print()
    print('=== %s: %d fights, win %.0f%%  (owner-normalised, first 10 turns; %d/%d owners)'%(label,len(rs),100*len(w)/len(rs),nw,nl))
    print('   %-20s %7s %7s'%('chip','WON','LOST'))
    for c in WIN: print('   W %-18s %7.3f %7.3f'%(c,rw[c],rl[c]))
    for c in LOSE: print('   L %-18s %7.3f %7.3f'%(c,rw[c],rl[c]))
    print('   SUM winner-sig won %.3f lost %.3f | loser-sig won %.3f lost %.3f'%(
        sum(rw[c] for c in WIN),sum(rl[c] for c in WIN),sum(rw[c] for c in LOSE),sum(rl[c] for c in LOSE)))
