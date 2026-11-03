"""Repository hygiene: no secrets, no local config tracked, vendored bundle intact."""
import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SECRET_PATTERNS = {
    'jwt': re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'),
    'github_token': re.compile(r'\b(ghp_|gho_|ghs_|github_pat_)[A-Za-z0-9_]{20,}'),
    'anthropic_key': re.compile(r'sk-ant-[A-Za-z0-9_-]{20,}'),
    'supabase_secret': re.compile(r'sb_secret_[A-Za-z0-9_-]{8,}'),
    'private_key': re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
}


def tracked_files():
    out = subprocess.run(['git', 'ls-files', '-co', '--exclude-standard'], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.split('\n')
    return [ROOT / f for f in out if f and (ROOT / f).is_file()]


def test_no_secret_patterns_in_repo():
    hits = []
    for f in tracked_files():
        if 'web/vendor/' in f.as_posix() or f.suffix in {'.docx', '.pdf'}:
            continue
        text = f.read_text(encoding='utf-8', errors='ignore')
        hits += [f'{f.relative_to(ROOT)}: {name}' for name, rx in SECRET_PATTERNS.items() if rx.search(text)]
    assert not hits, hits


def test_browser_code_never_references_privileged_keys():
    for f in (ROOT / 'web').glob('*.*'):
        if f.suffix in {'.js', '.html'}:
            t = f.read_text(encoding='utf-8')
            assert 'service_role' not in t and 'sb_secret_' not in t, f


def test_local_config_is_ignored_and_untracked():
    names = [f.relative_to(ROOT).as_posix() for f in tracked_files()]
    assert 'web/config.js' not in names and not any(n.startswith('.env') and n != '.env.example' for n in names)
    ignored = subprocess.run(['git', 'check-ignore', 'web/config.js'], cwd=ROOT, capture_output=True, text=True)
    assert ignored.returncode == 0


def test_vendored_supabase_bundle_matches_recorded_hash():
    d = ROOT / 'web' / 'vendor'
    recorded = (d / 'supabase.js.sha256').read_text().split()[0]
    assert hashlib.sha256((d / 'supabase.js').read_bytes()).hexdigest() == recorded


def test_csp_present_and_no_remote_scripts():
    html = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
    assert 'Content-Security-Policy' in html and "script-src 'self'" in html
    assert not re.search(r'<script[^>]+src="https?://', html)
    assert 'esm.sh' not in (ROOT / 'web' / 'app.js').read_text(encoding='utf-8')
