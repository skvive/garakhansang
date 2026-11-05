import importlib.util
from pathlib import Path
import pytest

src=Path(__file__).resolve().parents[1]/'tools/emulator_smoke.py'
spec=importlib.util.spec_from_file_location('gho_emulator_smoke',src)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
XML='''<hierarchy rotation="0"><node text="홈" bounds="[0,1800][100,1900]"/>
<node text="메뉴" bounds="[100,1800][200,1900]"/>
<node text="장바구니" bounds="[200,1800][300,1900]"/></hierarchy>'''

def test_text_based_navigation():
    assert mod.locate_text(XML,'메뉴')==(150,1850)
    assert mod.locate_text(XML,'장바구니')==(250,1850)

def test_missing_label_fails_closed():
    with pytest.raises(ValueError):mod.locate_text(XML,'주문 접수 완료')

@pytest.mark.parametrize('bounds',['[0,0][0,2]','bad','[1,3][4,2]','[x,2][5,6]'])
def test_bad_bounds(bounds):
    with pytest.raises(ValueError):mod.center_of_bounds(bounds)
