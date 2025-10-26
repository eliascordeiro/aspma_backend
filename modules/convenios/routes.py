from flask import Blueprint, request
from datetime import datetime
from pytz import timezone
import os
from werkzeug.exceptions import BadRequest
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from marshmallow import ValidationError

from core.responses import success_response, error_response
from flask_limiter.errors import RateLimitExceeded
from core.exceptions import AppError, AuthenticationError
from .schemas import (
  LoginConvenioSchema, MesAnoSchema,
  CodigoEmailSchema, AlterarSenhaCodigoSchema, AlterarSenhaEsqueceuSchema
)
from .service import ConveniosService
from core.security import limiter

convenios_bp = Blueprint('convenios', __name__, url_prefix='/api/convenios')
service = ConveniosService()
login_schema = LoginConvenioSchema()
mes_ano_schema = MesAnoSchema()
codigo_email_schema = CodigoEmailSchema()
alterar_senha_codigo_schema = AlterarSenhaCodigoSchema()
alterar_senha_esqueceu_schema = AlterarSenhaEsqueceuSchema()
from .schemas import LimiteRequestSchema, VendaSenhaSchema
limite_schema = LimiteRequestSchema()
venda_senha_schema = VendaSenhaSchema()
from marshmallow import Schema, fields, validate

class AutenticacaoAcaoSchema(Schema):
  senha = fields.Str(required=True)

class CadastroConvenioSchema(Schema):
  usuario = fields.Str(required=True, validate=validate.Length(min=3, max=20))
  email = fields.Email(required=True, validate=validate.Length(max=60))
  cpf_cnpj = fields.Str(required=True, validate=validate.Length(max=18))
  fantasia = fields.Str(required=True, validate=validate.Length(max=20))
  nome_razao = fields.Str(required=True, validate=validate.Length(max=40))

# Explicit OPTIONS handlers to avoid 405 in certain deployments/preflight scenarios
@convenios_bp.route('/limite', methods=['OPTIONS'])
def limite_options():  # pragma: no cover (infra/preflight)
  from flask import make_response
  return make_response('', 204)

@convenios_bp.route('/venda-senha', methods=['OPTIONS'])
def venda_senha_options():  # pragma: no cover (infra/preflight)
  from flask import make_response
  return make_response('', 204)

@convenios_bp.route('/compras', methods=['OPTIONS'])
def compras_options():  # pragma: no cover (infra/preflight)
  from flask import make_response
  return make_response('', 204)

@convenios_bp.route('/receber-mensais', methods=['OPTIONS'])
def receber_mensais_options():  # pragma: no cover (infra/preflight)
  from flask import make_response
  return make_response('', 204)

# Preflight for "esqueceu senha" endpoints (alguns servidores retornam 405 sem handler explícito)
@convenios_bp.route('/esqueceu/enviar-codigo', methods=['OPTIONS'])
def esqueceu_enviar_codigo_options():  # pragma: no cover (infra/preflight)
  from flask import make_response
  return make_response('', 204)

@convenios_bp.route('/esqueceu/alterar-senha', methods=['OPTIONS'])
def esqueceu_alterar_senha_options():  # pragma: no cover (infra/preflight)
  from flask import make_response
  return make_response('', 204)

