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

def changes(e, t):
    return [op for op in difflib.SequenceMatcher(None, e, t, autojunk=False).get_opcodes() if op[0] != 'equal']

def merge(e, t, k, ops=None):
    """apply the change e -> t (or only the given changes of it) to k; None when a
    change's context differs on k"""
    if ops is None:
        if e == k:
            return t
        ops = changes(e, t)
    if not ops:
        return list(k)
    if not e:
        return None
    ek = {}
    for i, j, n in difflib.SequenceMatcher(None, e, k, autojunk=False).get_matching_blocks():
        for x in range(n):
            ek[i + x] = j + x
    res, edits = list(k), []
    for tag, i1, i2, j1, j2 in ops:
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

LABEL = re.compile(r':(\w+)')
REGS = re.compile(r'^\.(registers|locals) ')

def label_refs(line):
    return [] if line.startswith(('const-string', '.field', '.method', '#')) else LABEL.findall(REF.sub('@', line))

def relabel(line, names):
    """rename labels in a line, leaving member references (->name:Type) alone"""
    if not label_refs(line) and not LABEL.fullmatch(line):
        return line
    out, at = [], 0
    for m in REF.finditer(line):
        out.append(LABEL.sub(lambda g: ':' + names.get(g.group(1), g.group(1)), line[at:m.start()]))
        out.append(m.group(0)); at = m.end()
    out.append(LABEL.sub(lambda g: ':' + names.get(g.group(1), g.group(1)), line[at:]))
    return ''.join(out)

def merge_ours(e, t, k, ops, tag):
    """merge_ours: apply the given changes of e -> t to k, with their labels made to fit k.

    baksmali names labels after code offsets, so an inserted block shifts every label
    after it: the part build calls a target :cond_11 that k calls :cond_c. Labels a change
    defines get names of their own; labels it jumps to outside itself are found in k at
    the same instruction (a label is added there when k has none). None when a change's
    context, or a jump target, is not the same on k."""
    if not e:
        return None
    ek, te = {}, {}
    for i, j, n in difflib.SequenceMatcher(None, e, k, autojunk=False).get_matching_blocks():
        for x in range(n):
            ek[i + x] = j + x
    for i, j, n in difflib.SequenceMatcher(None, t, e, autojunk=False).get_matching_blocks():
        for x in range(n):
            te[i + x] = j + x
    edits, made = [], {}
    for no, (_, i1, i2, j1, j2) in enumerate(ops):
        lo, hi = max(0, i1 - CTX), min(len(e), i2 + CTX)
        span = [ek.get(x) for x in range(lo, hi)]
        if not span or None in span or any(b - a != 1 for a, b in zip(span, span[1:])):
            return None
        hunk = t[j1:j2]
        defined = {l[1:] for l in hunk if LABEL.fullmatch(l)}
        names = {d: '%s%d_%s' % (tag, no, d) for d in defined}
        # a line the change rewrites with only its labels renamed tells which label of
        # the base build (and so of k) a shifted name stands for
        was = {}
        for r in e[i1:i2]:
            for n in hunk:
                if r != n and LABEL.sub(':@', REF.sub('@', r)) == LABEL.sub(':@', REF.sub('@', n)):
                    was.update(zip(label_refs(n), label_refs(r)))
        def target(lines, at):
            q = at + 1
            while q < len(lines) and LABEL.fullmatch(lines[q]):
                q += 1
            return q
        for ref in {r for l in hunk for r in label_refs(l)} - defined:
            if ref in made:
                names[ref] = made[ref]; continue
            kq = None
            if ':' + ref in t:
                kq = ek.get(te.get(target(t, t.index(':' + ref)), -1))
            if kq is None and ':' + was.get(ref, '') in e:
                kq = ek.get(target(e, e.index(':' + was[ref])))
            if kq is None:
                return None
            back = kq - 1
            while back >= 0 and LABEL.fullmatch(k[back]):
                back -= 1
            have = k[back + 1:kq]
            if have:
                names[ref] = have[0][1:]
            else:
                names[ref] = '%sx_%s' % (tag, ref)
                edits.append((kq, kq, 1, [':' + names[ref]]))
            made[ref] = names[ref]
        new = [relabel(l, names) for l in hunk]
        if i1 == i2:
            at = ek[i1 - 1] + 1 if i1 > 0 else ek[i1]
            edits.append((at, at, 0, new))
        else:
            edits.append((ek[i1], ek[i2 - 1] + 1, 0, new))
    res = list(k)
    for a, b, _, new in sorted(edits, key=lambda x: (x[0], x[2]), reverse=True):
        res[a:b] = new
    return res

