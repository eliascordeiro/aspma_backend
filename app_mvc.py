from flask import Flask, jsonify
from flask_cors import CORS
from config.settings import Settings
from config.database import DatabaseManager 
from core.security import init_security, limiter
from core.exceptions import AppError
from core.responses import error as error_json

# Importar blueprints dos novos módulos
from modules.socios import socios_bp
from modules.convenios.routes import convenios_bp

import logging, json, sys
from flasgger import Swagger
from flask import request, make_response, jsonify
from flask_jwt_extended import jwt_required

def create_app():
    """
    Application Factory Pattern para criar instância Flask.
    
    Benefícios:
    - Configuração centralizada baseada em ambiente
    - Inicialização segura de extensões
    - Facilita testes unitários
    - Separação de responsabilidades
    """
    
    app = Flask(__name__)
    
    # Carregar configurações baseadas no ambiente
    settings = Settings()
    app.config.update(settings.dict())

    # Logging básico estruturado
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        handlers=[logging.StreamHandler(sys.stdout)],
        format='%(message)s'
    )

    def log_event(event: str, **kwargs):
        payload = {"event": event, **kwargs}
        try:
            logging.getLogger('app').info(json.dumps(payload, ensure_ascii=False))
        except Exception:
            logging.getLogger('app').info(str(payload))
    app.log_event = log_event  # attach helper
    
    # Configurar CORS (expandindo variantes localhost <-> 127.0.0.1 para evitar erros de dev)
    raw_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, (list, tuple)) else [settings.CORS_ORIGINS]
    if '*' in raw_origins:
        expanded_origins = ['*']
    else:
        from urllib.parse import urlparse
        expanded = []
        for o in raw_origins:
            try:
                p = urlparse(o)
                if p.scheme and p.netloc:
                    host = p.hostname
                    port = f":{p.port}" if p.port else ''
                    if host in ('localhost', '127.0.0.1'):
                        for h in ('localhost', '127.0.0.1'):
                            variant = f"{p.scheme}://{h}{port}"
                            expanded.append(variant)
                    else:
                        expanded.append(o)
                else:
                    expanded.append(o)
            except Exception:
                expanded.append(o)
        # Remover duplicados mantendo ordem
        seen = set()
        expanded_origins = [x for x in expanded if not (x in seen or seen.add(x))]
    CORS(app,
         origins=expanded_origins,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
    # Inicializar extensões de segurança
    init_security(app)
    limiter.init_app(app)
    
    # Inicializar gerenciador de banco (lazy loading)
    DatabaseManager.init_app(app)
    
    # Swagger 2.0 (revert temporário para compatibilidade com docstrings atuais).
    # As docstrings usam formato Swagger 2 (parameters + in: body). Migração para
    # OpenAPI 3 exigirá adaptação (requestBody). Mantemos alias /api/docs/openapi.json
    # apontando para o mesmo conteúdo para consumidores que já tentaram a rota nova.
    swagger_template = {
        'swagger': '2.0',
        'info': {
            'title': 'ConsigExpress API',
            'description': 'Documentação interativa dos endpoints Sócios e Convênios',
            'version': '1.0.1'
        },
        'schemes': ['https', 'http'],
        'securityDefinitions': {
            'BearerAuth': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'JWT Bearer token. Formato: Bearer <token>'
            }
        },
        'security': [
            {'BearerAuth': []}
        ]
    }
    swagger_config = {
        'headers': [],
        'specs': [
            {  # Legacy route name retained
                'endpoint': 'apispec_1',
                'route': '/api/docs/apispec.json',
                'rule_filter': lambda rule: True,
                'model_filter': lambda tag: True,
            },
            {  # New canonical OpenAPI 3 alias
                'endpoint': 'openapi_alias',
                'route': '/api/docs/openapi.json',
                'rule_filter': lambda rule: True,
                'model_filter': lambda tag: True,
            }
        ],
        'static_url_path': '/flasgger_static',
        'swagger_ui': True,
        'specs_route': '/api/docs/'
    }
    Swagger(app, template=swagger_template, config=swagger_config)

    # Registrar blueprints novos (MVC)
    app.register_blueprint(socios_bp)
    app.register_blueprint(convenios_bp)

    # Preflight catch-all para evitar 405 em OPTIONS durante CORS (similar ao legacy app.py)
    @app.route('/api/<path:any_path>', methods=['OPTIONS'])
    def api_any_options(any_path):  # pragma: no cover (infra/preflight)
        return make_response('', 204)

    @app.route('/<path:any_path>', methods=['OPTIONS'])
    def any_options(any_path):  # pragma: no cover (infra/preflight)
        return make_response('', 204)

    # Debug: logar rotas registradas no startup
    try:
        rules_dump = []
        for r in app.url_map.iter_rules():
            rules_dump.append({
                'endpoint': r.endpoint,
                'rule': str(r),
                'methods': sorted(list(r.methods or []))
            })
        app.log_event('startup_routes', total=len(rules_dump), routes=rules_dump)
    except Exception:
        pass

    # Rota de compatibilidade LEGACY para clientes antigos que ainda usam /login_convenios
    # (antigo app.py com Flask-RESTful). Delegamos à lógica do novo endpoint.
    @app.route('/login_convenios', methods=['POST', 'OPTIONS'])
    def legacy_login_convenios():  # pragma: no cover (delegação simples)
        from flask import make_response, request
        # Preflight manual (alguns browsers exigem cabeçalhos explícitos quando rota não está no blueprint com prefixo /api)
        allowed = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, (list, tuple)) else [settings.CORS_ORIGINS]
        origin_req = request.headers.get('Origin')

        # Normalização: tratar localhost e 127.0.0.1 como equivalentes para facilitar dev
        def host_variants(o: str):
            if not o:
                return []
            try:
                from urllib.parse import urlparse
                p = urlparse(o)
                base = f"{p.scheme}://{{host}}{':' + str(p.port) if p.port else ''}"
                variants = []
                if p.hostname in ('localhost', '127.0.0.1'):
                    for h in ('localhost', '127.0.0.1'):
                        variants.append(base.format(host=h))
                else:
                    variants.append(o)
                return list(dict.fromkeys(variants))  # preserve order / dedupe
            except Exception:
                return [o]

        expanded_allowed = set()
        for a in allowed:
            for v in host_variants(a):
                expanded_allowed.add(v)

        if '*' in allowed:
            allow_origin = '*'
        elif origin_req and (origin_req in expanded_allowed or any(v in expanded_allowed for v in host_variants(origin_req))):
            # Ecoa exatamente a Origin recebida para satisfazer política do navegador
            allow_origin = origin_req
        else:
            # fallback: primeiro permitido (já normalizado quando possível)
            allow_origin = next(iter(expanded_allowed), 'http://localhost:3000')
        if request.method == 'OPTIONS':
            resp = make_response('', 204)
            resp.headers['Access-Control-Allow-Origin'] = allow_origin
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            resp.headers['Access-Control-Max-Age'] = '600'
            if allow_origin != '*':
                resp.headers['Vary'] = 'Origin'
            return resp
        from modules.convenios.routes import login_convenio as _login
        response = _login()
        # Garante header em resposta principal também
        try:
            response.headers['Access-Control-Allow-Origin'] = allow_origin
            if allow_origin != '*':
                # Evita sobrescrever Vary existente
                existing_vary = response.headers.get('Vary')
                if existing_vary:
                    if 'Origin' not in existing_vary:
                        response.headers['Vary'] = existing_vary + ', Origin'
                else:
                    response.headers['Vary'] = 'Origin'
        except Exception:
            pass
        return response

    # Rota de compatibilidade LEGACY para clientes que ainda usam /autenticacao (sem prefixo /api)
    @app.route('/autenticacao', methods=['POST', 'OPTIONS'])
    def legacy_autenticacao():  # pragma: no cover (delegação simples)
        from flask import make_response, request
        allowed = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, (list, tuple)) else [settings.CORS_ORIGINS]
        origin_req = request.headers.get('Origin')

        def host_variants(o: str):
            if not o:
                return []
            try:
                from urllib.parse import urlparse
                p = urlparse(o)
                base = f"{p.scheme}://{{host}}{':' + str(p.port) if p.port else ''}"
                variants = []
                if p.hostname in ('localhost', '127.0.0.1'):
                    for h in ('localhost', '127.0.0.1'):
                        variants.append(base.format(host=h))
                else:
                    variants.append(o)
                return list(dict.fromkeys(variants))
            except Exception:
                return [o]

        expanded_allowed = set()
        for a in allowed:
            for v in host_variants(a):
                expanded_allowed.add(v)

        if '*' in allowed:
            allow_origin = '*'
        elif origin_req and (origin_req in expanded_allowed or any(v in expanded_allowed for v in host_variants(origin_req))):
            allow_origin = origin_req
        else:
            allow_origin = next(iter(expanded_allowed), 'http://localhost:3000')

        if request.method == 'OPTIONS':
            resp = make_response('', 204)
            resp.headers['Access-Control-Allow-Origin'] = allow_origin
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            resp.headers['Access-Control-Max-Age'] = '600'
            if allow_origin != '*':
                resp.headers['Vary'] = 'Origin'
            return resp

        # Delegar para o endpoint MVC de autenticação de ação
        from modules.convenios.routes import autenticacao_acao as _autentica
        response = _autentica()
        try:
            response.headers['Access-Control-Allow-Origin'] = allow_origin
            if allow_origin != '*':
                existing_vary = response.headers.get('Vary')
                if existing_vary:
                    if 'Origin' not in existing_vary:
                        response.headers['Vary'] = existing_vary + ', Origin'
                else:
                    response.headers['Vary'] = 'Origin'
        except Exception:
            pass
        return response

    # Garantir métodos válidos mesmo em ambientes que apresentem 405 por conflitos de rota/OPTIONS
    @app.route('/api/convenios/limite', methods=['POST', 'OPTIONS'])
    def mvc_compat_limite():  # pragma: no cover (infra compat)
        from flask import make_response, request
        if request.method == 'OPTIONS':
            resp = make_response('', 204)
            # CORS básicos
            origin_req = request.headers.get('Origin')
            allow_origin = origin_req or '*'
            resp.headers['Access-Control-Allow-Origin'] = allow_origin
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            if allow_origin != '*':
                resp.headers['Vary'] = 'Origin'
            return resp
        from modules.convenios.routes import limite_convenio as _limite
        return _limite()

    # Registrar regra explícita sem OPTIONS automático para evitar 405 por conflito
    try:
        from modules.convenios.routes import limite_convenio as _limite_view
        app.add_url_rule('/api/convenios/limite', endpoint='mvc_limite_direct', view_func=_limite_view, methods=['POST'], provide_automatic_options=False)
    except Exception:
        pass

    @app.route('/api/convenios/venda-senha', methods=['POST', 'OPTIONS'])
    def mvc_compat_venda_senha():  # pragma: no cover (infra compat)
        if request.method == 'OPTIONS':
            resp = make_response('', 204)
            origin_req = request.headers.get('Origin')
            allow_origin = origin_req or '*'
            resp.headers['Access-Control-Allow-Origin'] = allow_origin
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            if allow_origin != '*':
                resp.headers['Vary'] = 'Origin'
            return resp
        from modules.convenios.routes import venda_senha as _venda
        return _venda()

    try:
        from modules.convenios.routes import venda_senha as _venda_view
        app.add_url_rule('/api/convenios/venda-senha', endpoint='mvc_venda_senha_direct', view_func=_venda_view, methods=['POST'], provide_automatic_options=False)
    except Exception:
        pass

    # Compatível com legado: /busca_limite (sem depender do Mongo legado)
    @app.route('/busca_limite', methods=['POST', 'OPTIONS'])
    @jwt_required()
    def legacy_busca_limite_compat():  # pragma: no cover (compat)
        if request.method == 'OPTIONS':
            resp = make_response('', 204)
            origin_req = request.headers.get('Origin')
            allow_origin = origin_req or '*'
            resp.headers['Access-Control-Allow-Origin'] = allow_origin
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            if allow_origin != '*':
                resp.headers['Vary'] = 'Origin'
            return resp
        try:
            payload = request.get_json(force=True) or {}
            dados = payload.get('dados') if isinstance(payload.get('dados'), dict) else payload
            matricula = str(dados.get('matricula', '')).strip()
            valor = str(dados.get('valor', '')).strip()
            try:
                nr_parcelas = int(dados.get('nr_parcelas', 1))
            except Exception:
                nr_parcelas = 1
            # Usa o serviço moderno para calcular, evitando o caminho Mongo legado
            from modules.convenios.routes import service as convenios_service
            res = convenios_service.calcular_limite(matricula, valor, nr_parcelas)
            # Mapeia resposta moderna para formato legado
            if isinstance(res, dict) and res.get('insuficiente'):
                return jsonify({'msg': 'Saldo insuficiente!', 'saldo': res.get('saldo')}), 200
            return jsonify({'msg': res}), 200
        except Exception as e:
            # Mantém simplicidade legado: retorna msg em caso de erro
            return jsonify({'msg': 'Erro ao calcular limite'}), 400

    # Endpoint de debug para inspecionar rotas e métodos permitidos
    @app.route('/_debug/routes', methods=['GET'])
    def debug_routes():  # pragma: no cover (debug only)
        from flask import jsonify, request
        path = request.args.get('path')
        items = []
        for r in app.url_map.iter_rules():
            if not path or str(r) == path:
                items.append({
                    'endpoint': r.endpoint,
                    'rule': str(r),
                    'methods': sorted(list(r.methods or []))
                })
        return jsonify({'count': len(items), 'routes': items})

    # Rota de compatibilidade LEGACY para clientes que usam /envia_email_esqueceu
    @app.route('/envia_email_esqueceu', methods=['POST', 'OPTIONS'])
    def legacy_envia_email_esqueceu():  # pragma: no cover
        from flask import make_response, request
        allowed = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, (list, tuple)) else [settings.CORS_ORIGINS]
        origin_req = request.headers.get('Origin')

        def host_variants(o: str):
            if not o:
                return []
            try:
                from urllib.parse import urlparse
                p = urlparse(o)
                base = f"{p.scheme}://{{host}}{':' + str(p.port) if p.port else ''}"
                variants = []
                if p.hostname in ('localhost', '127.0.0.1'):
                    for h in ('localhost', '127.0.0.1'):
                        variants.append(base.format(host=h))
                else:
                    variants.append(o)
                return list(dict.fromkeys(variants))
            except Exception:
                return [o]

        expanded_allowed = set()
        for a in allowed:
            for v in host_variants(a):
                expanded_allowed.add(v)

        if '*' in allowed:
            allow_origin = '*'
        elif origin_req and (origin_req in expanded_allowed or any(v in expanded_allowed for v in host_variants(origin_req))):
            allow_origin = origin_req
        else:
            allow_origin = next(iter(expanded_allowed), 'http://localhost:3000')

        if request.method == 'OPTIONS':
            resp = make_response('', 204)
            resp.headers['Access-Control-Allow-Origin'] = allow_origin
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            resp.headers['Access-Control-Max-Age'] = '600'
            if allow_origin != '*':
                resp.headers['Vary'] = 'Origin'
            return resp

        # Delegar para endpoint MVC de esqueceu (aceita formato legacy)
        from modules.convenios.routes import esqueceu_enviar_codigo as _esq
        response = _esq()
        try:
            response.headers['Access-Control-Allow-Origin'] = allow_origin
            if allow_origin != '*':
                existing_vary = response.headers.get('Vary')
                if existing_vary:
                    if 'Origin' not in existing_vary:
                        response.headers['Vary'] = existing_vary + ', Origin'
                else:
                    response.headers['Vary'] = 'Origin'
        except Exception:
            pass
        return response

    # Rota legacy opcional com formato antigo (tokens no topo e dados inline)
    # Útil para consumidores que esperam {access_token, refresh_token, token_type, dados:{...}}
    @app.route('/legacy/login_convenios_format_old', methods=['POST'])
    def legacy_login_convenios_old_format():  # pragma: no cover (compat)
        from modules.convenios.routes import login_convenio as _login
        resp = _login()
        try:
            # success_response retorna (Response, status)
            response_obj = resp[0] if isinstance(resp, tuple) else resp
            data = response_obj.get_json() if hasattr(response_obj, 'get_json') else None
            if data and data.get('success') and 'data' in data:
                payload = data['data']
                tokens = payload.get('tokens', {})
                dados = payload.get('dados', {})
                old_shape = {
                    'access_token': tokens.get('access_token'),
                    'refresh_token': tokens.get('refresh_token'),
                    'token_type': tokens.get('token_type'),
                    'dados': dados
                }
                if data.get('meta') and data['meta'].get('fake_login'):
                    old_shape['fake_login'] = True
                from flask import jsonify
                return jsonify(old_shape), 200
        except Exception:
            pass
        return resp

    # Health check básico legado (/health) - manter nome diferente para não bloquear /api/health
    @app.get('/health')
    def basic_health():
        return jsonify({'status': 'ok'}), 200

    # Error handlers
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        app.log_event('app_error', code=err.code, message=err.message)
        return error_json(message=err.message, code=err.code, status_code=err.status_code)

    @app.errorhandler(404)
    def handle_404(_):
        return error_json(message='Rota não encontrada', code='NOT_FOUND', status_code=404)

    @app.errorhandler(Exception)
    def handle_generic(err: Exception):
        # Não intercepta erros de rotas do Flasgger/Swagger
        from flask import request
        if request.path and (request.path.startswith('/api/docs') or 
                            request.path.startswith('/flasgger') or
                            request.path.startswith('/apispec')):
            # Deixa o Flasgger tratar seus próprios erros
            raise err
        
        app.log_event('internal_error', error=str(err.__class__.__name__))
        app.logger.exception(err)
        return error_json(message='Erro interno', code='INTERNAL_ERROR', status_code=500)

    # COMPATIBILIDADE: Registrar rotas legacy durante migração
    register_legacy_routes(app)

    # Health endpoint simples na raiz (para Railway/Render/Heroku)
    if 'root_health' not in app.view_functions:
        @app.route('/health', endpoint='root_health')
        @app.route('/', endpoint='root')
        def root_health():  # type: ignore
            """Endpoint de health check para provedores cloud"""
            return {
                'status': 'healthy',
                'service': 'ConsigExpress Backend API',
                'version': '1.0.1',
                'docs': '/apidocs'
            }, 200

    # Health endpoint com verificação de databases
    if 'api_health' not in app.view_functions:
        @app.route('/api/health', endpoint='api_health')
        def health():  # type: ignore
            from config.database import DatabaseManager
            status = {'mysql': False, 'mongo': False}
            details = {}
            # MySQL
            try:
                with DatabaseManager.get_mysql_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute('SELECT 1')
                        status['mysql'] = True
            except Exception as e:
                details['mysql_error'] = str(e.__class__.__name__)
            # Mongo
            try:
                mgr = DatabaseManager.get_mongo_client()
                db = getattr(mgr, '_mongo_db', None)
                if db is not None:
                    db.command('ping')
                    status['mongo'] = True
            except Exception as e:
                details['mongo_error'] = str(e.__class__.__name__)
            return {
                'ok': status['mysql'] or status['mongo'],
                'components': status,
                'details': details
            }, (200 if status['mysql'] or status['mongo'] else 503)

    # Health do e-mail
    if 'api_health_mail' not in app.view_functions:
        @app.route('/api/health/mail', endpoint='api_health_mail')
        def health_mail():  # type: ignore
            from flask import current_app
            info = {
                'configured': False,
                'server': app.config.get('MAIL_SERVER'),
                'port': app.config.get('MAIL_PORT'),
                'use_tls': app.config.get('MAIL_USE_TLS'),
                'use_ssl': app.config.get('MAIL_USE_SSL'),
            }
            try:
                # Verifica via registry de extensões do Flask
                info['configured'] = bool(getattr(current_app, 'extensions', {}).get('mail'))
            except Exception:
                info['configured'] = False
            # Não tentamos autenticar no servidor aqui (evita bloquear); objetivo é mostrar se o Mail está ativo
            status = 200 if info['configured'] else 503
            return {'ok': info['configured'], 'details': info}, status

    # Debug-only endpoint para envio de e-mail (útil em dev)
    if app.config.get('FLASK_ENV') != 'production' and 'api_debug_send_mail' not in app.view_functions:
        @app.route('/api/debug/send-mail', methods=['POST'], endpoint='api_debug_send_mail')
        def debug_send_mail_ep():  # pragma: no cover (helper)
            from flask import request, jsonify, current_app
            from core.security import mail
            try:
                payload = request.get_json(force=True) or {}
            except Exception:
                return jsonify({'ok': False, 'error': 'JSON inválido'}), 400
            to = payload.get('to') or payload.get('email')
            subject = payload.get('subject') or 'Teste ASPMA'
            body = payload.get('body') or '<p>Mensagem de teste ASPMA.</p>'
            if not to:
                return jsonify({'ok': False, 'error': 'Campo to/email é obrigatório'}), 400
            configured = bool(getattr(current_app, 'extensions', {}).get('mail'))
            if not configured:
                strict = (current_app.config.get('MAIL_STRICT_MODE') or False)
                if isinstance(strict, str):
                    strict = strict.lower() in ('1','true','yes')
                if strict:
                    return jsonify({'ok': False, 'error': 'Envio de e-mail não configurado (MAIL_STRICT_MODE habilitado)'}), 400
                current_app.log_event('mail_noop', reason='mail_not_configured_debug')
                return jsonify({'ok': True, 'noop': True, 'message': 'Mail não configurado. Mensagem não enviada (dev).'}), 200
            try:
                from flask_mail import Message
                sender = (current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME') or 'no-reply@localhost')
                msg = Message(subject=subject, sender=sender, recipients=[to])
                msg.html = body
                mail.send(msg)
                current_app.log_event('mail_sent', to=to, debug=True)
                return jsonify({'ok': True, 'sent': True, 'to': to}), 200
            except Exception as e:
                current_app.log_event('mail_send_error', error=str(e.__class__.__name__))
                # Em dev, exponha a classe de erro para facilitar diagnóstico local
                env = (current_app.config.get('FLASK_ENV') or '').lower()
                if env != 'production':
                    return jsonify({'ok': False, 'error': f"Falha ao enviar e-mail ({e.__class__.__name__})"}), 400
                return jsonify({'ok': False, 'error': 'Falha ao enviar e-mail'}), 400

    return app

def register_legacy_routes(app):
    """
    Registra rotas legacy para manter compatibilidade durante migração.
    
    TODO: Remover após migração completa dos endpoints.
    """
    from flask_restful import Api
    
    # Criar API para recursos legacy
    legacy_api = Api(app, prefix='/legacy')
    
    # Importar classes legacy apenas se necessário
    try:
        from socios import UserLogin, Login_Extrato, Margem
        from convenios import LoginConvenio, Receber_Mensal
        
        # Registrar recursos legacy com prefixo para evitar conflito
        legacy_api.add_resource(UserLogin, '/socios/user-login')
        legacy_api.add_resource(Login_Extrato, '/socios/login-extrato-old') 
        legacy_api.add_resource(Margem, '/socios/margem-old')
        legacy_api.add_resource(LoginConvenio, '/convenios/login')
        legacy_api.add_resource(Receber_Mensal, '/convenios/receber-mensal')
        
        app.logger.info("Rotas legacy registradas com prefixo /legacy")
        
    except ImportError as e:
        app.logger.warning(f"Algumas rotas legacy não foram carregadas: {e}")

# Expor uma instância global para que `flask run` (auto-discovery) encontre a app
# Mesmo usando o padrão factory, isto evita 404 em /api/docs quando o usuário
# esquece de setar FLASK_APP=app_mvc:create_app. Testes continuam podendo
# instanciar apps isoladas chamando create_app() diretamente.
app = create_app()

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True  # Apenas para desenvolvimento
    )

