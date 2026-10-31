#!/usr/bin/env python3
"""Find your way around a deodexed app's smali without printing its code.

usage: smalinav.py DIR who REGEX          every line matching REGEX, with its class and method
       smalinav.py DIR calls CLASS METHOD  the outline of one method (see below)
       smalinav.py DIR field CLASS NAME    the methods that read or write one field

  DIR     smali tree (baksmali output; Windows line ends are fine)
  CLASS   like e/b or com/daudio/app/dipo/e/b (a short name is looked up under DIR)
  METHOD  the method's name, optionally with its signature start: a  or  a(Lcom/x;Z)

The outline keeps labels, branches, switches, field reads/writes, constants and calls,
and leaves out logging and string building, so it shows how a method decides, not its
text. Meant for private stock trees: keep the output out of the repository.
"""
import os, re, sys

SKIP = re.compile(r'Landroid/util/Log;|Ljava/lang/StringBuilder;|Lcom/daudio/app/dipo/a/a;->[a-z]\(Ljava/lang/String;Ljava/lang/String;\)V|^\s*(move-result|\.line|\.prologue|\.local|\.end local|\.param|\.end param)')
KEEP = re.compile(r'^\s*(:|invoke|if-|goto|return|throw|[ais]get|[ais]put|const|packed-switch|sparse-switch|new-instance|instance-of|check-cast|\.catch)')

def lines(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return [l.rstrip('\r\n') for l in f]

def smali_files(d):
    for root, _, files in os.walk(d):
        for f in files:
            if f.endswith('.smali'):
                yield os.path.join(root, f)

def find_class(d, c):
    c = c.strip('L;').replace('.', '/')
    for cand in (os.path.join(d, c + '.smali'),):
        if os.path.exists(cand):
            return cand
    hits = [p for p in smali_files(d) if p.endswith('/' + c + '.smali')]
    if len(hits) != 1:
        sys.exit('class %s: %s' % (c, 'not found' if not hits else '%d matches, give more of the name' % len(hits)))
    return hits[0]

def methods(path):
    """[(method line, [body lines])]"""
    out, cur = [], None
    for l in lines(path):
        if l.startswith('.method'):
            cur = (l, [])
        elif l.startswith('.end method') and cur:
            out.append(cur); cur = None
        elif cur:
            cur[1].append(l)
    return out

def who(d, rx):
    r = re.compile(rx)
    for p in sorted(smali_files(d)):
        m = '(class)'
        for l in lines(p):
            if l.startswith('.method'):
                m = l.split()[-1]
            if r.search(l):
                print('%s :: %s :: %s' % (os.path.relpath(p, d)[:-6], m, l.strip()))

def calls(d, c, name):
    p = find_class(d, c)
    found = False
    for head, body in methods(p):
        sig = head.split()[-1]
        if sig == name or sig.startswith(name + '(') or ('(' in name and sig.startswith(name)):
            found = True
            print(head)
            for l in body:
                if KEEP.search(l) and not SKIP.search(l):
                    print('    ' + l.strip())
            print('.end method\n')
    if not found:
        sys.exit('no method %s in %s' % (name, c))

def field(d, c, name):
    full = find_class(d, c)
    cls = 'L' + os.path.relpath(full, d)[:-6] + ';'
    who(d, re.escape('%s->%s:' % (cls, name)))

def main():
    a = sys.argv[1:]
    if len(a) < 3 or a[1] not in ('who', 'calls', 'field') or (a[1] != 'who' and len(a) < 4):
        sys.exit(__doc__)
    d = a[0]
    if a[1] == 'who':
        who(d, a[2])
    elif a[1] == 'calls':
        calls(d, a[2], a[3])
    else:
        field(d, a[2], a[3])

if __name__ == '__main__':
    main()
