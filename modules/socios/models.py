from datetime import datetime
from typing import Optional

class Socio:
    """Entidade de domínio representando um sócio/associado."""
    
    def __init__(self, matricula: str, associado: str, email: str = None, 
                 celular: str = None, bloqueio: str = None, tipo: str = None,
                 cpf: str = None, nascimento: datetime = None):
        self.matricula = matricula
        self.associado = associado
        self.email = email
        self.celular = celular
        self.bloqueio = bloqueio
        self.tipo = tipo
        self.cpf = cpf
        self.nascimento = nascimento
    
    @classmethod
    def from_row(cls, row) -> Optional['Socio']:
        """Cria instância a partir de row do banco de dados."""
        if not row:
            return None
        
        return cls(
            matricula=str(row[0]) if row[0] else None,
            associado=row[1] if len(row) > 1 else None,
            email=row[2] if len(row) > 2 else None,
            celular=row[3] if len(row) > 3 else None,
            bloqueio=row[4] if len(row) > 4 else None,
            tipo=row[5] if len(row) > 5 else None,
        )
    
    def is_blocked(self) -> bool:
        """Verifica se o sócio está bloqueado."""
        return self.bloqueio and self.bloqueio.upper() in ('X', 'SIM', 'TRUE', '1')
    
    def to_dict(self) -> dict:
        """Converte para dicionário para serialização."""
        return {
            'matricula': self.matricula,
            'associado': self.associado,
            'email': self.email,
            'celular': self.celular,
            'bloqueio': self.bloqueio,
            'tipo': self.tipo,
            'cpf': self.cpf,
            'nascimento': self.nascimento.isoformat() if self.nascimento else None
        }
    
    def validate_cpf_fragment(self, full_cpf: str, fragment: str) -> bool:
        """Valida um fragmento do CPF em relação ao CPF completo."""
        if not full_cpf or not fragment:
            return False
        digits = ''.join(c for c in full_cpf if c.isdigit())
        if len(digits) < 11 or len(fragment) != 6:
            return False
        expected = digits[:3] + digits[-2:]
        return expected == fragment

class LoginResult:
    """Resultado de um processo de autenticação."""
    
    def __init__(self, socio: Socio, tokens: dict, bloqueio_aspma: str = None, 
                 mes_ano: str = None):
        self.socio = socio
        self.tokens = tokens
        self.bloqueio_aspma = bloqueio_aspma
        self.mes_ano = mes_ano
    
    def to_legacy_format(self) -> dict:
        """Converte para o formato legacy esperado pelo frontend."""
        return {
            'cpfcnpj': self.socio.cpf or self.socio.matricula,
            'access_token': self.tokens['access_token'],
            'refresh_token': self.tokens['refresh_token'],
            'nomerazao': self.socio.associado,
            'existe': 'X',
            'email': self.socio.email,
            'celular': self.socio.celular,
            'bloqueio': self.socio.bloqueio,
            'tipo': self.socio.tipo,
            'bloqueio_aspma': self.bloqueio_aspma,
            'mes_ano': self.mes_ano
        }