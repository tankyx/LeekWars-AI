#!/usr/bin/env python3
"""
Loss autopsy over saved local fights (one JSON per fight with `leeks`,
`actions`, `result`, `opp`, `seed`, as written by the collector in
docs/matchup_doctrine.md "Loss autopsy"). Splits each opponent into wins
and losses and prints, side by side: fight length, death turn, HP-lead
trajectory by turn, damage taken/dealt per turn (early vs late), poison
landed, heals, opening distances, chip/weapon usage per fight, damage
sources on us, and what the enemy did on the killing turn.

    python3 tools/loss_autopsy.py /tmp/autopsy
"""
import json,glob,sys,statistics as st
from collections import defaultdict,Counter
sys.path.insert(0,'/home/ubuntu/LeekWars-AI/tools')
from lw_decode import Decoder
D=Decoder()
# diamond map: even rows 18 cells, odd rows 17 (613 total)
_xy={}
c=0
for r in range(35):
    n=18 if r%2==0 else 17
    for k in range(n): _xy[c]=(2*k+(r%2),r); c+=1
def dist(a,b):
    if a not in _xy or b not in _xy: return None
    (x1,y1),(x2,y2)=_xy[a],_xy[b]; return max(abs(x1-x2),abs(y1-y2))
def timeline(d):
    ours=[l['id'] for l in d['leeks'] if l.get('team')==1]; me=ours[0]
    them=[l['id'] for l in d['leeks'] if l.get('team')!=1]; en=them[0]
    mx={l['id']:l['life'] for l in d['leeks']}
    hp={i:mx[i] for i in mx}; cell={}
    T=1; cur=None; held={}
    turns=defaultdict(lambda: defaultdict(lambda: dict(taken=Counter(),healed=0,chips=[],weapons=[],moved=0,src=Counter(),effects=[],endcell=None,tpstart=None)))
    death={}; firstfire={}
    for a in d['actions']:
        if not isinstance(a,list) or not a: continue
        c=a[0]
        if c==6: T=a[1] if len(a)>1 else T+1; continue
        if c==7: cur=a[1]; continue
        if cur is None: continue
        rec=turns[T][cur]
        if c==8 and len(a)>3: rec['tpstart']=(a[2],a[3])
        elif c==10 and len(a)>2:
            if cur not in cell and len(a)>3 and a[3]: cell[cur]=a[3][0]
            cell[cur]=a[2]; rec['moved']+=1; rec['endcell']=a[2]
        elif c==13 and len(a)>1: held[cur]=a[1]
        elif c==12 and len(a)>1:
            nm=D.chip(a[1]); rec['chips'].append(nm); firstfire.setdefault(cur,T) if nm and ('poison' in str(nm).lower() or True) else None
        elif c==16:
            nm=D.weapon(held.get(cur,-1)); rec['weapons'].append(nm); firstfire.setdefault(cur,T)
        elif c in (101,107,109,110,108) and len(a)>2:
            kind={101:'direct',107:'nova',109:'life',110:'poison',108:'return'}[c]
            tgt=a[1]; turns[T][tgt]['taken'][kind]+=a[2]; hp[tgt]-=a[2]
            if kind in ('direct','nova','life') and cur!=tgt:
                src=(rec['weapons'][-1] if rec['weapons'] and (not rec['chips'] or True) else None)
                # attribute to the most recent use action by the actor
                last=rec.get('_last'); rec['src'][last or '?']+=a[2]
        elif c==103 and len(a)>2: turns[T][a[1]]['healed']+=a[2]; hp[a[1]]=min(mx[a[1]],hp[a[1]]+a[2])
        elif c==104 and len(a)>2: mx[a[1]]+=a[2]; hp[a[1]]+=a[2]
        elif c in (301,302) and len(a)>7:
            tgt=a[4]; turns[T][tgt]['effects'].append((D.effect(a[5]) if hasattr(D,'effect') else a[5],a[6],a[7],cur))
        elif c==5 and len(a)>1: death[a[1]]=T
        if c==12 and len(a)>1: rec['_last']=D.chip(a[1])
        if c==16: rec['_last']=D.weapon(held.get(cur,-1))
        if c in (12,16): pass
        # snapshot hp at end of each action: keep last
        turns[T]['_hp']={i:hp[i] for i in mx}
        turns[T]['_cell']=dict(cell)
    return dict(me=me,en=en,mx=mx,turns=turns,death=death,firstfire=firstfire,T=T)