class MailSender:
  def __init__(self):
    try:
      from flask_mail import Message
      from core.security import mail
      self._mail = mail
      self._Message = Message
    except Exception:
      # Sem Flask-Mail instalado ou sem configuração: mantém modo no-op
      self._mail = None
      class _DummyMsg:
        def __init__(self, *args, **kwargs):
          pass
      self._Message = _DummyMsg

  def send_codigo(self, email: str, codigo: str):
    try:
      # Se mail não estiver configurado (ex: dev/teste), não tentar enviar e retornar sucesso
      configured = False
      try:
        from flask import current_app
        configured = bool(getattr(current_app, 'extensions', {}).get('mail'))
      except Exception:
        configured = bool(self._mail)
      if not configured:
        try:
          from flask import current_app
          current_app.log_event('mail_noop', reason='mail_not_configured')
        except Exception:
          pass
        # Modo estrito: se habilitado, falhar em vez de no-op
        strict = False
        try:
          from flask import current_app
          strict_cfg = current_app.config.get('MAIL_STRICT_MODE')
          if isinstance(strict_cfg, str):
            strict = strict_cfg.lower() in ('1','true','yes')
          else:
            strict = bool(strict_cfg)
        except Exception:
          strict = os.getenv('MAIL_STRICT_MODE', 'false').lower() in ('1','true','yes')
        if strict:
            raise AuthenticationError('Envio de e-mail não configurado (MAIL_STRICT_MODE habilitado)')
        return True
      # Determina o remetente a partir da configuração
      sender = None
      try:
        from flask import current_app
        sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
      except Exception:
        sender = os.getenv('MAIL_DEFAULT_SENDER') or os.getenv('MAIL_USERNAME')
      if not sender:
        sender = 'no-reply@localhost'
      msg = self._Message(
        subject='Código de Segurança A.S.P.M.A.',
        sender=sender,
        recipients=[email]
      )
      msg.html = f"<p style='font-size:22px'>INFORME ESTE CÓDIGO QUANDO SOLICITADO: {codigo}</p>"
      try:
        self._mail.send(msg)
      except Exception as send_err:
        # Em alguns servidores, o e-mail pode ser aceito mas a conexão cair no pós-DATA.
        # Quando MAIL_STRICT_MODE=false (default em dev), tratamos como sucesso e logamos.
        strict = False
        try:
          from flask import current_app
          strict_cfg = current_app.config.get('MAIL_STRICT_MODE')
          if isinstance(strict_cfg, str):
            strict = strict_cfg.lower() in ('1','true','yes')
          else:
            strict = bool(strict_cfg)
        except Exception:
          strict = os.getenv('MAIL_STRICT_MODE', 'false').lower() in ('1','true','yes')
        if strict:
          # Converter para AuthenticationError para a camada superior padronizar
          raise AuthenticationError('Falha ao enviar e-mail')
        try:
          from flask import current_app
          current_app.log_event('mail_send_warning', to=email, error=str(send_err))
        except Exception:
          pass
      try:
        from flask import current_app
        current_app.log_event('mail_sent', to=email)
      except Exception:
        pass
      return True
    except Exception:
      # Converter qualquer falha em AuthenticationError para padronização na camada de serviço
      try:
        from flask import current_app
        strict_cfg = current_app.config.get('MAIL_STRICT_MODE')
        strict = False
        if isinstance(strict_cfg, str):
          strict = strict_cfg.lower() in ('1','true','yes')
        else:
          strict = bool(strict_cfg)
        if not strict:
          # Em modo não estrito, trate como sucesso silencioso
          return True
      except Exception:
        # Se não conseguir ler configuração, use env var e mantenha padrão não estrito
        if os.getenv('MAIL_STRICT_MODE', 'false').lower() not in ('1','true','yes'):
          return True
      raise AuthenticationError('Falha ao enviar e-mail')


def _current_convenio_identity():
    """Recupera o payload completo de identidade do convênio.

    Com a mudança em `generate_tokens`, quando o identity é um dict ele passa a ser
    armazenado em um claim custom 'identity' e `sub` vira apenas o código string.
    Este helper centraliza a extração, mantendo fallback para tokens antigos
    (onde o dict ainda vinha como identity direto em `sub`).
    """
    claims = get_jwt()
    ident_claim = claims.get('identity') if isinstance(claims, dict) else None
    if isinstance(ident_claim, dict):
        return ident_claim
    legacy = get_jwt_identity()
    if isinstance(legacy, dict):
        return legacy
    return {'codigo': legacy}

