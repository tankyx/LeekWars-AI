import sys, json
sys.path.insert(0,'/home/ubuntu/LeekWars-AI/tools')
from lw_api import LWSession
lw=LWSession('main')
rows=json.load(open('/home/ubuntu/LeekWars-AI/data/ladder/ranking.json'))
out={}; skipped=0
for i,r in enumerate(rows):
    lid=r['id']
    d=lw.get(f'/leek/get/{lid}')
    if not isinstance(d,dict): skipped+=1; continue
    leek=d.get('leek') if isinstance(d.get('leek'),dict) else d
    if not isinstance(leek,dict) or 'strength' not in leek: skipped+=1; continue
    g=lambda k,dv=0: leek.get(k) if leek.get(k) is not None else dv
    out[str(lid)]={'rank':r['rank'],'talent':r['talent'],'name':leek.get('name'),
        'farmer':r.get('farmer'),'level':g('level'),'life':g('life'),'tp':g('tp'),'mp':g('mp'),
        'strength':g('strength'),'magic':g('magic'),'agility':g('agility'),
        'wisdom':g('wisdom'),'resistance':g('resistance'),'science':g('science'),
        'frequency':g('frequency',100),'cores':g('cores',1),'ram':g('ram',1),
        'weapons':[w.get('template') for w in (leek.get('weapons') or []) if isinstance(w,dict)],
        'chips':[c.get('template') for c in (leek.get('chips') or []) if isinstance(c,dict)],
        'components':[{'template':c.get('template'),'stats':c.get('stats'),
                       'altered_power':c.get('altered_power')}
                      for c in (leek.get('components') or []) if isinstance(c,dict)]}
    if (i+1)%50==0:
        print('fetched %d/%d (skipped %d)'%(i+1,len(rows),skipped), flush=True)
        json.dump(out, open('/home/ubuntu/LeekWars-AI/data/ladder/leeks.json','w'))
json.dump(out, open('/home/ubuntu/LeekWars-AI/data/ladder/leeks.json','w'))
print('DONE %d leeks, %d skipped'%(len(out),skipped), flush=True)
