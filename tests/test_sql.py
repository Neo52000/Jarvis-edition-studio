"""Runs the RLS / editorial-gate SQL suite against a THROW-AWAY empty Postgres.

Set JARVIS_TEST_DATABASE_URL (e.g. postgresql://postgres@127.0.0.1:5432/scratch).
Skipped otherwise. Never point this at a real Supabase project: it creates stub roles.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get('JARVIS_TEST_DATABASE_URL')


@pytest.mark.skipif(not URL or not shutil.which('psql'), reason='JARVIS_TEST_DATABASE_URL / psql absent')
def test_rls_and_gates():
    assert 'supabase.co' not in URL, 'refusing to run stub SQL against a Supabase host'
    run = subprocess.run(['bash', str(ROOT / 'tests/sql/run.sh'), URL], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