@convenios_bp.route('/login', methods=['POST'])
def login_convenio():
  """Login Convênio

  Autentica um convênio e retorna tokens JWT + dados básicos.

  Modo Fake (apenas desenvolvimento):
    - Ativado quando ENABLE_FAKE_LOGIN=true e a senha enviada é __dev__.
    - Retorna tokens contendo claim custom "fake": true e meta.fake_login=true.
    - Não utilizar em produção.

  Campos alternativos (entrada): usuario | user | username | login | codigo | cnpj
  Senha pode vir como: senha | password | pass | senha_convenio | pwd
  Aceita também formato legacy: {"dados": {"usuario":..., "senha":...}}
  ---
  tags:
    - Convenios
  consumes:
    - application/json
  parameters:
    - in: body
    name: credenciais
    required: true
    schema:
      type: object
      properties:
      usuario: {type: string, example: "LOJA01"}
      senha: {type: string, example: "secreta"}
  responses:
    200: {description: Sucesso}
    400: {description: Dados inválidos}
    401: {description: Falha de autenticação}
    503: {description: Serviço temporariamente indisponível}
  """
  try:
    payload = request.get_json(force=True) or {}
    raw_keys = list(payload.keys())

    if 'dados' in payload and isinstance(payload['dados'], dict):
      legacy = payload['dados']
      if 'usuario' not in payload and 'usuario' in legacy and 'senha' in legacy:
        payload = legacy

    if 'usuario' not in payload:
      for alt in ('user', 'username', 'login', 'codigo', 'cnpj'):
        if alt in payload and isinstance(payload[alt], str):
          payload['usuario'] = payload[alt]
          break

    if 'senha' not in payload:
      for alt in ('password', 'pass', 'senha_convenio', 'pwd'):
        if alt in payload and isinstance(payload[alt], str):
          payload['senha'] = payload[alt]
          break

    try:
      from flask import current_app
      current_app.log_event('login_convenio_payload_normalized', raw_keys=raw_keys, normalized_keys=list(payload.keys()))
    except Exception:
      pass

    data = login_schema.load({k: v for k, v in payload.items() if k in ('usuario', 'senha')})
    conv, tokens = service.autenticar(data['usuario'], data['senha'])
    meta_extra = {'fake_login': True} if tokens.get('fake') else None
    return success_response(
      data={
        'tokens': tokens,
        'dados': {
          'codigo': conv.codigo,
          'nome_razao': conv.nome_razao,
          'usuario': conv.usuario,
          'email': conv.email,
          'cpf_cnpj': conv.cpf_cnpj,
          'fantasia': conv.fantasia,
          'desconto': conv.desconto,
          'parcelas': conv.parcelas,
          'libera': conv.libera,
          'mes_ano': conv.mes_ano
        }
      },
      meta=meta_extra,
      message='Login convênio ok'
    )
  except ValidationError as e:
    try:
      from flask import current_app
      current_app.log_event('login_convenio_validation_error', details=e.messages)
    except Exception:
      pass
    return error_response(message='Dados inválidos', code='VALIDATION_ERROR', details=e.messages, status_code=400)
  except AuthenticationError as e:
    try:
      from flask import current_app
      current_app.log_event('login_convenio_auth_error', message=str(e))
    except Exception:
      pass
    return error_response(message=str(e), code='AUTH_ERROR', status_code=401)
  except AppError as e:
    try:
      from flask import current_app
      current_app.log_event('login_convenio_app_error', code=e.code, status=e.status_code)
    except Exception:
      pass
    return error_response(message=str(e), code=e.code, status_code=e.status_code)
  except Exception:
    try:
      from flask import current_app
      current_app.log_event('login_convenio_internal_error')
    except Exception:
      pass
    return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)