# Debug-only endpoints (lightweight helpers)
@app.route('/api/debug/send-mail', methods=['POST'])
def debug_send_mail():  # pragma: no cover (helper)
    from flask import request, jsonify, current_app
    from core.security import mail
    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        return jsonify({'ok': False, 'error': 'JSON inválido'}), 400
    to = payload.get('to') or payload.get('email')
    subject = payload.get('subject') or 'Teste ASPMA'
    body = payload.get('body') or '<p>Mensagem de teste ASPMA.</p>'
    if not to:
        return jsonify({'ok': False, 'error': 'Campo to/email é obrigatório'}), 400
    # Verifica configuração do Flask-Mail
    configured = bool(getattr(mail, 'state', None) and getattr(mail.state, 'app', None))
    if not configured:
        # Respeita modo estrito
        strict = (current_app.config.get('MAIL_STRICT_MODE') or False)
        if isinstance(strict, str):
            strict = strict.lower() in ('1','true','yes')
        if strict:
            return jsonify({'ok': False, 'error': 'Envio de e-mail não configurado (MAIL_STRICT_MODE habilitado)'}), 400
        current_app.log_event('mail_noop', reason='mail_not_configured_debug')
        return jsonify({'ok': True, 'noop': True, 'message': 'Mail não configurado. Mensagem não enviada (dev).'}), 200
    # Envio real
    try:
        from flask_mail import Message
        msg = Message(
            subject=subject,
            sender=(current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME') or 'no-reply@localhost'),
            recipients=[to]
        )
        msg.html = body
        mail.send(msg)
        current_app.log_event('mail_sent', to=to, debug=True)
        return jsonify({'ok': True, 'sent': True, 'to': to}), 200
    except Exception as e:
        current_app.log_event('mail_send_error', error=str(e.__class__.__name__))
        return jsonify({'ok': False, 'error': 'Falha ao enviar e-mail'}), 400