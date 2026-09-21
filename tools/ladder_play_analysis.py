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
files=sys.argv[1:]; fights={}
for f in files: fights.update(json.load(open(f)))
lad=json.load(open('/home/ubuntu/LeekWars-AI/data/ladder/leeks.json'))
def arch(l):
    s,m,sc=l.get('strength',0),l.get('magic',0),l.get('science',0)
    return 'MAG' if m>max(s,sc) else ('SCI' if sc>=300 and sc>=s else 'STR')
recs=[]
for fid,f in fights.items():
    data=f['data']; ent=[l for l in data['leeks'] if l.get('name')==f['owner']]
    if not ent: continue
    me=ent[0]['id']; team=ent[0].get('team'); ol=lad.get(str(f['owner_leek_id']))
    opp=[l for l in data['leeks'] if l.get('id')!=me]
    oarch=arch(opp[0]) if opp else '?'
    cur=None; t=0
    turns=defaultdict(list)          # (turn, actor) -> ordered action tokens
    dmg_to_me=defaultdict(int); enemy_shots=defaultdict(int); enemy_tp_used=defaultdict(int)
    for a in data['actions']:
        if not isinstance(a,list) or not a: continue
        c=a[0]
        if c==6: t+=1; continue
        if c==7: cur=a[1] if len(a)>1 else None; continue
        if cur is None: continue
        if c==12 and len(a)>1: turns[(t,cur)].append('c:'+d.chip(a[1]))
        elif c==13 and len(a)>1: turns[(t,cur)].append('w:'+d.weapon(a[1]))
        elif c==16: turns[(t,cur)].append('FIRE')
        elif c==10: turns[(t,cur)].append('MOVE')
        if cur!=me and c==16: enemy_shots[t]+=1
        if cur!=me and c in (101,107,109) and len(a)>2 and a[1]==me: dmg_to_me[t]+=a[2]
    myturns=sorted(tt for (tt,act) in turns if act==me)
    if not myturns: continue
    won=(f['winner']==team)
    # positional proxies over our first 10 turns
    denied=0; hnh=0; zero=0; n=0
    for tt in myturns[:10]:
        seq=turns[(tt,me)]; n+=1
        # enemy's next turn (same round index tt if they act after us, else tt+1)
        # use round tt AND tt+1 to be robust to turn order
        shots=enemy_shots.get(tt,0)+enemy_shots.get(tt+1,0)
        if shots==0: denied+=1
        if 'FIRE' in seq and 'MOVE' in seq and max(i for i,x in enumerate(seq) if x=='MOVE')>seq.index('FIRE'): hnh+=1
        if 'FIRE' not in seq and not any(x.startswith('c:') and x[2:] in ('venom','toxin','plague','arsenic','covid','lightning','spark','flame','meteorite','rockfall','iceberg','stalactite','pebble','rock','ice','thunder','burning') for x in seq): zero+=1
    # combos: ordered chip-only bigrams per turn (first 10 turns), and T1 opening
    big=Counter(); pairs=Counter(); t1=None
    for tt in myturns[:10]:
        chips=[x[2:] for x in turns[(tt,me)] if x.startswith('c:')]
        for i in range(len(chips)-1): big[(chips[i],chips[i+1])]+=1
        for i in range(len(chips)):
            for j in range(i+1,len(chips)): pairs[tuple(sorted((chips[i],chips[j])))]+=1
        if t1 is None: t1=' > '.join(chips[:4]) or '(no chips T1)'
    recs.append({'owner':f['owner'],'arch':arch(ol) if ol else '?','oarch':oarch,'won':won,'n':n,
                 'denied':denied,'hnh':hnh,'zero':zero,'big':big,'pairs':pairs,'t1':t1})
print('fights %d owners %d'%(len(recs),len({r['owner'] for r in recs})))
def onorm(rs,key):
    per=defaultdict(lambda:[0,0])
    for r in rs: per[r['owner']][0]+=r[key]; per[r['owner']][1]+=r['n']
    v=[a/b for a,b in per.values() if b>=10]; return st.mean(v) if v else 0
for label,sel in (('ALL',lambda r:True),('STR',lambda r:r['arch']=='STR'),('MAG',lambda r:r['arch']=='MAG'),
                  ('vs STR opponents (weapon users)',lambda r:r['oarch']=='STR'),('vs MAG opponents',lambda r:r['oarch']=='MAG')):
    rs=[r for r in recs if sel(r)]
    if len(rs)<50: continue
    w=[r for r in rs if r['won']]; l=[r for r in rs if not r['won']]
    print('\n=== %s  (%d fights)  share of our first-10 turns, owner-normalised, WON vs LOST:'%(label,len(rs)))
    for key,name in (('denied','enemy fired NO weapon on their next turn (area/LoS denial)'),
                     ('hnh','we MOVED AFTER firing (hit-and-hide)'),
                     ('zero','we dealt no damage this turn')):
        print('   %-58s %.2f   %.2f'%(name,onorm(w,key),onorm(l,key)))
    # combos enriched in wins vs losses (owner-agnostic counts, min support)
    def agg(rs,k):
        c=Counter(); T=0
        for r in rs: c.update(r[k]); T+=r['n']
        return c,T
    cw,Tw=agg(w,'pairs'); cl,Tl=agg(l,'pairs')
    rows=[]
    for k in set(cw)|set(cl):
        if cw[k]+cl[k]<40: continue
        rows.append((cw[k]/max(Tw,1)-cl[k]/max(Tl,1),cw[k]/max(Tw,1),cl[k]/max(Tl,1),k))
    rows.sort(reverse=True)
    print('   same-turn chip PAIRS most enriched in WINS (per our turn):')
    for dd,a,b,k in rows[:6]: print('      %-38s won %.3f lost %.3f  %+.3f'%(' + '.join(k),a,b,dd))
    print('   ...most enriched in LOSSES:')
    for dd,a,b,k in rows[-4:]: print('      %-38s won %.3f lost %.3f  %+.3f'%(' + '.join(k),a,b,dd))
    t1w=Counter(r['t1'] for r in w); t1l=Counter(r['t1'] for r in l)
    print('   top T1 openings (won-share vs lost-share):')
    for k,_ in (t1w+t1l).most_common(5): print('      %-52s won %.2f lost %.2f'%(k,t1w[k]/max(len(w),1),t1l[k]/max(len(l),1)))
