#!/usr/bin/env python3
"""Local Claude Code production step: proposal only, never writes to Supabase.

Requires the official Claude Code CLI installed and authenticated by the owner.
Usage: python scripts/claude_generate.py examples/sample_book.json --chapter 1 --task draft
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

TASKS={
    'draft': '''Rédige une proposition complète de chapitre en français pour le livre décrit.
Structure claire, style naturel, exemples adaptés au public, sans remplissage.
Indique [SOURCE À VÉRIFIER] pour toute affirmation factuelle non vérifiée.
N'invente jamais citations, études, noms d'auteurs ou liens.
Réponds uniquement avec le contenu Markdown du chapitre.''',
    'audit': '''Audite rigoureusement le chapitre. Donne les ambiguïtés, redondances,
erreurs plausibles, points nécessitant une validation juridique ou éditoriale,
et une liste de vérifications à effectuer. Ne conclus JAMAIS à une validation automatique.
Réponds en français, avec constat et recommandation par point.''',
    'factcheck': '''Établis un PLAN DE VÉRIFICATION des affirmations du chapitre.
Tu n'as accès à aucune source externe dans cette exécution: ne prétends donc pas
avoir vérifié en ligne. Reprends les assertions à contrôler et propose les sources
primaires qui conviendraient. Signale explicitement les inconnues.'''
}

def build_prompt(book: dict, chapter: dict, task: str) -> str:
    return f'''Tu es un assistant éditorial français.
Livre: {book.get('title','')}
Sous-titre: {book.get('subtitle','')}
Public cible: {book.get('target_audience','')}
Positionnement: {book.get('positioning','')}
Chapitre {chapter['position']}: {chapter['title']}
Contenu existant:\n{chapter.get('content','')}\n\nMISSION:\n{TASKS[task]}
RÈGLES: aucune publication, aucune manipulation de bases de données, aucun
engagement commercial, aucune référence inventée. Tu produis un TEXTE À RELIRE.'''


def build_command(max_budget: float) -> list:
    """Prompt is sent on stdin (not argv): no size limit, not visible in `ps`.
    No tools, no MCP, no slash commands/skills, no session saved on disk."""
    return ['claude', '-p', '--output-format', 'text', '--tools', '',
            '--disallowedTools', 'mcp__*', '--disable-slash-commands',
            '--no-session-persistence', '--max-budget-usd', str(max_budget)]


def main():
    ap=argparse.ArgumentParser(description='Production locale de brouillons avec Claude Code')
    ap.add_argument('snapshot',type=Path)
    ap.add_argument('--chapter',type=int,required=True)
    ap.add_argument('--task',choices=TASKS,default='draft')
    ap.add_argument('--max-budget-usd',type=float,default=0.75,
                    help='Plafond indicatif CLI, NON une garantie de facturation')
    ap.add_argument('--out',type=Path,default=Path('drafts'))
    ap.add_argument('--dry-run',action='store_true',help='Affiche la commande et le prompt sans appeler Claude')
    args=ap.parse_args()
    if args.max_budget_usd<=0:
        ap.error('Budget strictement positif requis.')
    snapshot=json.loads(args.snapshot.read_text(encoding='utf-8'))
    chapter=next((x for x in snapshot.get('chapters',[]) if x.get('position')==args.chapter),None)
    if not chapter:ap.error('Numéro de chapitre absent du JSON')
    prompt=build_prompt(snapshot['book'],chapter,args.task)
    cmd=build_command(args.max_budget_usd)
    if args.dry_run:
        print(' '.join(repr(c) if c=='' else c for c in cmd));print('---');print(prompt);return 0
    if not shutil.which('claude'):
        ap.error('CLI claude introuvable. Installer Claude Code et exécuter claude auth login.')
    try:
        run=subprocess.run(cmd,input=prompt,capture_output=True,text=True,timeout=300,check=False)
    except subprocess.TimeoutExpired:
        print('La génération a expiré sans enregistrement.',file=sys.stderr);return 3
    if run.returncode!=0:
        print((run.stderr or 'Erreur Claude Code')[:3000],file=sys.stderr);return run.returncode
    if not run.stdout.strip():
        print('Réponse vide : rien enregistré.',file=sys.stderr);return 4
    args.out.mkdir(parents=True,exist_ok=True)
    target=args.out/f"chapitre-{args.chapter:02d}-{args.task}.md"
    banner='<!-- PROPOSITION IA NON VÉRIFIÉE — à relire et valider par un humain -->\n\n'
    target.write_text(banner+run.stdout,encoding='utf-8')
    print(f'Brouillon créé : {target} (copier après vérification dans le tableau de bord)')
    return 0

if __name__=='__main__':raise SystemExit(main())
