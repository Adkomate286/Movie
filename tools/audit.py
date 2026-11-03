#!/usr/bin/env python3
"""Integrity and risk guard for this hardened copy of Lemo-Opuscar.

  python3 tools/audit.py            check: exit 0 only if nothing changed since the audit AND no new risky pattern exists
  python3 tools/audit.py --update   after YOU reviewed a change: re-baseline tools/audited.sha256

What it checks
  1. Every file matches tools/audited.sha256 (reports changed, new and missing files).
  2. Risky code patterns appear only in the files that were reviewed (ALLOW below).
  3. package-lock.json: only the two reviewed packages, each with an integrity hash.
  4. requirements*.txt: every requirement is pinned (==) and carries --hash.
  5. tools/assets.json: every pack has a sha256; prints the download source for review.

It uses only the Python standard library and never touches the network.
"""
import fnmatch, hashlib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, 'tools', 'audited.sha256')
SKIP_DIRS = {'.git', 'node_modules', '.venv', 'films', '__pycache__', '.release'}

# --- pattern classes -------------------------------------------------------------------------------------------
PATTERNS = {
    'net-py': (('py',), re.compile(r"urllib\.request|urlopen\(|\brequests\.(get|post|put)|import requests|http\.client|^import socket|\bsocket\.socket|aiohttp|httpx|edge_tts|ftplib|smtplib", re.M)),
    'net-js': (('js', 'mjs', 'cjs', 'html'), re.compile(r"fetch\(\s*[`'\"]https?:|XMLHttpRequest|new WebSocket|sendBeacon|<script[^>]+src=['\"]https?:|<link[^>]+href=['\"]https?:|@import\s+url\(['\"]?https?:|require\(['\"]https?['\"]\)|from ['\"]https?:|import\(['\"]https?:")),
    'net-sh': (('sh',), re.compile(r"\b(curl|wget|nc|ssh|scp|rsync)\s+-|\bgit (clone|fetch|pull|push)\b")),
    'proc': (('py', 'js', 'mjs', 'cjs', 'sh'), re.compile(r"child_process|subprocess\.|os\.system|os\.popen|shell\s*=\s*True|execSync|spawnSync|\bspawn\(")),
    'dyn-exec': (('py', 'js', 'mjs', 'cjs', 'html'), re.compile(r"(?<![\w.])eval\(|(?<![\w.])exec\(|new Function\(|__import__\(")),
    'foreign-data': (('py', 'js', 'mjs', 'cjs', 'html', 'sh'), re.compile(r"\.codex|CODEX_HOME|\.ssh|\.aws|\.gnupg|id_rsa|keychain|API_KEY|DOUBAO")),
    'encoded': (('py', 'js', 'mjs', 'cjs', 'html'), re.compile(r"\batob\(|\bbtoa\(|b64decode|fromCharCode(?:[^;]{0,200}fromCharCode){2}")),
}
# Files reviewed on 2026-11-03 that legitimately contain a class. Glob patterns allowed for the local-ffmpeg class only.
ALLOW = {
    'net-py': {'core/tts/tts_zh.py'},                       # optional Microsoft edge-tts voice (text leaves the machine)
    'net-js': set(),
    'net-sh': {'tools/fetch.sh'},                           # downloads release packs; sha256 from tools/assets.json is enforced
    'proc': {'core/render/*', 'core/tts/*', 'core/audio/*', 'core/post/*', 'styles/*/demo/*', 'tools/fetch.sh'},   # local ffmpeg/ffprobe/node wrappers; fetch.sh runs curl for the sha256-checked download
    'dyn-exec': {                                           # reviewed: arithmetic on a local file, exec of a sibling script, method name .eval(), __import__('PIL...')
        'styles/briefing-board/demo/kit/tools/redraw_stays.py', 'styles/cel-anime-80s/demo/tools/srt.py',
        'styles/kino-montage/demo/audio/mix.py', 'styles/living-screencast/demo/film.js', 'styles/scifi-toon/demo/levels.py'},
    'foreign-data': set(),
    'encoded': set(),
}
VENDORED = {  # byte-identical to the official npm releases (checked 2026-11-03)
    'styles/spy-titles/demo/vendor/opentype.min.js': 'c0f9c7ca85e18075a8819e5fe2dee6e1d535f9a2269f5314f36cce94a183adba',   # opentype.js 1.3.4
    'styles/watercolor/demo/vendor/topojson-client.min.cjs': '25cd02ae486cc5063e0215a4e4cfb15de83700c87ac48bac4d57dc6aaf3ebb89',  # topojson-client 3.1.0
}
LOCK_PACKAGES = {'node_modules/playwright-core', 'node_modules/three'}


