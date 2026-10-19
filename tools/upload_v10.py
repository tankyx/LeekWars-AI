#!/usr/bin/env python3
"""Build V10 and upload it as a single Python AI to 10.0/V10/v10.py.

    python3 tools/upload_v10.py            # build + upload + server syntax check
    python3 tools/upload_v10.py --minify   # comments/docstrings stripped first (the AI storage quota is full;
                                           # behaviour identical, v10_equiv 12/12 on 2026-10-19)
It never assigns the AI to a leek (use /leek/set-ai with ai_path for that).
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lw_api import LWSession

PATH = '10.0/V10/v10.py'


def minify(src):
    """Drop comments, docstrings (kept as a no-op `pass`) and blank lines; compile-checked."""
    import io, tokenize
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline)); res = []
    for i, t in enumerate(toks):
        if t.type == tokenize.COMMENT:
            continue
        if t.type == tokenize.STRING:
            j = i - 1
            while j >= 0 and toks[j].type in (tokenize.NL, tokenize.COMMENT):
                j -= 1
            if j < 0 or toks[j].type in (tokenize.INDENT, tokenize.NEWLINE, tokenize.DEDENT):
                k = i + 1
                while k < len(toks) and toks[k].type in (tokenize.NL, tokenize.COMMENT):
                    k += 1
                if k < len(toks) and toks[k].type in (tokenize.NEWLINE, tokenize.ENDMARKER):
                    res.append(t._replace(string='pass'))
                    continue
        res.append(t)
    out = '\n'.join(l.rstrip() for l in tokenize.untokenize(res).splitlines() if l.strip()) + '\n'
    compile(out, 'v10_min.py', 'exec')
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    subprocess.run([sys.executable, os.path.join(HERE, 'v10_build.py')], check=True)
    code = open(os.path.join(ROOT, 'V10', 'v10.py')).read()
    if '--minify' in sys.argv:
        n0 = len(code); code = minify(code)
        print('minified %d -> %d bytes' % (n0, len(code)))
    lw = LWSession(args[0] if args else 'main')
    r = lw.s.post('https://leekwars.com/api/ai/write', data={'path': PATH, 'code': code}).json()
    res = (r.get('result') or {}).get(PATH)
    if not res:
        sys.exit('upload failed: %s' % str(r)[:300])
    print('uploaded %s: %s lines, problems: %s' % (PATH, res.get('total_lines'), res.get('problems') or 'none'))


if __name__ == '__main__':
    main()
