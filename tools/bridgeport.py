#!/usr/bin/env python3
"""Carry one part's changes (e.g. the CarPlay bridge) onto this car's own stock code.

usage: bridgeport.py --work DIR --app NAME --set SET --base STAGE --part STAGE --out DIR
                     [--fw DIR --baksmali JAR]

  --work   cmpsmali.py's work folder: stock_<App>/ (this car's stock, deodexed) and
           <set>_<App>.<stage>/ (another car's builds, rebuilt from this car's files)
  --app    e.g. HKMC_DiPO     --set  e.g. neev_kr
  --base   the build the part sits on (tbt)      --part  the part to carry (bridge)
  --out    smali tree to write: this car's stock with the part's changes (private)
  --fw     this car's /system/framework: also check that every system call exists
           (deodexes the framework into <work>/fw once; needs --baksmali)

The part's changes are what differs between the base build and the part build of the
same car. Both were rebuilt the same way from this car's files, so whatever is wrong
in them is wrong in both and drops out of the difference. Member names that sit at
another index on this car (obfuscation shifts) are learnt from the classes that differ
from this car's stock only in references, and translated. Then each changed class is
merged into this car's stock class (the change's lines must sit in context that is the
same on this car); new classes are copied. Every reference must resolve.

Prints names and counts only, no code.
"""
import argparse, collections, difflib, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from port import REF, FIELD_DECL, METHOD_DECL, classes, defs_of, norm_lines, own_class, tokens, unresolved  # noqa: E402
from cmpsmali import baksmali, ref_pairs  # noqa: E402

CTX = 2

def learn_names(K, B):
    """{result ref: this car's ref} from classes that differ only in references"""
    seen = collections.defaultdict(collections.Counter)
    for c in classes(K) & classes(B):
        k, b = norm_lines(os.path.join(K, c)), norm_lines(os.path.join(B, c))
        if k == b:
            continue
        p = ref_pairs(k, b, own_class(k))
        for kr, br in p or []:
            seen[br][kr] += 1
    names, clash = {}, 0
    for br, ks in seen.items():
        if len(ks) == 1:
            names[br] = next(iter(ks))
        else:
            clash += 1
    return names, clash

def translate(lines, names, cls):
    def ref(m):
        return names.get('%s->%s%s' % m.groups(), m.group(0))
    out = []
    for l in lines:
        l = REF.sub(ref, l)
        m = FIELD_DECL.match(l) or METHOD_DECL.match(l)
        if m:
            new = names.get('%s->%s%s' % (cls, m.group(2), m.group(3)))
            if new and new.startswith(cls + '->'):
                l = m.group(1) + new.split('->', 1)[1] + l[m.end(3):]
        out.append(l)
    return out

def merge(e, t, k):
    """apply the change e -> t to k; None when a change's context differs on k"""
    if e == k:
        return t
    if not e:
        return None
    ek = {}
    for i, j, n in difflib.SequenceMatcher(None, e, k, autojunk=False).get_matching_blocks():
        for x in range(n):
            ek[i + x] = j + x
    res, edits = list(k), []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, e, t, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        lo, hi = max(0, i1 - CTX), min(len(e), i2 + CTX)
        span = [ek.get(x) for x in range(lo, hi)]
        if not span or None in span or any(b - a != 1 for a, b in zip(span, span[1:])):
            return None
        if i1 == i2:        # pure insertion: after the line before it
            at = ek[i1 - 1] + 1 if i1 > 0 else ek[i1]
            edits.append((at, at, t[j1:j2]))
        else:
            edits.append((ek[i1], ek[i2 - 1] + 1, t[j1:j2]))
    for a, b, new in sorted(edits, reverse=True):
        res[a:b] = new
    return res

NUM = re.compile(r'-?0x[0-9a-fA-F]+[lLtsS]?|\b-?\d+\b')
OURS = re.compile(r'Lcom/ev6/|Leafia|leafia|EV6CPWL|ev6')

