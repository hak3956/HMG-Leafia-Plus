#!/usr/bin/env python3
"""Try every patch set's deltas on a new car's stock files, ignoring the source check.

usage: trydelta.py <stock dir> [--out DIR]

  <stock dir>  the new car's stock files: app/<App>.odex, lib/libautoreceiver_infobank.so
               (a kit's LEAFIA/private/stock/ works as is)
  --out DIR    also write each result that reproduced its target (keep it private)

A .lpd holds the md5 of the exact source and of the target. `lpatch delta` refuses any
other source; this tool applies each delta to the new car's file anyway and reports
whether the result is still byte for byte the delta's target. When it is, the new car's
file carries every byte the delta copies from the stock original, and the result is the
same build another car already runs. Nothing is written into the repository and no
stock file is changed. Needs: pip install --require-hashes -r tools/requirements.txt
"""
import argparse, hashlib, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mkdelta import apply  # noqa: E402

PATCHES = os.path.join(os.path.dirname(HERE), 'patches')
LIB = 'libautoreceiver_infobank.so'

def source_of(stock, lpd):
    name = os.path.basename(lpd).split('.')[0]
    if name + '.so' == LIB:
        return os.path.join(stock, 'lib', LIB)
    return os.path.join(stock, 'app', name + '.odex')

def header(d):
    if d[:4] != b'LPD1':
        return None
    slen, = struct.unpack('<I', d[4:8]); tlen, = struct.unpack('<I', d[24:28])
    return slen, d[8:24].hex(), tlen, d[28:44].hex()

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stock')
    ap.add_argument('--out')
    ap.add_argument('--patches', default=PATCHES)
    a = ap.parse_args()
    rows, hits = [], {}
    for s in sorted(os.listdir(a.patches)):
        d = os.path.join(a.patches, s)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.lpd'):
                continue
            lpd = os.path.join(d, f); src = source_of(a.stock, lpd)
            if not os.path.exists(src):
                continue
            data = open(lpd, 'rb').read(); h = header(data)
            if not h:
                rows.append((s + '/' + f, 'not an LPD1 file')); continue
            slen, smd5, tlen, tmd5 = h
            sb = open(src, 'rb').read()
            if hashlib.md5(sb).hexdigest() == smd5:
                how = 'source is the exact stock file (lpatch accepts it as is)'
            else:
                how = 'source differs (%d bytes, delta made from %d)' % (len(sb), slen)
            try:
                out = apply(sb, data)
            except Exception as e:  # a corrupt or foreign delta must not stop the run
                rows.append((s + '/' + f, 'FAILED to apply: %s; %s' % (e, how))); continue
            ok = len(out) == tlen and hashlib.md5(out).hexdigest() == tmd5
            rows.append((s + '/' + f, ('REPRODUCED target %s' % tmd5 if ok else 'different result') + '; ' + how))
            if ok:
                hits.setdefault(f.rsplit('.', 1)[0] if s == 'common' else '.'.join(f.split('.')[:2]), []).append(s)
                if a.out:
                    os.makedirs(os.path.join(a.out, s), exist_ok=True)
                    open(os.path.join(a.out, s, f[:-4] + '.out'), 'wb').write(out)
    if not rows:
        sys.exit('no deltas apply to anything in %s (expected app/<App>.odex, lib/%s)' % (a.stock, LIB))
    w = max(len(r[0]) for r in rows)
    for name, res in rows:
        print('%-*s  %s' % (w, name, res))
    print()
    print('reproduced: ' + (', '.join('%s (%s)' % (k, ' '.join(v)) for k, v in sorted(hits.items())) or 'none'))

if __name__ == '__main__':
    main()
