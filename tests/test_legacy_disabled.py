import os
import importlib
import pytest


def build_app(disabled: bool):
    """Recarrega o módulo app com flags ajustadas."""
    os.environ['LEGACY_CONVENIOS_ENABLED'] = 'false' if disabled else 'true'
    os.environ['LEGACY_CONVENIOS_SOFT_DEPRECATION'] = 'true'
    import sys
    # Garante que Settings seja recalculado com novas envs
    for mod in ('app', 'config.settings'):
        if mod in sys.modules:
            del sys.modules[mod]
    importlib.invalidate_caches()
    app_module = importlib.import_module('app')
    return app_module.app.test_client()


@pytest.mark.parametrize(
    "path,should_exist",
    [
        ('/login_convenios', False),
        ('/legacy_convenios_disabled', True),
    ]
)
def test_legacy_routes_absent_when_disabled(path, should_exist):
    client = build_app(disabled=True)
    resp = client.get(path)
    if should_exist:
        # Sentinel deve devolver 410 (ou 200 se futuramente alterado)
        assert resp.status_code in (200, 404, 410)
        # Se 404 aqui, significa que o sentinel não foi criado -> falha explícita
        if path == '/legacy_convenios_disabled':
            assert resp.status_code != 404, 'Sentinel /legacy_convenios_disabled não registrado'
    else:
        # Quando desabilitado, rota legacy não deve responder com 200; aceita 404 ou 405 (method) ou 410
        assert resp.status_code in (404, 405, 410)