@convenios_bp.route('/autenticacao', methods=['POST'])
@jwt_required()
def autenticacao_acao():
    """Autenticação de ação (confirmar senha)
    ---
    tags:
      - Convenios
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: dados
        required: true
        schema:
          type: object
          properties:
            senha: {type: string}
    responses:
      200: {description: Autenticado}
      400: {description: Dados inválidos}
      401: {description: Falha de autenticação}
    """
    try:
        payload = request.get_json(force=True) or {}
        # Aceita formato legacy { dados: { senha } }
        if 'dados' in payload and isinstance(payload['dados'], dict) and 'senha' not in payload:
            payload = payload['dados']
        schema = AutenticacaoAcaoSchema()
        data = schema.load(payload)
        ident = _current_convenio_identity()
        # Bypass de desenvolvimento opcional via flag de ambiente
        try:
            allow_bypass = os.getenv('ALLOW_DEV_ACTION_BYPASS', 'false').lower() in ('1','true','yes')
        except Exception:
            allow_bypass = False
        if allow_bypass:
            return success_response(data={'msg': 'ok'}, message='Autenticado (dev bypass)')
        # Modo fake: tokens gerados com claim 'fake' permitem sucesso direto em dev
        try:
            claims = get_jwt()
            if isinstance(claims, dict) and claims.get('fake'):
                return success_response(data={'msg': 'ok'}, message='Autenticado (fake)')
        except Exception:
            pass
        codigo = ident['codigo']
        service.autenticar_acao(codigo, data['senha'])
        # manter compat de resposta com legado
        return success_response(data={'msg': 'ok'}, message='Autenticado')
    except ValidationError as e:
        return error_response(message='Dados inválidos', details=e.messages, status_code=400)
    except AuthenticationError as e:
        return error_response(message=str(e), code='AUTH_ERROR', status_code=401)
    except BadRequest:
        return error_response(message='JSON inválido', code='INVALID_JSON', status_code=400)
    except Exception:
        return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)


@convenios_bp.errorhandler(RateLimitExceeded)
def handle_ratelimit(exc):  # pragma: no cover (difícil de simular todas janelas)
    return error_response(message='Limite de requisições excedido', code='RATE_LIMIT', status_code=429)

@convenios_bp.route('/parcelas', methods=['POST'])
@jwt_required()
def parcelas_mensal():
    """Lista parcelas do mês para o convênio autenticado.
    ---
    tags:
      - Convenios
    security:
      - BearerAuth: []
    responses:
      200: {description: Parcelas retornadas}
      401: {description: Não autorizado}
    """
    try:
        payload = request.get_json(force=True) or {}
        data = mes_ano_schema.load(payload)
        ident = _current_convenio_identity()
        codigo = ident['codigo']
        res = service.listar_parcelas(codigo, data['mes_ano'])
        return success_response(data=res, message='Parcelas convênio')
    except ValidationError as e:
        return error_response(message='Dados inválidos', details=e.messages, status_code=400)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except Exception:
        return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)

@convenios_bp.route('/compras', methods=['POST'])
@jwt_required()
def compras_mensal():
    """Compras Mensais do Convênio
    ---
    tags:
      - Convenios
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: filtro
        required: true
        schema:
          type: object
          properties:
            mes_ano: {type: string, example: '10-2025'}
    responses:
      200: {description: Lista de compras do mês}
      400: {description: Dados inválidos}
      401: {description: Não autorizado}
    """
    try:
        payload = request.get_json(force=True) or {}
        data = mes_ano_schema.load(payload)
        ident = _current_convenio_identity()
        codigo = ident['codigo']
        res = service.listar_compras(codigo, data['mes_ano'])
        return success_response(data=res, message='Compras convênio')
    except ValidationError as e:
        return error_response(message='Dados inválidos', details=e.messages, status_code=400)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except Exception:
        return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)

@convenios_bp.route('/receber-mensais', methods=['POST'])
@jwt_required()
def receber_mensais():
    """Extrato de recebimentos (parcelas) com totais de desconto e receber
    ---
    tags:
      - Convenios
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: filtro
        required: true
        schema:
          type: object
          properties:
            mes_ano: {type: string, example: '10-2025'}
    responses:
      200: {description: Lista de parcelas + totais}
      400: {description: Dados inválidos}
      401: {description: Não autorizado}
    """
    try:
        payload = request.get_json(force=True) or {}
        data = mes_ano_schema.load(payload)
        ident = _current_convenio_identity()
        codigo = ident['codigo']
        res = service.listar_receber_mensais(codigo, data['mes_ano'])
        return success_response(data=res, message='Extrato convênio')
    except ValidationError as e:
        return error_response(message='Dados inválidos', details=e.messages, status_code=400)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except Exception:
        return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)

