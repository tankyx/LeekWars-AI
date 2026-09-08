#!/usr/bin/env python3
"""Farm the Nasu boss (boss 1, L100) for crafting parts. Runs N fights, tracks
resource/scheme deltas and wins. Usage: python3 tools/farm_nasu.py <N> [batch]"""
import sys, json, time, requests
sys.path.insert(0, 'tools')
from config_loader import load_credentials

LEEKS = [129295, 20443, 129296, 129288]
e, pw = load_credentials('main')


def login():
    s = requests.Session()
    j = s.post('https://leekwars.com/api/farmer/login-token', data={'login': e, 'password': pw}).json()
    s.headers['Authorization'] = 'Bearer ' + j['token']
    return s, j['farmer']


def snap(farmer):
    res = {x['template']: x['quantity'] for x in farmer.get('resources', [])}
    sch = {x['template']: x['quantity'] for x in farmer.get('schemes', [])}
    return res, sch, farmer.get('fights')


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    batch = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    s, farmer = login()
    res0, sch0, cred0 = snap(farmer)
    print(f'start: credits={cred0}, tracking resources+schemes', flush=True)
    done = 0
    wins = 0
    while done < n:
        k = min(batch, n - done)
        fids = []
        for _ in range(k):
            r = s.post('https://leekwars.com/api/garden/start-boss-fight',
                       data={'boss_id': 1, 'participants': json.dumps(LEEKS)}).json()
            if r.get('fight'):
                fids.append(r['fight'])
            elif r.get('error') == 'not_enough_fights':
                print('OUT OF CREDITS', flush=True); n = done; break
            time.sleep(2.5)
        time.sleep(max(15, k * 4))
        for fid in fids:
            try:
                fr = s.get(f'https://leekwars.com/api/fight/get/{fid}').json()
                if fr.get('winner') == 1:
                    wins += 1
            except Exception:
                pass
        done += len(fids)
        # re-login to refresh farmer snapshot
        s, farmer = login()
        res1, sch1, cred1 = snap(farmer)
        rd = {t: res1.get(t, 0) - res0.get(t, 0) for t in set(res0) | set(res1) if res1.get(t, 0) != res0.get(t, 0)}
        nsch = [t for t in sch1 if t not in sch0]
        print(f'  {done}/{n} fights | wins {wins} | credits {cred1} | res gains {rd} | NEW schemes {nsch}', flush=True)
    print(f'DONE: {done} fights, {wins} wins, credits now {cred1}', flush=True)
    print(f'total resource gains: {rd}', flush=True)


if __name__ == '__main__':
    main()
