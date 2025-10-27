import os, pytest

def test_legacy_deprecation_header_present():
    # Assume default settings (enabled) – just import app
    os.environ['LEGACY_CONVENIOS_ENABLED'] = 'true'
    os.environ['LEGACY_CONVENIOS_SOFT_DEPRECATION'] = 'true'
    import app as app_module
    client = app_module.app.test_client()
    r = client.options('/compras_mensais')
    assert r.status_code in (200,204,405)
    assert r.headers.get('Deprecation') == 'true'
    assert 'Sunset' in r.headers
