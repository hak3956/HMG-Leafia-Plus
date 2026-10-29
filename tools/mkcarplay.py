#!/usr/bin/env python3
"""Make a CarPlay-only patch set (bridge build, no turn-by-turn) for one car.

usage: mkcarplay.py --variant NAME --prefix PRODUCT_PREFIX --name "Car name"
                    --stock DIR --dipo-smali DIR --iap2-dex FILE --builds DIR
                    [--smali JAR] [--baksmali JAR] [--patches DIR]

  --stock       the car's stock files: app/HKMC_DiPO.{apk,odex}, app/Iap2ServerApp.{apk,odex}
  --dipo-smali  the car's stock DiPO with the bridge carried over (bridgeport.py --only-ours)
  --iap2-dex    the Iap2Server bridge dex (trydelta.py --out: <set>/Iap2ServerApp.bridge.out)
  --builds      where the full builds go (3_bridge/files_<variant>/: keep them private)
  --smali/--baksmali  smali/baksmali 2.5.2 jars (default ~/.local/share/smali/, or SMALI/BAKSMALI)

Assembles the DiPO dex (smali --api 18 -j 1: the same dex every run), reads it back and
checks it holds exactly the smali it was made from, adds both dex files to the car's
stock APKs with the host lpatch, then writes patches/<variant>/ (deltas, stock, manifest:
tools/mkpatches.py --carplay-only) and the car's line in patches/cars. The package then
installs that car in CarPlay mode. Needs java, the host lpatch (tools/lpatch/build.sh) and
pip install --require-hashes -r tools/requirements.txt.
"""
import argparse, hashlib, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from port import classes, norm_lines  # noqa: E402

ROOT = os.path.dirname(HERE)
LPATCH = os.path.join(HERE, 'lpatch', 'lpatch-host')
SMALI_DIR = os.path.expanduser('~/.local/share/smali')
JAVA = os.environ.get('JAVA', 'java')

def md5(p): return hashlib.md5(open(p, 'rb').read()).hexdigest()

def run(*a):
    r = subprocess.run(a, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        sys.exit('failed: %s\n%s' % (' '.join(a[:4]), (r.stderr or r.stdout)[-2000:]))
    return r

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for x in ('variant', 'prefix', 'name', 'stock', 'dipo-smali', 'iap2-dex', 'builds'):
        ap.add_argument('--' + x, required=True)
    ap.add_argument('--smali', default=os.environ.get('SMALI', os.path.join(SMALI_DIR, 'smali-2.5.2.jar')))
    ap.add_argument('--baksmali', default=os.environ.get('BAKSMALI', os.path.join(SMALI_DIR, 'baksmali-2.5.2.jar')))
    ap.add_argument('--patches', default=os.path.join(ROOT, 'patches'))
    a = ap.parse_args()
    for f in (a.smali, a.baksmali, LPATCH):
        if not os.path.exists(f):
            sys.exit('missing %s' % f)
    for n in ('HKMC_DiPO', 'Iap2ServerApp'):
        for e in ('apk', 'odex'):
            if not os.path.exists(os.path.join(a.stock, 'app', '%s.%s' % (n, e))):
                sys.exit('missing %s/app/%s.%s' % (a.stock, n, e))
    if open(a.iap2_dex, 'rb').read(4) != b'dex\n':
        sys.exit('%s is not a dex file' % a.iap2_dex)

    out = os.path.join(a.builds, '3_bridge', 'files_' + a.variant)
    os.makedirs(out, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        dex = os.path.join(t, 'dipo.dex')
        n = len(classes(a.dipo_smali))
        if not n:
            sys.exit('no .smali files under %s' % a.dipo_smali)
        r = run(JAVA, '-jar', a.smali, 'a', '--api', '18', '-j', '1', '-o', dex, a.dipo_smali)
        if not os.path.exists(dex):
            sys.exit('smali wrote no dex from %d .smali files:\n%s' % (n, (r.stdout + r.stderr)[-3000:]))
        back = os.path.join(t, 'back')
        run(JAVA, '-jar', a.baksmali, 'd', '-o', back, dex)
        src, got = classes(a.dipo_smali), classes(back)
        bad = sorted(c for c in src & got if norm_lines(os.path.join(a.dipo_smali, c)) != norm_lines(os.path.join(back, c)))
        if src != got or bad:
            sys.exit('the DiPO dex does not read back as its smali: %d classes missing, %d extra, %d differ (%s)'
                     % (len(src - got), len(got - src), len(bad), ', '.join(bad[:5])))
        print('HKMC_DiPO: assembled %d classes, reads back the same; dex md5 %s' % (len(src), md5(dex)))
        for n, d in (('HKMC_DiPO', dex), ('Iap2ServerApp', a.iap2_dex)):
            run(LPATCH, 'zipadd', os.path.join(a.stock, 'app', n + '.apk'), d, os.path.join(out, n + '.apk'))
            print('%s.apk: stock APK + bridge dex, md5 %s' % (n, md5(os.path.join(out, n + '.apk'))))

    r = run(sys.executable, os.path.join(HERE, 'mkpatches.py'), a.variant, a.stock, a.builds, a.patches, '--carplay-only')
    with open(os.path.join(a.patches, a.variant, 'stock'), 'w') as f:
        for n in ('HKMC_DiPO', 'Iap2ServerApp'):
            for e in ('apk', 'odex'):
                f.write('%s.%s %s\n' % (n, e, md5(os.path.join(a.stock, 'app', '%s.%s' % (n, e)))))
    cars = os.path.join(a.patches, 'cars')
    lines = [l for l in (open(cars).read().splitlines() if os.path.exists(cars) else []) if l.split()[1:2] != [a.variant]]
    # the installer takes the first matching prefix, so go above any shorter one that also matches
    at = next((i for i, l in enumerate(lines) if l and not l.startswith('#') and a.prefix.startswith(l.split()[0])), len(lines))
    lines.insert(at, '%s %s %s' % (a.prefix, a.variant, a.name))
    open(cars, 'w').write('\n'.join(lines) + '\n')
    print(r.stdout.strip())
    print('OK: patches/%s written (CarPlay mode) and %s added to patches/cars' % (a.variant, a.name))

if __name__ == '__main__':
    main()