@convenios_bp.route('/enviar-codigo', methods=['POST'])
@jwt_required()
@limiter.limit(
  "5/hour;2/minute",
  key_func=lambda: f"{request.remote_addr or 'ip'}:{(request.get_json(silent=True) or {}).get('email','')}"
)
def enviar_codigo_email():
    """Enviar Código de Segurança (Convênio logado)
    ---
    tags:
      - Convenios
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: email
        required: true
        schema:
          type: object
          properties:
            email: {type: string, format: email}
    responses:
      200: {description: Código enviado}
      400: {description: Dados inválidos}
      401: {description: Não autorizado / Falha de autenticação}
      429: {description: Rate limit excedido}
    """
    try:
        payload = request.get_json(force=True) or {}
        data = codigo_email_schema.load(payload)
        try:
            from flask import current_app
            current_app.log_event('convenios_enviar_codigo_request', email=data.get('email'))
        except Exception:
            pass
        ident = _current_convenio_identity()
        codigo = ident['codigo']
        # Em desenvolvimento, se o token for fake OU se a flag ALLOW_DEV_EMAIL_ANY=true, permite bypass
        allow_bypass = False
        try:
            claims = get_jwt()
            allow_bypass = bool(isinstance(claims, dict) and claims.get('fake'))
        except Exception:
            allow_bypass = False
        # Bypass adicional por flag de ambiente (mesmo sem token fake)
        env_bypass = os.getenv('ALLOW_DEV_EMAIL_ANY', 'false').lower() in ('1','true','yes')
        allow_bypass = allow_bypass or env_bypass
        if allow_bypass:
            try:
                from flask import current_app
                current_app.log_event('convenios_enviar_codigo_bypass_dev', codigo=codigo, email=data['email'], reason='fake-claim-or-env')
            except Exception:
                pass
        service.gerar_codigo_email(codigo, data['email'], MailSender(), allow_dev_bypass=allow_bypass)
        return success_response(message='Código enviado')
    except ValidationError as e:
        return error_response(message='Dados inválidos', details=e.messages, status_code=400)
    except AuthenticationError as e:
        return error_response(message=str(e), code='AUTH_ERROR', status_code=400)
    except BadRequest:
        return error_response(message='JSON inválido', code='INVALID_JSON', status_code=400)
    except Exception:
        try:
            from flask import current_app
            current_app.log_event('convenios_enviar_codigo_internal_error')
        except Exception:
            pass
        return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)

@convenios_bp.route('/alterar-senha-codigo', methods=['POST'])
@jwt_required()
def alterar_senha_codigo():
    """Alterar Senha (Convênio autenticado com código recebido)
    ---
    tags:
      - Convenios
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: payload
        required: true
        schema:
          type: object
          properties:
            codigo: {type: string, description: 'Código de verificação (6 dígitos)'}
            nova_senha: {type: string}
    responses:
      200: {description: Senha alterada}
      400: {description: Dados inválidos}
      401: {description: Não autorizado / Falha de autenticação}
    """
    try:
        payload = request.get_json(force=True) or {}
        data = alterar_senha_codigo_schema.load(payload)
        ident = _current_convenio_identity()
        codigo_convenio = ident['codigo']
        service.alterar_senha_codigo(codigo_convenio, data['codigo'], data['nova_senha'])
        return success_response(message='Senha alterada')
    except ValidationError as e:
        return error_response(message='Dados inválidos', details=e.messages, status_code=400)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except AuthenticationError as e:
        return error_response(message=str(e), code='AUTH_ERROR', status_code=401)
    except Exception:
        return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)