NUM = re.compile(r'-?0x[0-9a-fA-F]+[lLtsS]?|\b-?\d+\b')
OURS = re.compile(r'Lcom/ev6/|[Ll]eafia|EV6CPWL|[Ee]v6')

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

def refs_in(lines):
    return {'%s->%s%s' % r for l in lines for r in REF.findall(l)}

def decls_in(lines, cls):
    out = set()
    for l in lines:
        m = FIELD_DECL.match(l) or METHOD_DECL.match(l)
        if m:
            out.add('%s->%s%s' % (cls, m.group(2), m.group(3)))
    return out

def pick_ours(diffs, new_refs):
    """{class: [changes]}: the changes that mention our code, plus those that declare a
    member our code (or another picked change) uses, until nothing more is needed"""
    picked = {c: [op for op in ops if any(OURS.search(l) for l in t[op[3]:op[4]])] for c, (e, t, cls, ops) in diffs.items()}
    while True:
        want = set(new_refs)
        for c, ops in picked.items():
            t = diffs[c][1]
            for op in ops:
                want |= refs_in(t[op[3]:op[4]])
        grew = False
        for c, (e, t, cls, ops) in diffs.items():
            for op in ops:
                if op not in picked[c] and decls_in(t[op[3]:op[4]], cls) & want:
                    picked[c].append(op); grew = True
        if not grew:
            break
    # a method our code goes into may need more registers: carry its .registers change
    for c, (e, t, cls, ops) in diffs.items():
        starts = set()
        for op in picked[c]:
            j = op[3]
            while j > 0 and not t[j].startswith('.method'):
                j -= 1
            starts.add(j)
        for op in ops:
            if op in picked[c] or not all(REGS.match(l) for l in e[op[1]:op[2]] + t[op[3]:op[4]]):
                continue
            j = op[3]
            while j > 0 and not t[j].startswith('.method'):
                j -= 1
            if j in starts:
                picked[c].append(op)
    return {c: sorted(ops) for c, ops in picked.items()}

