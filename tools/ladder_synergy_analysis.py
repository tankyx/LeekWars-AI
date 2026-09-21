"""
Chip -> weapon synergies within a turn: does a buff precede the shots, how many
shots follow, which (buff, weapon) pairs are enriched in wins. Owner-normalised,
first 10 turns, split by outcome. Same inputs as ladder_play_analysis.py.

    python3 tools/ladder_synergy_analysis.py data/ladder/solo_fights_v2.json data/ladder/solo_fights_wide.json
    python3 tools/ladder_synergy_analysis.py data/ladder/our_solo.json
"""
import json, sys, statistics as st
from collections import Counter, defaultdict
sys.path.insert(0,'/home/ubuntu/LeekWars-AI/tools')
from lw_decode import Decoder
d=Decoder()
BUFF={'steroid','warm_up','doping','protein','rage','reflexes','adrenaline','motivation','prism','knowledge',
      'wizardry','stretching','leather_boots','seven_league_boots','winged_boots','precipitation','acceleration',
      'elevation','armoring','solidification','fortress','wall','armor','shield','helmet','mirror','thorn','bramble'}
OFF={'steroid','warm_up','doping','protein','rage','reflexes','adrenaline','motivation','prism','knowledge','wizardry','stretching','precipitation','acceleration'}
fights={}
for f in sys.argv[1:]: fights.update(json.load(open(f)))
recs=[]
for fid,f in fights.items():
    data=f['data']; ent=[l for l in data['leeks'] if l.get('name')==f['owner']]
    if not ent: continue
    me=ent[0]['id']; team=ent[0].get('team'); cur=None; t=0
    turns=defaultdict(list)
    for a in data['actions']:
        if not isinstance(a,list) or not a: continue
        c=a[0]
        if c==6: t+=1; continue
        if c==7: cur=a[1] if len(a)>1 else None; continue
        if cur!=me: continue
        if c==12 and len(a)>1: turns[t].append(('c',d.chip(a[1])))
        elif c==13 and len(a)>1: turns[t].append(('w',d.weapon(a[1])))
        elif c==16: turns[t].append(('F',None))
    my=sorted(turns)[:10]
    if not my: continue
    r={'owner':f['owner'],'won':f['winner']==team,'n':len(my),'bf':0,'shots_b':[],'shots_nb':[],
       'pairs':Counter(),'adr':0,'adr_shots':[],'fire_turns':0}
    for tt in my:
        seq=turns[tt]; held=None; buffs_before=[]; shots=0; fired=False
        for kind,name in seq:
            if kind=='w': held=name
            elif kind=='c':
                if not fired and name in BUFF: buffs_before.append(name)
            elif kind=='F':
                fired=True; shots+=1
                for b in buffs_before:
                    if b in OFF and held: r['pairs'][(b,held)]+=1
        if fired: r['fire_turns']+=1
        offb=[b for b in buffs_before if b in OFF]
        if fired and offb: r['bf']+=1; r['shots_b'].append(shots)
        elif fired: r['shots_nb'].append(shots)
        if 'adrenaline' in buffs_before: r['adr']+=1; r['adr_shots'].append(shots)
    recs.append(r)
print('fights %d owners %d'%(len(recs),len({r['owner'] for r in recs})))
def onorm(rs,num,den):
    per=defaultdict(lambda:[0,0])
    for r in rs: per[r['owner']][0]+=num(r); per[r['owner']][1]+=den(r)
    v=[a/b for a,b in per.values() if b>=10]; return st.mean(v) if v else 0
w=[r for r in recs if r['won']]; l=[r for r in recs if not r['won']]
print('\n%-62s %7s %7s'%('per turn (first 10), owner-normalised','WON','LOST'))
print('%-62s %7.2f %7.2f'%('turns with an OFFENSIVE buff cast BEFORE firing / firing turns',onorm(w,lambda r:r['bf'],lambda r:max(r['fire_turns'],1)),onorm(l,lambda r:r['bf'],lambda r:max(r['fire_turns'],1))))
sb=[s for r in w for s in r['shots_b']]; snb=[s for r in w for s in r['shots_nb']]
sbl=[s for r in l for s in r['shots_b']]; snbl=[s for r in l for s in r['shots_nb']]
print('%-62s %7.2f %7.2f'%('shots in a turn WITH a preceding offensive buff (mean)',st.mean(sb) if sb else 0,st.mean(sbl) if sbl else 0))
print('%-62s %7.2f %7.2f'%('shots in a turn WITHOUT one (mean)',st.mean(snb) if snb else 0,st.mean(snbl) if snbl else 0))
aw=[s for r in w for s in r['adr_shots']]; al=[s for r in l for s in r['adr_shots']]
print('%-62s %7.2f %7.2f'%('adrenaline turns: shots that turn (mean)',st.mean(aw) if aw else 0,st.mean(al) if al else 0))
def agg(rs):
    c=Counter(); T=0
    for r in rs: c.update(r['pairs']); T+=r['n']
    return c,T
cw,Tw=agg(w); cl,Tl=agg(l); rows=[]
for k in set(cw)|set(cl):
    if cw[k]+cl[k]<30: continue
    rows.append((cw[k]/max(Tw,1)-cl[k]/max(Tl,1),cw[k]/max(Tw,1),cl[k]/max(Tl,1),k))
rows.sort(reverse=True)
print('\n(buff -> weapon fired) pairs per turn, most enriched in WINS:')
for dd,a,b,k in rows[:8]: print('   %-18s -> %-22s won %.3f lost %.3f  %+.3f'%(k[0],k[1],a,b,dd))
print('...most enriched in LOSSES:')
for dd,a,b,k in rows[-5:]: print('   %-18s -> %-22s won %.3f lost %.3f  %+.3f'%(k[0],k[1],a,b,dd))
