#!/usr/bin/env python3
"""Compare another car's build, rebuilt from this car's files, with this car's own code.

usage: cmpsmali.py --stock DIR --fw DIR --missed DIR --work DIR [--baksmali JAR]

  --stock   this car's stock files (app/<App>.odex)
  --fw      this car's /system/framework
  --missed  trydelta.py --out folder: <set>/<App>.<stage>.miss.dex
  --work    where the smali goes (stock code: keep it private, outside the repository)
  --baksmali  baksmali 2.5.2 jar (default ~/.local/share/smali/baksmali-2.5.2.jar, or BAKSMALI)

trydelta.py rebuilds another car's build from this car's odex; when the md5 misses, the
result is that build with every byte that differs between the two cars' odex files
carried over wrongly. This lists, class by class, how the result differs from this
car's own code (deodexed against its own framework):

  same       identical: the class is the same on both cars and we never changed it
  refs only  only member references differ, the rest of every line is the same: the
             two cars' frameworks put a method or field at another index (dexopt
             quickening), not a code difference
  code       anything else: our change to the class, or a real code difference

Only names and counts are printed, no code. Needs java.
"""
import argparse, collections, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from port import BCP, REF, classes, norm_lines, own_class, tokens  # noqa: E402

SMALI_DIR = os.path.expanduser('~/.local/share/smali')

def baksmali(jar, *args):
    r = subprocess.run(['java', '-jar', jar] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return r.returncode, r.stderr

def deodex(jar, odex, fw, out):
    have = set(os.listdir(fw))
    bcp = [b + '.odex' for b in BCP if b + '.odex' in have]
    extra = sorted(f for f in have if f.endswith('.odex') and f not in bcp)
    rc, err = baksmali(jar, 'x', '-a', '18', '-d', fw, '-b', ':'.join(bcp + extra), '-o', out, odex)
    skipped = err.count('skipping class')
    if rc or skipped:
        sys.exit('deodex of %s failed (exit %d, %d classes skipped):\n%s' % (odex, rc, skipped, err[-2000:]))

def disasm(jar, dex, out):
    rc, err = baksmali(jar, 'd', '-o', out, dex)
    if rc:
        print('    baksmali could not read %s (exit %d): %s' % (os.path.basename(dex), rc, err.strip()[-500:]))
        return False
    return True

def skeleton(line):
    """the line with every member reference blanked (class, name and signature: a wrong
    index points at another member, often of another class)"""
    return REF.sub('@', line)

def ref_pairs(k, o, cls):
    """[(stock ref, result ref)] when k and o differ only in member references, else None"""
    if len(k) != len(o):
        return None
    pairs = []
    for a, b in zip(k, o):
        if a == b:
            continue
        if skeleton(a) != skeleton(b):
            return None
        ta, tb = tokens(a, cls), tokens(b, cls)
        if len(ta) != len(tb):
            return None
        pairs += [('%s->%s%s' % x, '%s->%s%s' % y) for x, y in zip(ta, tb) if x != y]
    return pairs

def compare(K, O, top):
    ck, co = classes(K), classes(O)
    same, refs, code = 0, collections.Counter(), []
    lines = 0
    for c in sorted(ck & co):
        k, o = norm_lines(os.path.join(K, c)), norm_lines(os.path.join(O, c))
        if k == o:
            same += 1; continue
        p = ref_pairs(k, o, own_class(k))
        if p is None:
            code.append((c, sum(1 for a, b in zip(k, o) if a != b) + abs(len(k) - len(o))))
        else:
            refs.update(p); lines += 1
    print('    classes: %d in this car, %d in the result; same %d, refs only %d, code %d, only in this car %d, only in the result %d'
          % (len(ck), len(co), same, lines, len(code), len(ck - co), len(co - ck)))
    if refs:
        print('    references that differ (this car -> result, count):')
        for (a, b), n in refs.most_common(top):
            print('      %4d  %s  ->  %s' % (n, a, b))
        if len(refs) > top:
            print('      ... %d more' % (len(refs) - top))
    if code:
        print('    classes with code differences (lines differing, roughly):')
        for c, n in sorted(code, key=lambda x: -x[1])[:top]:
            print('      %5d  %s' % (n, c[:-6]))
        if len(code) > top:
            print('      ... %d more' % (len(code) - top))
    for c in sorted(co - ck)[:top]:
        print('      only in the result: %s' % c[:-6])

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for x in ('stock', 'fw', 'missed', 'work'):
        ap.add_argument('--' + x, required=True)
    ap.add_argument('--baksmali', default=os.environ.get('BAKSMALI', os.path.join(SMALI_DIR, 'baksmali-2.5.2.jar')))
    ap.add_argument('--top', type=int, default=25)
    a = ap.parse_args()
    if not os.path.isdir(a.missed):
        sys.exit('no folder %s (run trydelta.py with --out first)' % a.missed)
    os.makedirs(a.work, exist_ok=True)
    found = False
    for s in sorted(os.listdir(a.missed)):
        d = os.path.join(a.missed, s)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.miss.dex'):
                continue
            app = f.split('.')[0]
            odex = os.path.join(a.stock, 'app', app + '.odex')
            if not os.path.exists(odex):
                continue
            found = True
            K = os.path.join(a.work, 'stock_' + app)
            if not os.path.isdir(K):
                print('deodexing %s against this car\'s framework' % app)
                deodex(a.baksmali, odex, a.fw, K)
            O = os.path.join(a.work, '%s_%s' % (s, f[:-len('.miss.dex')]))
            print('%s/%s' % (s, f[:-len('.miss.dex')]))
            if not os.path.isdir(O) and not disasm(a.baksmali, os.path.join(d, f), O):
                continue
            compare(K, O, a.top)
    if not found:
        sys.exit('no <set>/<App>.<stage>.miss.dex in %s (run trydelta.py with --out first)' % a.missed)

if __name__ == '__main__':
    main()
