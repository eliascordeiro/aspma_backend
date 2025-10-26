from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, get_jwt
from marshmallow import ValidationError

from core.exceptions import AppError, ValidationError as AppValidationError, AuthenticationError
from core.responses import success_response, error_response
from core.security import revoke_token
from .schemas import LoginExtratoSchema, ExtratoMesAnoSchema, CodigoCompraSchema
from .service import SociosService

socios_bp = Blueprint('socios', __name__, url_prefix='/api/socios')
login_extrato_schema = LoginExtratoSchema()
socios_service = SociosService()

@socios_bp.route('/login-extrato', methods=['POST'])
def login_extrato():
    """Login Extrato Sócio
    ---
    tags:
      - Socios
    consumes:
      - application/json
    parameters:
      - in: body
        name: credenciais
        required: true
        schema:
          type: object
          properties:
            matricula: {type: string}
            cpf: {type: string, description: 'Fragmento 5-6 dígitos'}
    responses:
      200: {description: Autenticado}
      400: {description: Erro de validação}
      401: {description: Não autenticado}
    """
    try:
        json_data = request.get_json()
        if not json_data:
            raise AppValidationError("Dados JSON obrigatórios")
        data = login_extrato_schema.load(json_data)
        login_result = socios_service.authenticate_extrato(data['matricula'], data['cpf'])
        response_data = {
            'matricula': login_result.socio.matricula,
            'nome': login_result.socio.associado,
            'email': login_result.socio.email,
            'celular': login_result.socio.celular,
            'bloqueio': login_result.socio.bloqueio,
            'tipo': login_result.socio.tipo,
            'mes_ano': login_result.mes_ano,
            'bloqueio_aspma': login_result.bloqueio_aspma,
            'cpfcnpj': login_result.socio.cpf or login_result.socio.matricula,
            'existe': 'X',
            'tokens': {
                'access_token': login_result.tokens['access_token'],
                'refresh_token': login_result.tokens['refresh_token']
            }
        }
        return success_response(data=response_data, message="Autenticação realizada com sucesso")
    except ValidationError as e:
        return error_response(message="Dados de entrada inválidos", details=e.messages, status_code=400)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except AuthenticationError as e:
        return error_response(message=str(e), code='AUTHENTICATION_ERROR', status_code=401)
    except Exception:
        return error_response(message="Erro interno no servidor", code='INTERNAL_ERROR', status_code=500)

@socios_bp.route('/margem', methods=['POST'])
@jwt_required()
def get_margem():
    """Calcula margem disponível do sócio autenticado.
    ---
    tags:
      - Socios
    security:
      - BearerAuth: []
    responses:
      200: {description: Margem calculada}
      401: {description: Não autorizado}
    """
    try:
        matricula = get_jwt_identity()
        result = socios_service.calcular_margem(matricula)
        if result.get('margem') is not None:
            from babel.numbers import format_decimal
            result['margem_formatada'] = format_decimal(result['margem'], format="#.##0,00", locale='pt_BR')
        return success_response(data=result, message="Margem calculada")
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except Exception:
        return error_response(message="Erro interno no cálculo de margem", code='INTERNAL_ERROR', status_code=500)


@socios_bp.route('/extrato', methods=['POST'])
@jwt_required()
def descontos_mensais():
    """Extrato de Descontos Mensais
    ---
    tags:
      - Socios
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
            mes_ano: {type: string, example: '2025-10'}
    responses:
      200: {description: Lista de descontos do mês}
      400: {description: Erro de validação}
      401: {description: Não autorizado}
    """
    try:
        payload = request.get_json(force=True) or {}
        schema = ExtratoMesAnoSchema()
        data = schema.load(payload)
        matricula = get_jwt_identity()
        resultado = socios_service.listar_descontos_mensais(matricula, data['mes_ano'])
        return success_response(data=resultado, message="Descontos mensais")
    except ValidationError as e:
        return error_response(message=str(e), code='VALIDATION_ERROR', status_code=400)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except Exception:
        return error_response(message="Erro interno ao listar descontos", code='INTERNAL_ERROR', status_code=500)


