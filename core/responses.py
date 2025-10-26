import uuid
from datetime import datetime
from flask import jsonify
from typing import Any, Dict, Optional

def _generate_request_id() -> str:
    """Gera um ID único para cada requisição."""
    return str(uuid.uuid4())[:8]

def _get_timestamp() -> str:
    """Retorna timestamp ISO 8601."""
    return datetime.utcnow().isoformat() + 'Z'

def success(data: Any = None, message: str = None, meta: Dict = None, status_code: int = 200):
    """Resposta padronizada para sucesso."""
    response_data = {
        'success': True,
        'data': data,
        'message': message,
        'meta': {
            'timestamp': _get_timestamp(),
            'request_id': _generate_request_id(),
            **(meta or {})
        }
    }
    return jsonify(response_data), status_code

def error(message: str, code: str = None, details: Any = None, meta: Dict = None, status_code: int = 400):
    """Resposta padronizada para erro."""
    response_data = {
        'success': False,
        'error': {
            'code': code or 'GENERIC_ERROR',
            'message': message,
            'details': details
        },
        'meta': {
            'timestamp': _get_timestamp(),
            'request_id': _generate_request_id(),
            **(meta or {})
        }
    }
    return jsonify(response_data), status_code

def paginated_response(items: list, total: int, page: int, per_page: int, **kwargs):
    """Resposta padronizada para listagens paginadas."""
    total_pages = (total + per_page - 1) // per_page
    
    meta = {
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }
    
    return success(data=items, meta=meta, **kwargs)

# Backward compatibility helpers

def success_response(data: Any = None, message: str = None, meta: Dict = None, status_code: int = 200):
    """Alias legacy para success."""
    return success(data=data, message=message, meta=meta, status_code=status_code)

def error_response(message: str, code: str = None, details: Any = None, meta: Dict = None, status_code: int = 400):
    """Alias legacy para error."""
    return error(message=message, code=code, details=details, meta=meta, status_code=status_code)