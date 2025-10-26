from flask import Flask, jsonify, request, make_response
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_mail import Mail
from config.settings import settings

import socios
import convenios
import convenios_teste

app = Flask(__name__)
# Carrega configurações modernas (Settings) mantendo compat com legacy
for k, v in settings.dict().items():
    app.config[k] = v

jwt = JWTManager(app)
cors = CORS(app, resources={r"*": {"origins": "*"}}, supports_credentials=True)
mail = Mail(app)

api = Api(app)

@app.route('/')
def index():
    return jsonify("Seja Bem Vindo!")

api.add_resource(socios.UserRegistration, '/register')
api.add_resource(socios.UserLogin, '/login')
api.add_resource(socios.Usuarios, '/users')
api.add_resource(socios.Edita, '/edita')
api.add_resource(socios.Salva, '/salva')
api.add_resource(socios.Altera, '/altera')
api.add_resource(socios.Exclui, '/exclui')
api.add_resource(socios.Login_Extrato, '/login_extrato')
api.add_resource(socios.Descontos, '/descontos')
api.add_resource(socios.Compras, '/compras')
api.add_resource(socios.Margem, '/margem')
api.add_resource(socios.Codigo_Compra, '/codigo_compra')
api.add_resource(socios.Gera_Codigo, '/gera_codigo_senha')
api.add_resource(socios.Altera_Senha, '/altera_senha')
api.add_resource(socios.Altera_Cadastro, '/altera_cadastro')
api.add_resource(socios.Altera_Dados_Cadastro, '/altera_dados_cadastro')
api.add_resource(socios.Altera_Dados_Unico, '/altera_dados_unico')
api.add_resource(socios.Compras_Mensais_Socios, '/compras_mensais_socios')
api.add_resource(socios.Descontos_Mensais_Socios, '/descontos_mensais_socios')
api.add_resource(socios.Lista_Convenios, '/lista_convenios')
api.add_resource(socios.Autentica_Socios, '/autentica_socios')

#---------#
def _register_legacy_convenios():
    # Se desabilitado, expor endpoint sentinel retornando 410
    if not settings.LEGACY_CONVENIOS_ENABLED:
        @app.route('/legacy_convenios_disabled')
        def legacy_disabled():  # pragma: no cover (apenas quando desligado)
            return make_response({'error': 'Legacy convenios desativado'}, 410)
        return
    # Registro normal porém adicionando cabeçalho deprecação via after_request
    api.add_resource(convenios.LoginConvenio, '/login_convenios')
    api.add_resource(convenios.Receber_Mensal, '/receber_mensais')
    api.add_resource(convenios.Compras_Mensal, '/compras_mensais')
    api.add_resource(convenios.Autenticacao, '/autenticacao')
    api.add_resource(convenios.Grava_Vendas, '/grava_vendas')
    api.add_resource(convenios.Envia_Email_Codigo, '/envia_email_codigo')
    api.add_resource(convenios.Altera_Senha_Convenio, '/altera_senha_convenio')
    api.add_resource(convenios.Grava_Regs, '/grava_regs')
    api.add_resource(convenios.Envia_Email_Codigo_Esqueceu,'/envia_email_esqueceu')
    api.add_resource(convenios.Altera_Senha_Esqueceu_Convenio,'/altera_senha_esqueceu_convenio')
    api.add_resource(convenios.Busca_Limite, '/busca_limite')
    api.add_resource(convenios.Grava_Vendas_Senha, '/grava_vendas_senha')
    api.add_resource(convenios.Conta_Senha_Convenio, '/conta_senha_convenio')

_register_legacy_convenios()


#-----------------------------------#

# api de teste de aspma convenios
api.add_resource(convenios_teste.Login_Convenio_Teste, '/login_convenios_teste')
api.add_resource(convenios_teste.Receber_Mensal_Teste, '/receber_mensais_teste')
api.add_resource(convenios_teste.Compras_Mensal_Teste, '/compras_mensais_teste')
api.add_resource(convenios_teste.Autenticacao_Teste, '/autenticacao_teste')
api.add_resource(convenios_teste.Grava_Vendas_Teste, '/grava_vendas_teste')
api.add_resource(convenios_teste.Envia_Email_Codigo_Teste, '/envia_email_codigo_teste')
api.add_resource(convenios_teste.Altera_Senha_Convenio_Teste, '/altera_senha_convenio_teste')
api.add_resource(convenios_teste.Grava_Regs_Teste, '/grava_regs_teste')
api.add_resource(convenios_teste.Envia_Email_Codigo_Esqueceu_Teste,
                 '/envia_email_esqueceu_teste')
api.add_resource(convenios_teste.Altera_Senha_Esqueceu_Convenio_Teste,
                 '/altera_senha_esqueceu_convenio_teste')
api.add_resource(convenios_teste.Busca_Limite_Teste, '/busca_limite_teste')
api.add_resource(convenios_teste.Grava_Vendas_Senha_Teste, '/grava_vendas_senha_teste')
api.add_resource(convenios_teste.Conta_Senha_Convenio_Teste, '/conta_senha_convenio_teste')
#-----------------------------------#