def summarize(files):
    byopp=defaultdict(lambda: defaultdict(list))
    for fn in files:
        d=json.load(open(fn)); tl=timeline(d); res=d['result']
        me,en,mx=tl['me'],tl['en'],tl['mx']
        Ts=sorted(t for t in tl['turns'] if isinstance(t,int))
        hpme=[tl['turns'][t]['_hp'][me] for t in Ts]; hpen=[tl['turns'][t]['_hp'][en] for t in Ts]
        lead=[100*hpme[i]/mx[me]-100*hpen[i]/mx[en] for i in range(len(Ts))]
        # turn the lead goes negative for good
        neg=None
        for i in range(len(Ts)):
            if all(x<0 for x in lead[i:]): neg=Ts[i]; break
        taken_me=[sum(tl['turns'][t][me]['taken'].values()) for t in Ts]
        taken_en=[sum(tl['turns'][t][en]['taken'].values()) for t in Ts]
        poison_en=[tl['turns'][t][en]['taken']['poison'] for t in Ts]
        en_chips=Counter(x for t in Ts for x in tl['turns'][t][en]['chips']); me_chips=Counter(x for t in Ts for x in tl['turns'][t][me]['chips'])
        en_w=Counter(x for t in Ts for x in tl['turns'][t][en]['weapons']); me_w=Counter(x for t in Ts for x in tl['turns'][t][me]['weapons'])
        src=Counter(); 
        for t in Ts: src.update(tl['turns'][t][en]['src'])
        dth=tl['death'].get(me); kill=None
        if dth is not None:
            kt=tl['turns'][dth][en]; kill=(sum(kt['taken'].values()), list(kt['chips']), list(kt['weapons']), taken_me[Ts.index(dth)] if dth in Ts else None)
        d12=[]
        for t in Ts[:3]:
            cl=tl['turns'][t]['_cell']; d12.append(dist(cl.get(me,-1),cl.get(en,-1)))
        r=dict(seed=d['seed'],len=len(Ts),death=dth,en_death=tl['death'].get(en),neg=neg,lead=lead,taken_me=taken_me,taken_en=taken_en,poison_en=poison_en,en_chips=en_chips,me_chips=me_chips,en_w=en_w,me_w=me_w,src=src,kill=kill,ff_me=tl['firstfire'].get(me),ff_en=tl['firstfire'].get(en),dist=d12,en_hp_at_end=100*hpen[-1]/mx[en],me_hp_at_end=100*hpme[-1]/mx[me],en_heal=sum(tl['turns'][t][en]['healed'] for t in Ts),me_heal=sum(tl['turns'][t][me]['healed'] for t in Ts))
        byopp[d['opp']][res].append(r)
    return byopp
