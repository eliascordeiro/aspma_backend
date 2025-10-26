from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token
import os
try:  # Redis opcional
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    redis = None
"""Security & auth initialization utilities.

This module now tolerates absence of the optional dependency `flask-limiter`.
If the package is missing (e.g. virtualenv não ativado), a DummyLimiter is
used so that the application can still subir sem quebrar imediatamente,
facilitando diagnosticar o problema de ambiente. Rate limiting simplesmente
fica inoperante nesse modo.
Também é possível DESATIVAR rate limiting em desenvolvimento com variáveis de
ambiente: defina DISABLE_RATE_LIMIT=true ou FLASK_ENV=development.
"""

# DummyLimiter sempre disponível para uso como fallback ou quando desabilitado
class DummyLimiter:  # pragma: no cover - comportamento simples
    def __init__(self, *_, **__):
        pass

    def init_app(self, app):
        msg = 'Rate limiting DESATIVADO (DummyLimiter ativo).'
        try:
            app.logger.warning(msg)
        except Exception:
            pass

    def limit(self, *_, **__):
        def decorator(fn):
            return fn
        return decorator

try:  # Rate limiter opcional
    from flask_limiter import Limiter  # type: ignore
    from flask_limiter.util import get_remote_address  # type: ignore
except ImportError:  # pragma: no cover
    Limiter = None  # type: ignore

    def get_remote_address():  # type: ignore
        return None
    # For compatibility downstream we still expose a 'Limiter'-like instance pattern
    # but only after instantiation below (see "limiter = ...").
from flask_cors import CORS
from flask_mail import Mail
from datetime import timedelta
from typing import Dict, Any

# Instâncias globais das extensões
jwt = JWTManager()

# Desabilitar rate limiting em dev ou via env
_disable_rl = os.getenv('DISABLE_RATE_LIMIT', '').lower() in ('1', 'true', 'yes') \
    or os.getenv('FLASK_ENV', '').lower() == 'development'

limiter = Limiter(key_func=get_remote_address) if (Limiter and not _disable_rl) else DummyLimiter()
cors = CORS()
mail = Mail()

_revoked_tokens = {}
_redis_client = None

def _init_redis_if_configured(app):
    global _redis_client
    url = app.config.get('TOKEN_BLOCKLIST_REDIS_URL') or os.getenv('TOKEN_BLOCKLIST_REDIS_URL')
    if url and redis:
        try:
            _redis_client = redis.from_url(url, decode_responses=True)
            _redis_client.ping()
            app.logger.info('Redis blocklist ativo')
        except Exception as e:  # pragma: no cover
            app.logger.warning(f'Falha ao conectar Redis blocklist: {e}. Usando memória.')
            _redis_client = None

def _cleanup_revoked(now_ts: int):
    if _redis_client:
        return  # Redis gerencia TTL
    expired = [k for k, exp in _revoked_tokens.items() if exp < now_ts]
    for k in expired:
        _revoked_tokens.pop(k, None)

def revoke_token(jti: str, exp_timestamp: int):
    """Registra revogação de um token (memória ou Redis)."""
    if _redis_client:
        ttl = max(exp_timestamp - int(__import__('time').time()), 1)
        _redis_client.setex(f'blk:{jti}', ttl, '1')
    else:
        _revoked_tokens[jti] = exp_timestamp
        from time import time
        if len(_revoked_tokens) % 50 == 0:
            _cleanup_revoked(int(time()))

def is_token_revoked(jti: str) -> bool:
    if _redis_client:
        return _redis_client.exists(f'blk:{jti}') == 1
    from time import time
    _cleanup_revoked(int(time()))
    return jti in _revoked_tokens

def init_security_extensions(app):
    """Inicializa extensões de segurança."""
    
    # JWT Configuration
    jwt.init_app(app)
    
    # CORS Configuration  
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', ['*']),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Rate Limiter (opcional)
    if limiter:
        try:
            limiter.init_app(app)
        except Exception as e:  # pragma: no cover
            app.logger.warning(f'Falha ao inicializar rate limiter: {e}')
    
    # Mail
    mail.init_app(app)

    # Redis init para blocklist
    _init_redis_if_configured(app)

    # JWT blocklist (revogação)
    @jwt.token_in_blocklist_loader
    def check_token_revoked(jwt_header, jwt_payload):  # pragma: no cover (callback)
        jti = jwt_payload.get('jti')
        return is_token_revoked(jti)

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):  # pragma: no cover
        return ({'error': 'Token revogado', 'code': 'TOKEN_REVOKED'}, 401)

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):  # pragma: no cover
        return ({'error': 'Token expirado', 'code': 'TOKEN_EXPIRED'}, 401)

    @jwt.invalid_token_loader
    def invalid_token_callback(err):  # pragma: no cover
        return ({'error': 'Token inválido', 'code': 'TOKEN_INVALID'}, 422)

    @jwt.unauthorized_loader
    def missing_token_callback(err):  # pragma: no cover
        return ({'error': 'Credenciais ausentes', 'code': 'TOKEN_MISSING'}, 401)

# Backward compatibility alias
init_security = init_security_extensions

def generate_tokens(identity: Any, additional_claims: Dict = None) -> Dict[str, str]:
    """Gera tokens JWT padronizados.

    Se identity for um dict (ex: convenios), o campo padrão 'sub' deve ser string
    para evitar InvalidSubjectError (PyJWT exige string). Nesse caso colocamos o
    valor principal (ex: codigo) em 'sub' e armazenamos o payload completo em um
    claim custom 'identity'. Para identity simples (string/int) mantemos direto.
    """
    extra_claims = additional_claims.copy() if additional_claims else {}
    real_identity = identity
    if isinstance(identity, dict):
        codigo = identity.get('codigo') or identity.get('id') or 'unknown'
        extra_claims['identity'] = identity
        real_identity = str(codigo)

    access_token = create_access_token(identity=real_identity, additional_claims=extra_claims)
    refresh_token = create_refresh_token(identity=real_identity, additional_claims=extra_claims)
    result = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer'
    }
    if 'fake' in extra_claims:
        result['fake'] = True
    return result