if __name__ == "__main__":
    app.run()

# Middleware simples para garantir respostas a preflight em rotas legacy não-blueprint
@app.after_request
def add_cors_headers(resp):
    # Define CORS de forma explícita para evitar '*' com credentials=true
    origin_req = request.headers.get('Origin')
    allow_origin = origin_req or '*'
    resp.headers['Access-Control-Allow-Origin'] = allow_origin
    # Vary só quando não é wildcard
    if allow_origin != '*':
        existing_vary = resp.headers.get('Vary')
        if existing_vary:
            if 'Origin' not in existing_vary:
                resp.headers['Vary'] = existing_vary + ', Origin'
        else:
            resp.headers['Vary'] = 'Origin'
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    req_headers = request.headers.get('Access-Control-Request-Headers')
    resp.headers['Access-Control-Allow-Headers'] = req_headers or 'Authorization,Content-Type'
    # Cabeçalho de deprecação para rotas legacy convênios
    if settings.LEGACY_CONVENIOS_ENABLED and settings.LEGACY_CONVENIOS_SOFT_DEPRECATION:
        legacy_paths = (
            '/login_convenios','/receber_mensais','/compras_mensais','/autenticacao','/grava_vendas',
            '/envia_email_codigo','/altera_senha_convenio','/grava_regs','/envia_email_esqueceu',
            '/altera_senha_esqueceu_convenio','/busca_limite','/grava_vendas_senha','/conta_senha_convenio'
        )
        if request.path in legacy_paths:
            resp.headers['Deprecation'] = 'true'
            resp.headers['Sunset'] = 'Wed, 31 Dec 2025 23:59:59 GMT'
            resp.headers['Link'] = '<https://internal.docs/convenios-migration>; rel="deprecation"'
    return resp

@app.route('/compras_mensais', methods=['OPTIONS'])
def compras_mensais_options():
    resp = make_response('', 204)
    return resp

# Preflight explícito para endpoints legacy mais usados no frontend
@app.route('/envia_email_esqueceu', methods=['OPTIONS'])
def envia_email_esqueceu_options():
    return make_response('', 204)

@app.route('/altera_senha_esqueceu_convenio', methods=['OPTIONS'])
def altera_senha_esqueceu_convenio_options():
    return make_response('', 204)

# Preflight explícito para /autenticacao (legacy) para evitar 401 do @jwt_required no OPTIONS
@app.route('/autenticacao', methods=['OPTIONS'])
def autenticacao_options():
    return make_response('', 204)

# Catch-all para qualquer outro preflight não mapeado (evita 405 em OPTIONS)
@app.route('/<path:any_path>', methods=['OPTIONS'])
def any_options(any_path):
    return make_response('', 204)

# Compat: encaminhar /api/convenios/login para o handler moderno quando rodando este app legacy
@app.route('/api/convenios/login', methods=['POST', 'OPTIONS'])
def compat_api_convenios_login():
    if request.method == 'OPTIONS':
        # Responder preflight coerentemente com outras rotas
        origin_req = request.headers.get('Origin')
        allow_origin = origin_req or '*'
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = allow_origin
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        if allow_origin != '*':
            resp.headers['Vary'] = 'Origin'
        return resp
    # POST: delega para o novo handler
    from modules.convenios.routes import login_convenio as _login
    response = _login()
    try:
        origin_req = request.headers.get('Origin')
        if origin_req:
            response.headers['Access-Control-Allow-Origin'] = origin_req
            existing_vary = response.headers.get('Vary')
            if existing_vary:
                if 'Origin' not in existing_vary:
                    response.headers['Vary'] = existing_vary + ', Origin'
            else:
                response.headers['Vary'] = 'Origin'
    except Exception:
        pass
    return response

# Compat: encaminhar /api/convenios/limite e /api/convenios/venda-senha para handlers modernos
@app.route('/api/convenios/limite', methods=['POST', 'OPTIONS'])
def compat_api_convenios_limite():
    if request.method == 'OPTIONS':
        origin_req = request.headers.get('Origin')
        allow_origin = origin_req or '*'
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = allow_origin
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        if allow_origin != '*':
            resp.headers['Vary'] = 'Origin'
        return resp
    from modules.convenios.routes import limite_convenio as _limite
    response = _limite()
    try:
        origin_req = request.headers.get('Origin')
        if origin_req:
            response.headers['Access-Control-Allow-Origin'] = origin_req
            existing_vary = response.headers.get('Vary')
            if existing_vary:
                if 'Origin' not in existing_vary:
                    response.headers['Vary'] = existing_vary + ', Origin'
            else:
                response.headers['Vary'] = 'Origin'
    except Exception:
        pass
    return response

