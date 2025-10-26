class AppError(Exception):
    """Exceção base da aplicação."""
    
    def __init__(self, message: str, code: str = None, status_code: int = 400):
        self.message = message
        self.code = code or self.__class__.__name__.upper()
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(AppError):
    """Erro de validação de dados."""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, 'VALIDATION_ERROR', 422)

class AuthenticationError(AppError):
    """Erro de autenticação."""
    
    def __init__(self, message: str = "Credenciais inválidas"):
        super().__init__(message, 'AUTHENTICATION_ERROR', 401)

class AuthorizationError(AppError):
    """Erro de autorização."""
    
    def __init__(self, message: str = "Acesso negado"):
        super().__init__(message, 'AUTHORIZATION_ERROR', 403)

class NotFoundError(AppError):
    """Recurso não encontrado."""
    
    def __init__(self, message: str = "Recurso não encontrado"):
        super().__init__(message, 'NOT_FOUND', 404)

class DatabaseError(AppError):
    """Erro de banco de dados."""
    
    def __init__(self, message: str = "Erro interno do banco de dados"):
        super().__init__(message, 'DATABASE_ERROR', 500)

class RateLimitError(AppError):
    """Limite de taxa excedido."""
    
    def __init__(self, message: str = "Limite de requisições excedido"):
        super().__init__(message, 'RATE_LIMIT_EXCEEDED', 429)