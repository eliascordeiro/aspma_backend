import sys, pathlib
backend_dir = pathlib.Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app_mvc import create_app


def test_health_endpoint():
    app = create_app()
    with app.test_client() as c:
        r = c.get('/health')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] == 'ok'


def test_root_legacy_index_import_wsgi():
    # Garante que wsgi importa sem explodir e que rota / existe no app legacy
    import wsgi  # noqa
    assert hasattr(wsgi, 'app')
    with wsgi.app.test_client() as c:
        r = c.get('/')
        assert r.status_code == 200
