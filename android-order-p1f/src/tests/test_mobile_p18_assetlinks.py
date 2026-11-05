import importlib.util
from pathlib import Path
import pytest

PATH=Path(__file__).resolve().parents[1]/'tools/generate_assetlinks.py'
spec=importlib.util.spec_from_file_location('gho_assetlinks',PATH)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_exact_package_and_sha256():
    fingerprint='AB:'*31+'CD'
    val=module.make_statement('site.lexid.garakhansang.order',fingerprint)
    assert val[0]['relation']==['delegate_permission/common.handle_all_urls']
    assert val[0]['target']['package_name']=='site.lexid.garakhansang.order'
    assert val[0]['target']['sha256_cert_fingerprints']==[fingerprint]

@pytest.mark.parametrize('bad',["", "1234", 'AA:'*32, 'GG:'*31+'GG', 'FF'*32, 'FF:'*30+'XX:FF'])
def test_bad_digest_rejected(bad):
    with pytest.raises(ValueError):module.make_statement('site.lexid.garakhansang.order',bad)

@pytest.mark.parametrize('bad',['site.lexid.other','site.lexid.garakhansang.order.debug',''])
def test_wrong_application_id_rejected(bad):
    with pytest.raises(ValueError):module.make_statement(bad,'AB:'*31+'CD')
