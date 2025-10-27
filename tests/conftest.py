import sys, pathlib, os

# Ensure backend root on PYTHONPATH for test imports like `import app_mvc`
backend_root = pathlib.Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

# Não força modo fake por padrão; testes de integração específicos setarão ENABLE_FAKE_LOGIN
os.environ.setdefault('ENABLE_FAKE_LOGIN', 'false')