@app.route('/api/convenios/venda-senha', methods=['POST', 'OPTIONS'])
def compat_api_convenios_venda_senha():
    if request.method == 'OPTIONS':
        origin_req = request.headers.get('Origin')
        allow_origin = origin_req or '*'
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = allow_origin
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        if allow_origin != '*':
            resp.headers['Vary'] = 'Origin'
        return resp
    from modules.convenios.routes import venda_senha as _venda
    response = _venda()
    try:
        origin_req = request.headers.get('Origin')
        if origin_req:
            response.headers['Access-Control-Allow-Origin'] = origin_req
            existing_vary = response.headers.get('Vary')
            if existing_vary:
                if 'Origin' not in existing_vary:
                    response.headers['Vary'] = existing_vary + ', Origin'
            else:
                response.headers['Vary'] = 'Origin'
    except Exception:
        pass
    return response

# Compat: encaminhar /api/convenios/compras e /api/convenios/receber-mensais para handlers modernos
@app.route('/api/convenios/compras', methods=['POST', 'OPTIONS'])
def compat_api_convenios_compras():
    if request.method == 'OPTIONS':
        origin_req = request.headers.get('Origin')
        allow_origin = origin_req or '*'
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = allow_origin
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        if allow_origin != '*':
            resp.headers['Vary'] = 'Origin'
        return resp
    from modules.convenios.routes import compras_mensal as _compras
    response = _compras()
    try:
        origin_req = request.headers.get('Origin')
        if origin_req:
            response.headers['Access-Control-Allow-Origin'] = origin_req
            existing_vary = response.headers.get('Vary')
            if existing_vary:
                if 'Origin' not in existing_vary:
                    response.headers['Vary'] = existing_vary + ', Origin'
            else:
                response.headers['Vary'] = 'Origin'
    except Exception:
        pass
    return response

@app.route('/api/convenios/receber-mensais', methods=['POST', 'OPTIONS'])
def compat_api_convenios_receber_mensais():
    if request.method == 'OPTIONS':
        origin_req = request.headers.get('Origin')
        allow_origin = origin_req or '*'
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = allow_origin
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        if allow_origin != '*':
            resp.headers['Vary'] = 'Origin'
        return resp
    from modules.convenios.routes import receber_mensais as _receber
    response = _receber()
    try:
        origin_req = request.headers.get('Origin')
        if origin_req:
            response.headers['Access-Control-Allow-Origin'] = origin_req
            existing_vary = response.headers.get('Vary')
            if existing_vary:
                if 'Origin' not in existing_vary:
                    response.headers['Vary'] = existing_vary + ', Origin'
            else:
                response.headers['Vary'] = 'Origin'
    except Exception:
        pass
    return response

# Compat: encaminhar esqueceu-senha endpoints para handlers modernos
@app.route('/api/convenios/esqueceu/enviar-codigo', methods=['POST', 'OPTIONS'])
def compat_api_convenios_esqueceu_enviar_codigo():
    if request.method == 'OPTIONS':
        origin_req = request.headers.get('Origin')
        allow_origin = origin_req or '*'
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = allow_origin
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        if allow_origin != '*':
            resp.headers['Vary'] = 'Origin'
        return resp
    from modules.convenios.routes import esqueceu_enviar_codigo as _esq_env
    response = _esq_env()
    # Tentar inserir CORS sem quebrar quando a view retorna (Response, status)
    try:
        origin_req = request.headers.get('Origin')
        if origin_req:
            resp_obj = response[0] if isinstance(response, tuple) else response
            resp_obj.headers['Access-Control-Allow-Origin'] = origin_req
            existing_vary = resp_obj.headers.get('Vary')
            if existing_vary:
                if 'Origin' not in existing_vary:
                    resp_obj.headers['Vary'] = existing_vary + ', Origin'
            else:
                resp_obj.headers['Vary'] = 'Origin'
            if isinstance(response, tuple):
                response = (resp_obj, response[1])
            else:
                response = resp_obj
    except Exception:
        pass
    return response

@app.route('/api/convenios/esqueceu/alterar-senha', methods=['POST', 'OPTIONS'])
def compat_api_convenios_esqueceu_alterar_senha():
    if request.method == 'OPTIONS':
        origin_req = request.headers.get('Origin')
        allow_origin = origin_req or '*'
        resp = make_response('', 204)
        resp.headers['Access-Control-Allow-Origin'] = allow_origin
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        if allow_origin != '*':
            resp.headers['Vary'] = 'Origin'
        return resp
    from modules.convenios.routes import esqueceu_alterar_senha as _esq_alt
    response = _esq_alt()
    try:
        origin_req = request.headers.get('Origin')
        if origin_req:
            resp_obj = response[0] if isinstance(response, tuple) else response
            resp_obj.headers['Access-Control-Allow-Origin'] = origin_req
            existing_vary = resp_obj.headers.get('Vary')
            if existing_vary:
                if 'Origin' not in existing_vary:
                    resp_obj.headers['Vary'] = existing_vary + ', Origin'
            else:
                resp_obj.headers['Vary'] = 'Origin'
            if isinstance(response, tuple):
                response = (resp_obj, response[1])
            else:
                response = resp_obj
    except Exception:
        pass
    return response