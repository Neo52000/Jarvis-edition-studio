import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('export_book',ROOT/'scripts'/'export_book.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_draft_and_final_gate():
    sample=json.loads((ROOT/'examples'/'sample_book.json').read_text())
    assert module.validate(sample,final=False)==[]
    assert module.validate(sample,final=True)
    sample['book']['status']='approved'
    for c in sample['chapters']: c['review_status']='reviewed'
    sample['quality_checks']=[{'code':code,'verdict':'pass'} for code in module.CHECK_CODES]
    sample['approvals']=[{'decision':'approved'}]
    assert module.validate(sample,final=True)==[]


def test_export_files(tmp_path):
    sample=json.loads((ROOT/'examples'/'sample_book.json').read_text())
    module.export_docx(sample,tmp_path/'book.docx',True)
    module.export_pdf(sample,tmp_path/'book.pdf',True)
    assert (tmp_path/'book.docx').stat().st_size>4000
    assert (tmp_path/'book.pdf').stat().st_size>3000
    assert 'MANUSCRIT' in module.markdown(sample,True)


def test_accents_ligatures_and_inline_markup(tmp_path):
    sample=json.loads((ROOT/'examples'/'sample_book.json').read_text())
    sample['chapters'][0]['content']='## Cœur\n\nUn **texte gras** et *italique*, prix 12,90 € « ok ».\n\n- point'
    module.export_pdf(sample,tmp_path/'b.pdf',True)
    module.export_docx(sample,tmp_path/'b.docx',True)
    from docx import Document
    paras=Document(tmp_path/'b.docx').paragraphs
    assert any(r.bold and r.text=='texte gras' for p in paras for r in p.runs)
    assert not any('**' in p.text for p in paras)
    assert module.pdf_inline('a <b> & **x**')=='a &lt;b&gt; &amp; <b>x</b>'
    assert (tmp_path/'b.pdf').read_bytes().startswith(b'%PDF')


def test_final_gate_blocks_missing_pieces():
    sample=json.loads((ROOT/'examples'/'sample_book.json').read_text())
    sample['book']['status']='approved'
    for c in sample['chapters']: c['review_status']='reviewed'
    sample['quality_checks']=[{'code':c,'verdict':'pass'} for c in list(module.CHECK_CODES)[:6]]
    sample['approvals']=[{'decision':'approved'}]
    assert any('sept' in e for e in module.validate(sample,final=True))
    sample['quality_checks']=[{'code':c,'verdict':'pass'} for c in module.CHECK_CODES]
    sample['approvals']=[]
    assert any('Visa' in e for e in module.validate(sample,final=True))


def test_cli_final_refuses_unapproved(tmp_path):
    import subprocess,sys
    r=subprocess.run([sys.executable,str(ROOT/'scripts'/'export_book.py'),str(ROOT/'examples'/'sample_book.json'),'--out',str(tmp_path),'--final'],capture_output=True,text=True)
    assert r.returncode==2 and not list(tmp_path.iterdir())