def hunks(e, t):
    """one line per change: kind (refs / numbers / code), sizes, names only"""
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, e, t, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        old, new = e[i1:i2], t[j1:j2]
        kind, refs = 'code', []
        if tag == 'replace' and len(old) == len(new):
            if all(REF.sub('@', a) == REF.sub('@', b) for a, b in zip(old, new)):
                kind = 'refs'
                refs = ['%s -> %s' % (x.group(0), y.group(0)) for a, b in zip(old, new)
                        for x, y in zip(REF.finditer(a), REF.finditer(b)) if x.group(0) != y.group(0)]
            elif all(NUM.sub('#', a) == NUM.sub('#', b) for a, b in zip(old, new)):
                kind = 'numbers'
            elif all(NUM.sub('#', REF.sub('@', a)) == NUM.sub('#', REF.sub('@', b)) for a, b in zip(old, new)):
                kind = 'refs+numbers'
                refs = ['%s -> %s' % (x.group(0), y.group(0)) for a, b in zip(old, new)
                        for x, y in zip(REF.finditer(a), REF.finditer(b)) if x.group(0) != y.group(0)]
        if kind == 'code':
            refs = sorted({m.group(0) for l in new for m in REF.finditer(l)} - {m.group(0) for l in old for m in REF.finditer(l)})
        ours = ' OURS' if any(OURS.search(l) for l in new) else ''
        out.append('-%d +%d %s%s%s' % (len(old), len(new), kind, ours, (': ' + '; '.join(refs[:4]) + (' ...' if len(refs) > 4 else '')) if refs else ''))
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for x in ('work', 'app', 'set', 'out'):
        ap.add_argument('--' + x, required=True)
    ap.add_argument('--base', default='tbt')
    ap.add_argument('--part', default='bridge')
    ap.add_argument('--fw')
    ap.add_argument('--baksmali')
    ap.add_argument('--detail', action='store_true', help='list each change of each class (names only)')
    a = ap.parse_args()
    K = os.path.join(a.work, 'stock_' + a.app)
    B = os.path.join(a.work, '%s_%s.%s' % (a.set, a.app, a.base))
    P = os.path.join(a.work, '%s_%s.%s' % (a.set, a.app, a.part))
    for d in (K, B, P):
        if not os.path.isdir(d) or not classes(d):
            sys.exit('missing %s (run cmpsmali.py first)' % d)
    ck, cb, cp = classes(K), classes(B), classes(P)
    if len(cb) < len(ck) or len(cp) < len(cb):
        print('note: some classes of the builds could not be read (%d stock, %d %s, %d %s)'
              % (len(ck), len(cb), a.base, len(cp), a.part))
    names, clash = learn_names(K, B)
    print('names learnt from reference-only classes: %d (%d ambiguous, left alone)' % (len(names), clash))

    added = sorted(cp - cb)
    changed = sorted(c for c in cp & cb if norm_lines(os.path.join(B, c)) != norm_lines(os.path.join(P, c)))
    removed = sorted(cb - cp)
    print('%s changes against %s: %d new classes, %d changed, %d removed'
          % (a.part, a.base, len(added), len(changed), len(removed)))

    if os.path.isdir(a.out):
        shutil.rmtree(a.out)
    shutil.copytree(K, a.out)
    clean, merged, manual, detail = [], [], [], {}
    for c in changed:
        if c not in ck:
            manual.append((c, 'not in this car\'s stock')); continue
        cls = own_class(norm_lines(os.path.join(K, c)))
        e = translate(norm_lines(os.path.join(B, c)), names, cls)
        t = translate(norm_lines(os.path.join(P, c)), names, cls)
        k = norm_lines(os.path.join(K, c))
        detail[c] = hunks(e, t)
        r = merge(e, t, k)
        if r is None:
            n = sum(1 for op in difflib.SequenceMatcher(None, e, t, autojunk=False).get_opcodes() if op[0] != 'equal')
            manual.append((c, '%d change(s), context differs on this car' % n)); continue
        (clean if e == k else merged).append(c)
        open(os.path.join(a.out, c), 'w', encoding='utf-8').write('\n'.join(r) + '\n')
    for c in added:
        lines = norm_lines(os.path.join(P, c))
        r = translate(lines, names, own_class(lines))
        os.makedirs(os.path.dirname(os.path.join(a.out, c)), exist_ok=True)
        open(os.path.join(a.out, c), 'w', encoding='utf-8').write('\n'.join(r) + '\n')
    for c in removed:
        manual.append((c, 'removed by the part'))

    print('changed classes: %d taken whole (stock same as the base build), %d merged, %d need a person'
          % (len(clean), len(merged), len(manual)))
    def more(c):
        if a.detail:
            for h in detail.get(c, []):
                print('            %s' % h)
    for c in clean:
        print('  whole   %s' % c[:-6]); more(c)
    for c in merged:
        print('  merged  %s' % c[:-6]); more(c)
    for c, why in manual:
        print('  BY HAND %s: %s' % (c[:-6], why)); more(c)
    for c in added:
        print('  new     %s' % c[:-6])

    bad = unresolved(a.out)
    base_bad = unresolved(K)
    new_bad = sorted(bad - base_bad)
    print('references inside the app that do not resolve (new ones): %d' % len(new_bad))
    for r in new_bad[:40]:
        print('  %s' % r)
    if a.fw:
        fwdir = os.path.join(a.work, 'fw')
        if not os.path.isdir(fwdir):
            if not a.baksmali:
                sys.exit('--fw needs --baksmali')
            print('deodexing the framework once into %s' % fwdir)
            for f in sorted(os.listdir(a.fw)):
                if f.endswith('.odex'):
                    baksmali(a.baksmali, 'd', '-a', '18', '--allow-odex-opcodes', os.path.join(a.fw, f),
                             '-o', os.path.join(fwdir, f[:-5]))
        fw_bad = sorted(unresolved(a.out, defs_of(fwdir)) - unresolved(K, defs_of(fwdir)))
        print('system calls missing in this framework (new ones): %d' % len(fw_bad))
        for r in fw_bad[:40]:
            print('  %s' % r)
    print('written: %s' % a.out)
    if manual or new_bad:
        sys.exit(1)

if __name__ == '__main__':
    main()