@convenios_bp.route('/esqueceu/enviar-codigo', methods=['POST'])
@limiter.limit(
  "3/hour;2/10minute",
  key_func=lambda: f"{request.remote_addr or 'ip'}:{(request.get_json(silent=True) or {}).get('email','')}"
)
def esqueceu_enviar_codigo():
    """Esqueceu a Senha - Enviar Código por E-mail
    ---
    tags:
      - Convenios
    consumes:
      - application/json
    parameters:
      - in: body
        name: email
        required: true
        schema:
          type: object
          properties:
            email: {type: string, format: email}
    responses:
      200: {description: Código enviado}
      400: {description: Dados inválidos}
      429: {description: Rate limit excedido}
    """
    try:
        payload = request.get_json(force=True) or {}
        # Aceita formato legacy { dados: { email } }
        if 'dados' in payload and isinstance(payload['dados'], dict) and 'email' in payload['dados'] and 'email' not in payload:
            payload = payload['dados']
        data = codigo_email_schema.load(payload)
        try:
            from flask import current_app
            current_app.log_event('convenios_esqueceu_enviar_codigo_request', email=data.get('email'))
        except Exception:
            pass
        service.solicitar_codigo_esqueceu(data['email'], MailSender())
        return success_response(message='Código enviado')
    except ValidationError as e:
        return error_response(message='Dados inválidos', details=e.messages, status_code=400)
    except AuthenticationError as e:
        # Em modo não estrito, tratamos falha de envio como sucesso (evitar bloquear UX em dev)
        try:
            from flask import current_app
            strict_cfg = current_app.config.get('MAIL_STRICT_MODE')
            strict = False
            if isinstance(strict_cfg, str):
                strict = strict_cfg.lower() in ('1','true','yes')
            else:
                strict = bool(strict_cfg)
            if not strict and str(e).lower().startswith('falha ao enviar e-mail'):
                try:
                    current_app.log_event('mail_send_dev_override', reason='non_strict_mode')
                except Exception:
                    pass
                return success_response(message='Código enviado')
        except Exception:
            # Se não for possível ler config e não é produção, ainda assim evitar bloquear
            env = os.getenv('FLASK_ENV','development').lower()
            if env != 'production' and str(e).lower().startswith('falha ao enviar e-mail'):
                return success_response(message='Código enviado')
        # Outros erros (e-mail não encontrado, etc.) retornam 400
        return error_response(message=str(e), code='AUTH_ERROR', status_code=400)
    except BadRequest:
        return error_response(message='JSON inválido', code='INVALID_JSON', status_code=400)
    except Exception as e:
        # Log interno pode ser adicionado; retorna 500 genérico
        try:
            from flask import current_app
            current_app.log_event('convenios_esqueceu_enviar_codigo_internal_error', error=str(e))
        except Exception:
            pass
        return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)

@convenios_bp.route('/esqueceu/alterar-senha', methods=['POST'])
def esqueceu_alterar_senha():
    """Esqueceu a Senha - Alterar com Código
    ---
    tags:
      - Convenios
    consumes:
      - application/json
    parameters:
      - in: body
        name: payload
        required: true
        schema:
          type: object
          properties:
            codigo: {type: string}
            nova_senha: {type: string}
    responses:
      200: {description: Senha alterada}
      400: {description: Dados inválidos}
      401: {description: Falha de autenticação}
    """
    try:
        payload = request.get_json(force=True) or {}
        data = alterar_senha_esqueceu_schema.load(payload)
        service.alterar_senha_esqueceu(data['codigo'], data['nova_senha'])
        return success_response(message='Senha alterada')
    except ValidationError as e:
        return error_response(message='Dados inválidos', details=e.messages, status_code=400)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except AuthenticationError as e:
        # Código inválido não é 500 — sinalize de forma clara
        return error_response(message=str(e), code='AUTH_ERROR', status_code=400)
    except Exception:
        return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)

