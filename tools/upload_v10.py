#!/usr/bin/env python3
"""Build V10 and upload it as a single Python AI to 10.0/V10/v10.py.

    python3 tools/upload_v10.py            # build + upload + server syntax check
It never assigns the AI to a leek (use /leek/set-ai with ai_path for that).
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

PATH = '10.0/V10/v10.py'


def main():
    subprocess.run([sys.executable, os.path.join(HERE, 'v10_build.py')], check=True)
    code = open(os.path.join(ROOT, 'V10', 'v10.py')).read()
    lw = LWSession(sys.argv[1] if len(sys.argv) > 1 else 'main')
    r = lw.s.post('https://leekwars.com/api/ai/write', data={'path': PATH, 'code': code}).json()
    res = (r.get('result') or {}).get(PATH)
    if not res:
        sys.exit('upload failed: %s' % str(r)[:300])
    print('uploaded %s: %s lines, problems: %s' % (PATH, res.get('total_lines'), res.get('problems') or 'none'))


if __name__ == '__main__':
    main()
