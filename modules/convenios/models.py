from dataclasses import dataclass
from typing import Optional

@dataclass
class ConvenioLogin:
    codigo: str
    nome_razao: str
    fantasia: str
    usuario: str
    email: str
    cpf_cnpj: str
    desconto: float
    parcelas: int
    libera: str
    mes_ano: str
    senha_4_digitos: bool = False  # Flag para indicar senha insegura

@dataclass
class ParcelaResumo:
    periodo: str
    n_parcela: str
    id: int
    nome: str
    data: str
    parcelas: str
    valor: str

@dataclass
class CompraResumo:
    periodo: str
    data: str
    nome: str
    parcelas: str
    valor: str
    id: int
