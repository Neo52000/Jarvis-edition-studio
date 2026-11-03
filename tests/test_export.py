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