def avg(xs): xs=[x for x in xs if x is not None]; return (sum(xs)/len(xs)) if xs else float('nan')
def med(xs): xs=[x for x in xs if x is not None]; return st.median(xs) if xs else float('nan')
def show(byopp):
    for opp in sorted(byopp):
        W=byopp[opp].get('WIN',[]); L=byopp[opp].get('LOSS',[])
        print('='*100); print('%s   wins %d  losses %d  draws %d'%(opp,len(W),len(L),len(byopp[opp].get('DRAW',[]))))
        def row(lbl,f,fmt='%6.1f'):
            print('  %-44s W '+fmt+'   L '+fmt) if False else print(('  %-44s W '+fmt+'   L '+fmt)%(lbl,f(W),f(L)))
        row('fight length (turns, median)',lambda R: med([r['len'] for r in R]))
        row('our death turn (median)',lambda R: med([r['death'] for r in R]))
        row('enemy HP% at end (mean)',lambda R: avg([r['en_hp_at_end'] for r in R]))
        row('our HP% at end (mean)',lambda R: avg([r['me_hp_at_end'] for r in R]))
        row('lead goes negative for good at turn (median)',lambda R: med([r['neg'] for r in R]))
        row('first fire turn: ours (median)',lambda R: med([r['ff_me'] for r in R]))
        row('first fire turn: enemy (median)',lambda R: med([r['ff_en'] for r in R]))
        row('dmg taken/turn T1-3 (mean)',lambda R: avg([x for r in R for x in r['taken_me'][:3]]))
        row('dmg taken/turn T4+ (mean)',lambda R: avg([x for r in R for x in r['taken_me'][3:]]))
        row('dmg dealt/turn T1-3 (mean)',lambda R: avg([x for r in R for x in r['taken_en'][:3]]))
        row('dmg dealt/turn T4+ (mean)',lambda R: avg([x for r in R for x in r['taken_en'][3:]]))
        row('poison dealt per fight (mean)',lambda R: avg([sum(r['poison_en']) for r in R]))
        row('poison dealt per turn (mean)',lambda R: avg([x for r in R for x in r['poison_en']]))
        row('enemy healed per fight (mean)',lambda R: avg([r['en_heal'] for r in R]))
        row('we healed per fight (mean)',lambda R: avg([r['me_heal'] for r in R]))
        row('distance after T1 (median)',lambda R: med([r['dist'][0] for r in R if r['dist']]))
        row('distance after T2 (median)',lambda R: med([r['dist'][1] for r in R if len(r['dist'])>1]))
        for lbl,key in [('enemy chips per fight','en_chips'),('our chips per fight','me_chips'),('enemy weapons per fight','en_w'),('our weapons per fight','me_w')]:
            cw=Counter(); cl=Counter()
            for r in W: cw.update(r[key])
            for r in L: cl.update(r[key])
            names=sorted(set(cw)|set(cl),key=lambda k:-(cw[k]+cl[k]))[:8]
            print('  %-44s '%lbl + '  '.join('%s W%.1f/L%.1f'%(str(n)[:14],cw[n]/max(len(W),1),cl[n]/max(len(L),1)) for n in names))
        srcL=Counter(); 
        for r in L: srcL.update(r['src'])
        print('  damage sources on us in LOSSES (per fight): '+', '.join('%s %.0f'%(str(k)[:16],v/max(len(L),1)) for k,v in srcL.most_common(5)))
        kills=[r['kill'] for r in L if r['kill']]
        if kills:
            print('  killing turn: dmg %.0f (mean); enemy actions: %s'%(avg([k[0] for k in kills]), Counter(x for k in kills for x in (k[1]+k[2])).most_common(6)))
        # lead trajectory
        for lbl,R in [('W',W),('L',L)]:
            if R:
                mxlen=max(len(r['lead']) for r in R)
                traj=[avg([r['lead'][i] for r in R if len(r['lead'])>i]) for i in range(min(mxlen,12))]
                print('  HP%%-lead by turn (%s): '%lbl+' '.join('%+.0f'%x for x in traj))
if __name__=='__main__':
    files=sorted(glob.glob((sys.argv[1] if len(sys.argv)>1 else '/tmp/autopsy')+'/*.json'))
    # distance self-check on one move path
    d=json.load(open(files[0]))
    for a in d['actions']:
        if isinstance(a,list) and a and a[0]==10 and len(a)>3 and len(a[3])>1:
            p=a[3]; print('dist self-check consecutive path cells:',[dist(p[i],p[i+1]) for i in range(len(p)-1)]); break
    show(summarize(files))