@socios_bp.route('/compras', methods=['POST'])
@jwt_required()
def compras_mensais():
    """Compras Mensais
    ---
    tags:
      - Socios
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
            mes_ano: {type: string, example: '2025-10'}
    responses:
      200: {description: Lista de compras do mês}
      400: {description: Erro de validação}
      401: {description: Não autorizado}
    """
    try:
        payload = request.get_json(force=True) or {}
        schema = ExtratoMesAnoSchema()
        data = schema.load(payload)
        matricula = get_jwt_identity()
        resultado = socios_service.listar_compras_mensais(matricula, data['mes_ano'])
        return success_response(data=resultado, message="Compras mensais")
    except ValidationError as e:
        return error_response(message=str(e), code='VALIDATION_ERROR', status_code=400)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except Exception:
        return error_response(message="Erro interno ao listar compras", code='INTERNAL_ERROR', status_code=500)


@socios_bp.route('/codigo-compra', methods=['POST'])
@jwt_required()
def gerar_codigo_compra():
    """Gerar Código de Compra
    ---
    tags:
      - Socios
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
            cpf: {type: string, description: 'Fragmento de CPF para verificação'}
            email: {type: string}
            celular: {type: string}
            nova_senha: {type: string, description: 'Opcional para redefinir senha'}
    responses:
      200: {description: Código gerado}
      400: {description: Erro de validação}
      401: {description: Autenticação inválida}
    """
    try:
        schema = CodigoCompraSchema()
        payload = request.get_json(force=True) or {}
        data = schema.load(payload)
        matricula = get_jwt_identity()
        result = socios_service.gerar_codigo_compra(
            matricula=matricula,
            senha=data['senha'],
            cpf_fragment=data['cpf'],
            email=data['email'],
            celular=data['celular'],
            nova_senha=data.get('nova_senha')
        )
        return success_response(data=result, message="Código gerado")
    except ValidationError as e:
        return error_response(message=str(e), code='VALIDATION_ERROR', status_code=400)
    except AuthenticationError as e:
        return error_response(message=str(e), code='AUTH_ERROR', status_code=401)
    except AppError as e:
        return error_response(message=str(e), code=e.code, status_code=e.status_code)
    except Exception:
        return error_response(message="Erro interno ao gerar código", code='INTERNAL_ERROR', status_code=500)


@socios_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    """Refresh Token
    ---
    tags:
      - Socios
    security:
      - BearerAuth: []
    responses:
      200: {description: Novo access token emitido}
      401: {description: Refresh inválido ou ausente}
    description: "Requer envio do refresh token válido no header Authorization: Bearer <refresh>"
    """
    try:
        identity = get_jwt_identity()
        new_access = create_access_token(identity=identity)
        return success_response(data={'access_token': new_access, 'token_type': 'Bearer'}, message='Token renovado')
    except Exception:
        return error_response(message='Não foi possível renovar token', code='TOKEN_REFRESH_ERROR', status_code=401)

@socios_bp.route('/logout', methods=['POST'])
@jwt_required(optional=True)
def logout():
    """Logout
    ---
    tags:
      - Socios
    security:
      - BearerAuth: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: refresh
        required: false
        schema:
          type: object
          properties:
            refresh_jti: {type: string, description: 'JTI do refresh para revogar'}
            refresh_exp: {type: integer, description: 'Timestamp expiração do refresh'}
    responses:
      200: {description: Logout efetuado}
    """
    try:
        claims = get_jwt()
        if claims:
            exp = claims.get('exp')
            jti = claims.get('jti')
            if jti and exp:
                revoke_token(jti, exp)
        payload = request.get_json(silent=True) or {}
        refresh_jti = payload.get('refresh_jti')
        refresh_exp = payload.get('refresh_exp')
        if refresh_jti and refresh_exp:
            revoke_token(refresh_jti, int(refresh_exp))
        return success_response(message='Logout efetuado', data={})
    except Exception:
        return error_response(message='Falha no logout', code='LOGOUT_ERROR', status_code=500)