def files():
    for root, dirs, fs in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in fs:
            p = os.path.relpath(os.path.join(root, f), ROOT).replace(os.sep, '/')
            if p == 'tools/audited.sha256': continue
            yield p


def sha(p):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, p), 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()


def load_manifest():
    m = {}
    if os.path.exists(MANIFEST):
        for line in open(MANIFEST, encoding='utf-8'):
            if line.strip():
                h, p = line.rstrip('\n').split('  ', 1); m[p] = h
    return m


def allowed(cls, p):
    return any(fnmatch.fnmatch(p, g) for g in ALLOW[cls])


def main():
    cur = {p: sha(p) for p in files()}
    if '--update' in sys.argv:
        with open(MANIFEST, 'w', encoding='utf-8') as f:
            for p in sorted(cur): f.write(f'{cur[p]}  {p}\n')
        print(f'baseline written: {len(cur)} files -> tools/audited.sha256'); return 0

    problems = []
    base = load_manifest()
    if not base: problems.append('tools/audited.sha256 is missing: run with --update once after reviewing the tree')
    changed = sorted(p for p in cur if p in base and cur[p] != base[p])
    new = sorted(p for p in cur if p not in base)
    gone = sorted(p for p in base if p not in cur)
    for label, lst in (('CHANGED since audit', changed), ('NEW since audit', new), ('MISSING since audit', gone)):
        if lst and base: problems.append(f'{label}: {len(lst)} file(s)'); print(f'\n{label}:'); [print('   ', p) for p in lst[:50]]

    for p in sorted(cur):
        ext = p.rsplit('.', 1)[-1].lower() if '.' in p else ''
        if ext not in ('py', 'js', 'mjs', 'cjs', 'html', 'sh') or p in VENDORED or p == 'tools/audit.py': continue   # audit.py holds the patterns itself; its hash is in the manifest
        text = open(os.path.join(ROOT, p), encoding='utf-8', errors='replace').read()
        for cls, (exts, rx) in PATTERNS.items():
            if ext in exts and rx.search(text) and not allowed(cls, p):
                problems.append(f'unreviewed pattern [{cls}] in {p}')
    for p, h in VENDORED.items():
        if p in cur and cur[p] != h: problems.append(f'vendored library differs from the official release: {p}')

    try:
        lock = json.load(open(os.path.join(ROOT, 'package-lock.json')))
        pk = {k for k in lock['packages'] if k}
        if pk != LOCK_PACKAGES: problems.append(f'package-lock.json packages changed: {sorted(pk ^ LOCK_PACKAGES)}')
        for k in pk:
            if not lock['packages'][k].get('integrity'): problems.append(f'package-lock.json: no integrity for {k}')
    except Exception as e:
        problems.append(f'package-lock.json unreadable: {e}')

    for rf in sorted(f for f in cur if re.fullmatch(r'requirements[\w-]*\.txt', f)):
        body = re.sub(r'\\\n', ' ', open(os.path.join(ROOT, rf), encoding='utf-8').read())
        for line in body.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'): continue
            if '==' not in line or '--hash=sha256:' not in line: problems.append(f'{rf}: not pinned with hash: {line[:60]}')

    try:
        man = json.load(open(os.path.join(ROOT, 'tools', 'assets.json')))
        for k, v in man['packs'].items():
            if not re.fullmatch(r'[0-9a-f]{64}', v.get('sha256', '')): problems.append(f'assets.json: no sha256 for {k}')
        print(f"asset source (review!): github.com/{man['repo']}  release tag '{man['tag']}'  ({len(man['packs'])} packs, all sha256-pinned)")
    except Exception as e:
        problems.append(f'tools/assets.json unreadable: {e}')

    print()
    if problems:
        print('AUDIT FAILED:'); [print(' -', x) for x in problems]
        print('\nReview the listed files, then run: python3 tools/audit.py --update'); return 1
    print(f'AUDIT OK: {len(cur)} files identical to the reviewed state; no unreviewed risky patterns.'); return 0


if __name__ == '__main__':
    sys.exit(main())
