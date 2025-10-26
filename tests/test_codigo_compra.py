import pytest
from modules.socios.service import SociosService
from core.exceptions import AuthenticationError

class FakeMongoRepoCodigo:
    def __init__(self):
        self.cache = {
            '1234': {
                'matricula': '1234',
                'associado': 'Teste',
                'tipo': 'A',
                'cpf': '12345678901',
                'email': 't@example.com',
                'celular': '11999999999',
                'bloqueio': 'NAO',
                # senha: plain 'abc123' hashed
                'senha': __import__('bcrypt').hashpw(b'abc123', __import__('bcrypt').gensalt())
            }
        }
        self.tentativas = {}
        self.codigos = {}
    # Métodos compatíveis com service
    def get_tentativas(self, m):
        return self.tentativas.get(m, 0)
    def incrementar_tentativa(self, m):
        self.tentativas[m] = self.get_tentativas(m) + 1
        return self.tentativas[m]
    def reset_tentativas(self, m):
        self.tentativas.pop(m, None)
    def set_bloqueio_login_cache(self, m, status):
        if m in self.cache:
            self.cache[m]['bloqueio'] = status
    def find_login_data(self, m):
        return self.cache.get(m)
    def codigo_existe(self, c):
        return c in self.codigos.values()
    def store_codigo_compra(self, m, c, associados):
        self.codigos[m] = c
    # não usados aqui
    def store_login_data(self, socio):
        pass

service = SociosService(mongo_repo=FakeMongoRepoCodigo())


def test_codigo_compra_sucesso():
    res = service.gerar_codigo_compra('1234', 'abc123', '12301', 'new@example.com', '1188888888')
    assert 'codigo' in res
    assert res['nr_vezes'] == 0


def test_codigo_compra_cpf_errado_incrementa():
    with pytest.raises(AuthenticationError):
        service.gerar_codigo_compra('1234', 'abc123', '99999', 'a@b.com', '1188888888')
    # segunda tentativa também falha
    with pytest.raises(AuthenticationError):
        service.gerar_codigo_compra('1234', 'abc123', '99999', 'a@b.com', '1188888888')
    # terceira bloqueia
    with pytest.raises(AuthenticationError):
        service.gerar_codigo_compra('1234', 'abc123', '99999', 'a@b.com', '1188888888')


def test_codigo_compra_senha_errada():
    with pytest.raises(AuthenticationError):
        service.gerar_codigo_compra('1234', 'wrong', '12301', 'a@b.com', '1188888888')
