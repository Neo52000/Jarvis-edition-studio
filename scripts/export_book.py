#!/usr/bin/env python3
"""Transform a JARVIS Edition Studio exported JSON snapshot into Markdown, DOCX and A5 PDF.

This is a manuscript PREVIEW/WORKING PROOF, not a KDP-certified print-ready file.
Check margins, pagination, ISBN, cover and physical proof before publication.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether

CHECK_CODES = {'facts','language','originality','copyright','layout','pricing','human_review'}


def validate(snapshot: dict, final: bool = False) -> list[str]:
    problems = []
    book = snapshot.get('book', {})
    chapters = snapshot.get('chapters', [])
    if not book.get('title', '').strip():
        problems.append('Titre manquant')
    if not chapters:
        problems.append('Aucun chapitre')
    for ch in chapters:
        if not ch.get('title', '').strip() or not ch.get('content', '').strip():
            problems.append(f"Chapitre {ch.get('position', '?')} : titre ou contenu manquant")
    if final:
        if book.get('status') != 'approved':
            problems.append('Le statut du livre doit être approved')
        if any(ch.get('review_status') != 'reviewed' for ch in chapters):
            problems.append('Tous les chapitres doivent être relus')
        passing = {c.get('code') for c in snapshot.get('quality_checks', []) if c.get('verdict') == 'pass'}
        if not CHECK_CODES.issubset(passing):
            problems.append('Les sept contrôles qualité doivent être validés')
        if not any(a.get('decision') == 'approved' for a in snapshot.get('approvals', [])):
            problems.append('Visa humain absent')
    return problems


def clean_filename(text: str) -> str:
    normalized = unicodedata.normalize('NFKD', text.lower().strip())
    ascii_text = ''.join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9_-]+', '-', ascii_text.replace(' ', '-'))[:64].strip('-') or 'livre'


def get_chapters(snapshot: dict) -> list[dict]:
    return sorted(snapshot.get('chapters', []), key=lambda x: x.get('position', 0))


def markdown(snapshot: dict, draft: bool) -> str:
    book = snapshot['book']
    lines = [f"# {book['title']}"]
    if book.get('subtitle'): lines += ['', book['subtitle']]
    lines += ['', f"Auteur : {book.get('author_name', '')}"]
    if draft: lines += ['', '> MANUSCRIT DE TRAVAIL — NON APPROUVÉ POUR PUBLICATION']
    for chapter in get_chapters(snapshot):
        lines += ['', '---', '', f"## {chapter.get('position', '')}. {chapter['title']}", '', chapter['content'].strip()]
    lines += ['']
    return '\n'.join(lines)


def export_docx(snapshot: dict, path: Path, draft: bool) -> None:
    book = snapshot['book']
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(14.8), Cm(21)
    sec.top_margin = sec.bottom_margin = Cm(1.9)
    sec.left_margin = sec.right_margin = Cm(1.8)
    normal = doc.styles['Normal']
    normal.font.name = 'DejaVu Sans'
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(7)
    doc.add_heading(book['title'],0)
    if book.get('subtitle'): doc.add_paragraph(book['subtitle'], style='Subtitle')
    doc.add_paragraph(book.get('author_name',''))
    if draft: doc.add_paragraph('BROUILLON — NON VALIDÉ POUR PUBLICATION')
    for chapter in get_chapters(snapshot):
        doc.add_page_break()
        doc.add_heading(f"{chapter['position']}. {chapter['title']}", level=1)
        blocks = re.split(r'\n\s*\n', chapter['content'].strip())
        for block in blocks:
            for line in block.splitlines():
                line=line.strip()
                if not line: continue
                if line.startswith('### '): doc.add_heading(line[4:],level=3)
                elif line.startswith('## '): doc.add_heading(line[3:],level=2)
                elif line.startswith('- '): doc.add_paragraph(line[2:],style='List Bullet')
                else: doc.add_paragraph(line)
    doc.core_properties.title = book['title']
    doc.core_properties.author = book.get('author_name','')
    doc.save(path)


def font_setup() -> str:
    candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
    ]
    for path in candidates:
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont('StudioText',path))
            return 'StudioText'
    return 'Helvetica'  # Accent coverage not guaranteed on other systems.


def export_pdf(snapshot: dict, path: Path, draft: bool) -> None:
    book = snapshot['book']
    family = font_setup()
    title_style = ParagraphStyle('BookTitle',fontName=family,fontSize=20,leading=28,alignment=TA_CENTER,textColor=colors.HexColor('#1f3556'),spaceAfter=20)
    subtitle_style = ParagraphStyle('Subtitle',fontName=family,fontSize=11,leading=17,alignment=TA_CENTER,spaceAfter=14)
    chapter_style = ParagraphStyle('Chapter',fontName=family,fontSize=15,leading=21,textColor=colors.HexColor('#1f3556'),spaceAfter=18)
    body_style = ParagraphStyle('Body',fontName=family,fontSize=9.3,leading=14.7,alignment=TA_LEFT,spaceAfter=11)
    note_style = ParagraphStyle('Note',fontName=family,fontSize=8,leading=12,alignment=TA_CENTER,textColor=colors.HexColor('#a83333'))
    story=[Spacer(1,120),Paragraph(html.escape(book['title']),title_style)]
    if book.get('subtitle'): story.append(Paragraph(html.escape(book['subtitle']),subtitle_style))
    story.append(Paragraph(html.escape(book.get('author_name','')),subtitle_style))
    if draft: story.append(Paragraph('MANUSCRIT DE TRAVAIL — NON VALIDÉ',note_style))
    for chapter in get_chapters(snapshot):
        story.append(PageBreak())
        story.append(Paragraph(f"{chapter['position']}. {html.escape(chapter['title'])}",chapter_style))
        blocks = re.split(r'\n\s*\n',chapter['content'].strip())
        for block in blocks:
            for line in block.splitlines():
                line=line.strip()
                if not line:continue
                text=line.lstrip('#').strip() if line.startswith('#') else line
                if text.startswith('- '):text='• '+text[2:]
                story.append(Paragraph(html.escape(text).replace('\n',' '),body_style))
    doc=SimpleDocTemplate(str(path),pagesize=A5,leftMargin=47,rightMargin=47,topMargin=53,bottomMargin=52,
                          title=book['title'],author=book.get('author_name',''),pageCompression=1)
    def footer(canvas,doc):
        canvas.saveState()
        canvas.setFont(family,7)
        canvas.setFillColor(colors.HexColor('#7a899b'))
        canvas.drawCentredString(A5[0]/2,24,str(doc.page))
        if draft:
            canvas.setFont(family,7)
            canvas.setFillColor(colors.HexColor('#b45858'))
            canvas.drawString(47,24,'ÉPREUVE DE TRAVAIL')
        canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)


def main() -> int:
    parser=argparse.ArgumentParser(description='JARVIS Studio : export manuscrit en MD, DOCX et PDF A5')
    parser.add_argument('snapshot',type=Path,help='Fichier JSON téléchargé depuis le tableau de bord')
    parser.add_argument('--out',type=Path,default=Path('exports'),help='Dossier de sortie')
    parser.add_argument('--final',action='store_true',help='Refuser tout export sans validations enregistrées')
    args=parser.parse_args()
    snapshot=json.loads(args.snapshot.read_text(encoding='utf-8'))
    errors=validate(snapshot,final=args.final)
    if errors:
        for e in errors:print('ERREUR :',e)
        return 2
    args.out.mkdir(parents=True,exist_ok=True)
    filename=clean_filename(snapshot['book']['title'])
    draft=snapshot['book'].get('status')!='approved' or not args.final
    (args.out/f'{filename}.md').write_text(markdown(snapshot,draft),encoding='utf-8')
    export_docx(snapshot,args.out/f'{filename}.docx',draft)
    export_pdf(snapshot,args.out/f'{filename}.pdf',draft)
    for ext in ('md','docx','pdf'):print(args.out/f'{filename}.{ext}')
    print('NOTE : vérification physique et conformité imprimeur/KDP restent à effectuer.')
    return 0

if __name__=='__main__':raise SystemExit(main())
