import pytest
from modules.convenios.service import ConveniosService


class FakeSettings:
    CORTE_DIA = 9
    WHATSAPP_ENABLED = False
    WHATS_GW_API_URL = 'https://app.whatsgw.com.br/api/WhatsGw/Send'
    WHATS_GW_APIKEY = 'dummy'
    WHATS_GW_SENDER = '5541900000000'
    WHATS_DEFAULT_DDD = '41'


class FakeRepo:
    def __init__(self, celular='12345678', tipo=0, limite=1000.0, utilizado=0.0):
        self._socio = {
            'tipo': tipo, 'limite': limite, 'sequencia': 5,
            'associado': 'JOAO TESTE', 'cpf': '12345678901', 'celular': celular
        }
        self._utilizado = utilizado
        self.saved = None

    def fetch_socio_core(self, matricula):
        return self._socio if matricula == '999999' else None

    def soma_parcelas_mes(self, matricula, ano, mes):
        return self._utilizado

    def registrar_venda(self, venda: dict):
        self.saved = venda


def test_mask_phone_8_digits():
    svc = ConveniosService(repo=FakeRepo(celular='12345678'), settings=FakeSettings())
    masked = svc._mask_phone('12345678')
    assert masked == '(41) 9*****78'


def test_mask_phone_11_digits():
    # número com DDD (41) e 9 dígitos
    svc = ConveniosService(repo=FakeRepo(celular='41999999999'), settings=FakeSettings())
    masked = svc._mask_phone('41999999999')
    assert masked == '(41) 9*****99'


def test_calcular_limite_includes_phone_mask_and_whatsapp_flag_false_by_default():
    settings = FakeSettings()
    settings.WHATSAPP_ENABLED = False  # padrão
    svc = ConveniosService(repo=FakeRepo(celular='12345678'), settings=settings)
    resp = svc.calcular_limite('999999', '600,00', 3)
    assert resp.get('phone_mask') == '(41) 9*****78'
    # Como envio está desativado, whatsapp_sent deve ser False
    assert resp.get('whatsapp_sent') is False


def test_calcular_limite_whatsapp_sent_true_when_enabled_and_send_ok(monkeypatch):
    settings = FakeSettings()
    settings.WHATSAPP_ENABLED = True
    svc = ConveniosService(repo=FakeRepo(celular='12345678'), settings=settings)
    # evita chamada real e força sucesso
    monkeypatch.setattr(svc, '_send_whatsapp', lambda *a, **k: True)
    resp = svc.calcular_limite('999999', '600,00', 3)
    assert resp.get('whatsapp_sent') is True


def test_registrar_venda_senha_sets_post_flags(monkeypatch):
    settings = FakeSettings()
    settings.WHATSAPP_ENABLED = True
    repo = FakeRepo(celular='12345678')
    svc = ConveniosService(repo=repo, settings=settings)
    monkeypatch.setattr(svc, '_send_whatsapp', lambda *a, **k: True)
    dados = {
        'matricula': '999999', 'associado': 'JOAO TESTE', 'sequencia': 6,
        'nr_parcelas': 2, 'valor': '200,00', 'mes': 10, 'ano': 2025, 'tipo': 0
    }
    ok = svc.registrar_venda_senha(dados, codigo_convenio='123', nome_convenio='CONV', usuario='user')
    assert ok is True
    assert svc._last_phone_mask_post == '(41) 9*****78'
    assert svc._last_whatsapp_sent_post is True


def test_registrar_venda_senha_includes_id_compra_in_confirmation(monkeypatch):
    settings = FakeSettings()
    settings.WHATSAPP_ENABLED = True
    repo = FakeRepo(celular='12345678')
    svc = ConveniosService(repo=repo, settings=settings)

    captured = {}

    def fake_send(associado_primeiro_nome, convenio, id_compra, valor_total, nr_parcelas, valor_parcela, contato_celular):
        captured['id_compra'] = id_compra
        captured['nr_parcelas'] = nr_parcelas
        captured['valor_total'] = valor_total
        captured['valor_parcela'] = valor_parcela
        return True

    monkeypatch.setattr(svc, '_send_whatsapp', fake_send)

    dados = {
        'matricula': '999999', 'associado': 'JOAO TESTE', 'sequencia': 6,
        'nr_parcelas': 2, 'valor': '200,00', 'mes': 10, 'ano': 2025, 'tipo': 0,
        'id_compra': '1234'
    }
    svc.registrar_venda_senha(dados, codigo_convenio='123', nome_convenio='CONV', usuario='user')
    assert captured.get('id_compra') == '1234'
