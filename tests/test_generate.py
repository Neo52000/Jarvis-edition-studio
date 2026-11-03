import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('claude_generate', ROOT / 'scripts' / 'claude_generate.py')
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
SAMPLE = ROOT / 'examples' / 'sample_book.json'


def test_command_is_sandboxed_and_prompt_not_in_argv():
    cmd = gen.build_command(0.5)
    assert cmd[:2] == ['claude', '-p']
    assert cmd[cmd.index('--tools') + 1] == ''            # all tools disabled
    assert 'mcp__*' in cmd and '--no-session-persistence' in cmd
    assert cmd[cmd.index('--max-budget-usd') + 1] == '0.5'
    assert not any('Tu es un assistant' in c for c in cmd)


def test_prompt_forbids_invention_and_publication():
    snap = json.loads(SAMPLE.read_text())
    p = gen.build_prompt(snap['book'], snap['chapters'][0], 'draft')
    assert 'SOURCE À VÉRIFIER' in p and 'aucune publication' in p and 'TEXTE À RELIRE' in p
    assert 'JAMAIS à une validation automatique' in gen.TASKS['audit']


def test_dry_run_never_calls_claude():
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'claude_generate.py'), str(SAMPLE),
                        '--chapter', '1', '--dry-run'], capture_output=True, text=True)
    assert r.returncode == 0 and 'claude -p' in r.stdout


def test_output_is_bannered_with_fake_cli(tmp_path):
    fake = tmp_path / 'bin'; fake.mkdir()
    (fake / 'claude').write_text('#!/bin/sh\ncat >/dev/null\necho "# Chapitre proposé"\n')
    (fake / 'claude').chmod(0o755)
    env = {'PATH': f'{fake}:/usr/bin:/bin'}
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'claude_generate.py'), str(SAMPLE),
                        '--chapter', '1', '--out', str(tmp_path / 'd')], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    out = (tmp_path / 'd' / 'chapitre-01-draft.md').read_text()
    assert out.startswith('<!-- PROPOSITION IA NON VÉRIFIÉE') and '# Chapitre proposé' in out


def test_unknown_chapter_rejected():
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'claude_generate.py'), str(SAMPLE),
                        '--chapter', '99', '--dry-run'], capture_output=True, text=True)
    assert r.returncode == 2
