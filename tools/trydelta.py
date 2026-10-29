#!/usr/bin/env python3
"""Try every patch set's deltas on a new car's stock files, ignoring the source check.

usage: trydelta.py <stock dir> [--out DIR] [--explain]

  <stock dir>  the new car's stock files: app/<App>.odex, lib/libautoreceiver_infobank.so
               (a kit's LEAFIA/private/stock/ works as is)
  --out DIR    also write each result that reproduced its target (keep it private)
  --explain    for a dex result that missed: how far its body is from the target (the
               target's own adler32 sits in its header), and a search over the bytes in
               which two sets' deltas for the same target disagree

A .lpd holds the md5 of the exact source and of the target. `lpatch delta` refuses any
other source; this tool applies each delta to the new car's file anyway and reports
whether the result is still byte for byte the delta's target. When it is, the new car's
file carries every byte the delta copies from the stock original, and the result is the
same build another car already runs. Nothing is written into the repository and no
stock file is changed. Needs: pip install --require-hashes -r tools/requirements.txt
"""
import argparse, hashlib, itertools, os, struct, sys, zlib

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

MOD = 65521

def parse(d):
    """ctrl, diff, extra of an LPD1 delta (the format mkdelta.py writes)."""
    comp, plen = struct.unpack('<II', d[44:52])
    body = zlib.decompress(d[52:52 + plen], -15) if comp == 1 else d[52:52 + plen]
    n, = struct.unpack('<I', body[:4]); p = 4
    ctrl = [struct.unpack('<iii', body[p + 12*i:p + 12*i + 12]) for i in range(n)]; p += 12 * n
    dl, = struct.unpack('<I', body[p:p+4]); diff = body[p+4:p+4+dl]; p += 4 + dl
    el, = struct.unpack('<I', body[p:p+4])
    return ctrl, diff, body[p+4:p+4+el]

def diff_out_pos(ctrl):
    """output position of each diff byte"""
    pos, o = [], 0
    for x, y, z in ctrl:
        pos.extend(range(o, o + x)); o += x + y
    return pos

def adler_gap(out):
    """(A, B) the body is off from the adler32 its dex header carries; (0, 0) = they agree"""
    want, = struct.unpack('<I', out[8:12]); got = zlib.adler32(out[12:])
    return ((want & 0xffff) - (got & 0xffff)) % MOD, ((want >> 16) - (got >> 16)) % MOD

def signed(v): return v - MOD if v > MOD // 2 else v

def explain(name, sb, data, tmd5, others):
    out = apply(sb, data)
    if out[:4] != b'dex\n':
        print('  %s: not a dex result, nothing to explain' % name); return None
    a, b = adler_gap(out)
    print('  %s: adler32 gap A=%+d B=%+d (A = sum of byte errors when each is small)' % (name, signed(a), signed(b)))
    ctrl, diff, extra = parse(data); pos = None
    for oname, od in others:
        c2, d2, e2 = parse(od)
        if c2 != ctrl or e2 != extra or len(d2) != len(diff):
            continue
        pos = pos or diff_out_pos(ctrl)
        alt = [(pos[i], (d2[i] - diff[i]) & 255) for i in range(len(diff)) if d2[i] != diff[i]]
        print('    vs %s (same target, same layout): %d bytes differ' % (oname, len(alt)))
        if not alt or len(alt) > 16:
            continue
        for pick in itertools.product((0, 1), repeat=len(alt)):
            o = bytearray(out)
            for (i, dv), on in zip(alt, pick):
                if on: o[i] = (o[i] + dv) & 255
            if hashlib.md5(o).hexdigest() == tmd5:
                print('    REPRODUCED by taking the bytes of %s at %s' % (oname, [i for (i, _), on in zip(alt, pick) if on]))
                return bytes(o)
        print('    no mix of the two reproduces the target')
    return None

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stock')
    ap.add_argument('--out')
    ap.add_argument('--patches', default=PATCHES)
    ap.add_argument('--explain', action='store_true')
    a = ap.parse_args()
    rows, hits, missed = [], {}, []
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
            if not ok:
                missed.append((s + '/' + f, sb, data, tmd5))
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
    if a.explain:
        print()
        print('explain:')
        for name, sb, data, tmd5 in missed:
            others = [(n2, d2) for n2, _, d2, t2 in missed if t2 == tmd5 and n2 != name]
            fixed = explain(name, sb, data, tmd5, others)
            if fixed and a.out:
                s, f = name.split('/')
                os.makedirs(os.path.join(a.out, s), exist_ok=True)
                open(os.path.join(a.out, s, f[:-4] + '.out'), 'wb').write(fixed)

if __name__ == '__main__':
    main()