def write(out, c, lines):
    os.makedirs(os.path.dirname(os.path.join(out, c)), exist_ok=True)
    open(os.path.join(out, c), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')

def only_ours(a, K, B, P, names, changed, added, ck):
    new = {}
    for c in added:
        lines = norm_lines(os.path.join(P, c))
        new[c] = translate(lines, names, own_class(lines))
    diffs = {}
    for c in changed:
        if c not in ck:
            continue
        cls = own_class(norm_lines(os.path.join(K, c)))
        e = translate(norm_lines(os.path.join(B, c)), names, cls)
        t = translate(norm_lines(os.path.join(P, c)), names, cls)
        diffs[c] = (e, t, cls, changes(e, t))
    picked = pick_ours(diffs, set().union(*[refs_in(l) for l in new.values()]) if new else set())
    done, manual = [], []
    for c in sorted(diffs):
        ops = picked[c]
        if not ops:
            continue
        e, t, cls, _ = diffs[c]
        r = merge_ours(e, t, norm_lines(os.path.join(K, c)), ops, 'lf')
        print('  %s %s: %d of %d changes' % ('carried' if r is not None else 'BY HAND', c[:-6], len(ops), len(diffs[c][3])))
        for op in ops:
            add = t[op[3]:op[4]]
            kind = ' OURS' if any(OURS.search(l) for l in add) else (
                ' (registers)' if all(REGS.match(l) for l in add) else ' (declares what our code uses)')
            print('            -%d +%d%s' % (op[2] - op[1], len(add), kind))
            if a.show_ours:
                for l in e[op[1]:op[2]]:
                    print('              - %s' % l)
                for l in add:
                    print('              + %s' % l)
        if r is None:
            manual.append(c)
        else:
            write(a.out, c, r); done.append(c)
    by_hand = set()
    if a.replace:
        for c in sorted(classes(a.replace)):
            new[c] = open(os.path.join(a.replace, c), encoding='utf-8').read().rstrip('\n').split('\n')
            by_hand.add(c)
    for c in sorted(new):
        write(a.out, c, new[c])
        if c in by_hand:
            print('  ours    %s (written by hand: %s)' % (c[:-6], a.replace)); continue
        opened = sum(1 for l in new[c] if l.startswith('.method'))
        closed = sum(1 for l in new[c] if l == '.end method')
        if opened != closed or not new[c] or new[c][-1] not in ('.end method', '.end field', '.end annotation') and opened:
            manual.append(c)
            print('  BROKEN  %s: cut short in the part build (%d methods, %d complete) - write it by hand' % (c[:-6], opened, closed))
        else:
            print('  new     %s' % c[:-6])
    print('classes carried: %d, by hand: %d, new: %d; every other class is this car\'s stock'
          % (len(done), len(manual), len(new)))
    pairs = []
    def pair(raw_lines, lines):
        for x, y in zip(raw_lines, lines):
            rx, ry = ['%s->%s%s' % r for r in REF.findall(x)], ['%s->%s%s' % r for r in REF.findall(y)]
            if len(rx) == len(ry):
                pairs.extend(zip(rx, ry))
    for c in new:
        pair(norm_lines(os.path.join(P, c)), new[c])
    for c in done:
        raw = norm_lines(os.path.join(P, c))
        for op in picked[c]:
            pair(raw[op[3]:op[4]], diffs[c][1][op[3]:op[4]])
    check_calls(K, P, pairs)
    checks(a, K, manual)

def body(root, ref):
    """skeleton of a method's code (references, numbers and labels blanked), or None"""
    cls, rest = ref.split('->', 1)
    path = os.path.join(root, cls[1:-1] + '.smali')
    if not os.path.exists(path) or '(' not in rest:
        return None
    lines, out, inside = norm_lines(path), [], False
    for l in lines:
        m = METHOD_DECL.match(l)
        if m and m.group(2) + m.group(3) == rest:
            inside = True; continue
        if inside:
            if l == '.end method':
                return out
            out.append(LABEL.sub(':@', NUM.sub('#', REF.sub('@', l))))
    return None

def check_calls(K, P, pairs):
    """our code calls this app's methods by names learnt from a broken build: check that
    the method it meant (in the part build) is the same code as the one it now calls"""
    seen, same, other = set(), 0, []
    for raw, ref in pairs:
        if ref in seen or ref.startswith(('Landroid/', 'Ljava/', 'Lcom/ev6/', 'Ldalvik/', 'Lorg/')) or '(' not in ref:
            continue
        seen.add(ref)
        bk, bp = body(K, ref), body(P, raw)
        if bk is None:
            continue
        if bk == bp:
            same += 1
        else:
            other.append((ref, raw, 'not found in the part build' if bp is None else
                          '%d of %d lines differ' % (sum(1 for x, y in zip(bk, bp) if x != y) + abs(len(bk) - len(bp)), len(bk))))
    print('calls from our code into this app: %d same code as in the part build, %d to check' % (same, len(other)))
    for ref, raw, why in other:
        print('  CHECK %s%s: %s' % (ref, '' if raw == ref else ' (part build: %s)' % raw.split('->', 1)[1], why))

def checks(a, K, manual):
    new_bad = sorted(unresolved(a.out) - unresolved(K))
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

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for x in ('work', 'app', 'set', 'out'):
        ap.add_argument('--' + x, required=True)
    ap.add_argument('--base', default='tbt')
    ap.add_argument('--part', default='bridge')
    ap.add_argument('--fw')
    ap.add_argument('--baksmali')
    ap.add_argument('--detail', action='store_true', help='list each change of each class (names only)')
    ap.add_argument('--only-ours', action='store_true',
                    help='carry only the changes that mention our code (com/ev6, Leafia) and what they need; '
                         'every other class stays this car\'s stock')
    ap.add_argument('--show-ours', action='store_true', help='with --only-ours: print the lines those changes add (our code)')
    ap.add_argument('--replace', help='with --only-ours: folder of our own classes (<path>.smali) written by hand '
                    'for this car; each replaces the class of that name (e.g. tools/cvev_kr)')
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
    if a.only_ours:
        only_ours(a, K, B, P, names, changed, added, ck)
        return
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

    checks(a, K, manual)

if __name__ == '__main__':
    main()