@convenios_bp.route('/limite', methods=['POST'])
@jwt_required()
def limite_convenio():
    """Calcular Limite para Matrícula
    ---
    tags:
      - Convenios
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: dados
        required: true
        schema:
          type: object
          properties:
            matricula: {type: string}
            valor: {type: string, description: 'Valor pretendido'}
            nr_parcelas: {type: integer}
    responses:
      200:
        description: Limite calculado
        schema:
          type: object
          properties:
            ok: {type: boolean}
            msg:
              type: object
              description: Envelope com dados do limite
              properties:
                id_compra: {type: string}
                phone_mask: {type: string}
                whatsapp_sent: {type: boolean}
      400: {description: Dados inválidos}
      401: {description: Não autorizado}
    """
    try:
        payload = request.get_json(force=True) or {}
        data = limite_schema.load(payload)
        ident = _current_convenio_identity()  # auditoria futura
        resp = service.calcular_limite(data['matricula'], data['valor'], data['nr_parcelas'])
        return success_response(data=resp, message='Limite calculado')
    except ValidationError as e:
        return error_response(message='Dados inválidos', details=e.messages, status_code=400)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except Exception:
        return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)

@convenios_bp.route('/venda-senha', methods=['POST'])
@jwt_required()
def venda_senha():
    """Registrar Venda utilizando Senha
    ---
    tags:
      - Convenios
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: venda
        required: true
        schema:
          type: object
          properties:
            matricula: {type: string}
            valor: {type: string}
            nr_parcelas: {type: integer}
            tipo: {type: string}
            sequencia: {type: integer}
            mes: {type: integer}
            ano: {type: integer}
            saldo: {type: number}
            cpf: {type: string}
            matricula_atual: {type: string}
            celular: {type: string}
            associado: {type: string}
    responses:
      200: {description: Venda registrada}
      400: {description: Dados inválidos}
      401: {description: Não autorizado}
    """
    try:
        payload = request.get_json(force=True) or {}
        data = venda_senha_schema.load(payload)
        ident = _current_convenio_identity()
        codigo = ident['codigo']
        nome = ident.get('nome_razao','')
        usuario = ident.get('usuario','')
        service.registrar_venda_senha(data, codigo, nome, usuario)
        # Expõe status do WhatsApp pós-venda (se disponível) e um carimbo de data/hora confiável do servidor
        now_sp = datetime.now(timezone('America/Sao_Paulo'))
        extra = {
          'whatsapp_confirm_sent': bool(getattr(service, '_last_whatsapp_sent_post', False)),
          'phone_mask': getattr(service, '_last_phone_mask_post', None),
          # Campo confiável de data da compra (servidor). Frontend formata em dd/mm/aaaa
          'data_compra': now_sp.isoformat()
        }
        return success_response(data=extra, message='Venda registrada')
    except ValidationError as e:
        return error_response(message='Dados inválidos', details=e.messages, status_code=400)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except Exception:
        return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)

@convenios_bp.route('/cadastro', methods=['POST'])
@jwt_required()
def atualizar_cadastro():
    """Atualizar cadastro do convênio
    ---
    tags:
      - Convenios
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: dados
        required: true
        schema:
          type: object
          properties:
            usuario: {type: string}
            email: {type: string}
            cpf_cnpj: {type: string}
            fantasia: {type: string}
            nome_razao: {type: string}
    responses:
      200: {description: Cadastro atualizado}
      400: {description: Dados inválidos}
      401: {description: Não autorizado}
    """
    try:
        payload = request.get_json(force=True) or {}
        data = CadastroConvenioSchema().load(payload)
        ident = _current_convenio_identity()
        codigo = ident['codigo']
        res = service.atualizar_cadastro(codigo, data)
        return success_response(data=res, message='Cadastro atualizado')
    except ValidationError as e:
        return error_response(message='Dados inválidos', details=e.messages, status_code=400)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except Exception:
        return error_response(message='Erro interno', code='INTERNAL_ERROR', status_code=500)
