from typing import Optional
from config.database import DatabaseManager
from core.exceptions import DatabaseError, NotFoundError
from .models import Socio

class SociosRepository:
    """Repository para operações de dados de sócios."""
    
    def __init__(self):
        pass
    
    def find_by_matricula_cpf(self, matricula: str, cpf_fragment: str) -> Optional[Socio]:
        """
        Busca sócio por matrícula e fragmento de CPF de forma segura.
        
        Args:
            matricula: Número da matrícula
            cpf_fragment: Fragmento do CPF (primeiros 3 + últimos 2 dígitos)
        
        Returns:
            Socio encontrado ou None
        """
        query = """
        SELECT 
            socios.matricula, 
            socios.associado, 
            socios.email, 
            socios.celular, 
            socios.bloqueio, 
            socios.tipo 
        FROM socios 
        WHERE socios.matricula = %s 
        AND RIGHT(socios.cpf, 2) = %s 
        AND SUBSTR(socios.cpf, 9, 3) = %s
        """
        
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    # Extrai fragmentos do CPF de forma segura
                    cpf_last_2 = cpf_fragment[-2:] if len(cpf_fragment) >= 2 else ''
                    cpf_first_3 = cpf_fragment[:3] if len(cpf_fragment) >= 3 else ''
                    
                    cursor.execute(query, (matricula, cpf_last_2, cpf_first_3))
                    row = cursor.fetchone()
                    
                    return Socio.from_row(row) if row else None
                    
        except Exception as e:
            raise DatabaseError(f"Erro ao buscar sócio: {str(e)}")
    
    def get_bloqueio_aspma(self, matricula: str) -> Optional[str]:
        """
        Busca status de bloqueio ASPMA de um sócio.
        
        Args:
            matricula: Número da matrícula
            
        Returns:
            Status de bloqueio ou None
        """
        query = "SELECT socios.bloqueio FROM socios WHERE socios.matricula = %s"
        
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (matricula,))
                    row = cursor.fetchone()
                    
                    return row[0] if row else None
                    
        except Exception as e:
            raise DatabaseError(f"Erro ao buscar bloqueio ASPMA: {str(e)}")

    def fetch_login_row(self, matricula: str, cpf_fragment: str):
        """Retorna linha crua para compatibilidade com formato legacy."""
        query = (
            "SELECT socios.matricula, socios.associado, socios.email, socios.celular, socios.bloqueio, socios.tipo, socios.cpf "
            "FROM socios WHERE socios.matricula = %s AND RIGHT(socios.cpf,2) = %s AND SUBSTR(socios.cpf,9,3) = %s"
        )
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    last2 = cpf_fragment[-2:]
                    first3 = cpf_fragment[:3]
                    cursor.execute(query, (matricula, last2, first3))
                    return cursor.fetchone()
        except Exception as e:
            raise DatabaseError(f"Erro ao buscar linha de login: {e}")

    # ==== Margem (Nova Lógica) ====
    def get_socio_core(self, matricula: str):
        """Retorna (tipo, limite, cpf) do sócio."""
        query = "SELECT tipo, limite, cpf FROM socios WHERE TRIM(matricula) = %s"
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (matricula.strip(),))
                    return cursor.fetchone()
        except Exception as e:
            raise DatabaseError(f"Erro ao buscar dados do sócio: {e}")

    def get_matricula_atual(self, matricula_antiga: str) -> Optional[str]:
        query = "SELECT matricula_atual FROM matriculas WHERE TRIM(matricula_antiga) = %s"
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (matricula_antiga.strip(),))
                    row = cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            raise DatabaseError(f"Erro ao buscar matrícula atual: {e}")

    def get_sum_parcelas(self, matricula: str, ano: int, mes: int) -> float:
        query = (
            "SELECT SUM(parcelas.valor) FROM parcelas "
            "WHERE TRIM(parcelas.matricula) = %s AND YEAR(parcelas.vencimento)= %s "
            "AND MONTH(parcelas.vencimento)= %s AND parcelas.baixa = ''"
        )
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (matricula.strip(), ano, mes))
                    row = cursor.fetchone()
                    return float(row[0]) if row and row[0] is not None else 0.0
        except Exception as e:
            raise DatabaseError(f"Erro ao somar parcelas: {e}")

    # ==== Extrato / Descontos Mensais ====
    def list_parcelas_mes(self, matricula: str, mes: int, ano: int):
        """Lista parcelas abertas de um mês/ano para a matrícula."""
        query = (
            "SELECT parcelas.id, parcelas.conveniado, vendas.emissao, parcelas.parcelas, parcelas.valor, TRIM(parcelas.nrseq) "
            "FROM parcelas LEFT JOIN vendas ON parcelas.matricula = vendas.matricula AND parcelas.sequencia = vendas.sequencia "
            "WHERE parcelas.baixa = '' AND MONTH(parcelas.vencimento)= %s AND YEAR(parcelas.vencimento)= %s AND TRIM(parcelas.matricula)= %s "
            "ORDER BY parcelas.associado"
        )
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (mes, ano, matricula.strip()))
                    return cursor.fetchall()
        except Exception as e:
            raise DatabaseError(f"Erro ao listar parcelas: {e}")

    def list_compras_mes(self, matricula: str, mes: int, ano: int):
        """Lista compras (vendas) de um mês/ano para a matrícula."""
        query = (
            "SELECT vendas.emissao, TRIM(vendas.conveniado), vendas.parcelas, vendas.valorparcela, vendas.id "
            "FROM vendas WHERE vendas.valorparcela > 0 AND vendas.cancela = '' AND TRIM(vendas.matricula)= %s "
            "AND YEAR(vendas.emissao)= %s AND MONTH(vendas.emissao)= %s ORDER BY vendas.id DESC"
        )
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (matricula.strip(), ano, mes))
                    return cursor.fetchall()
        except Exception as e:
            raise DatabaseError(f"Erro ao listar compras: {e}")

class SociosMongoRepository:
    """Repository para operações MongoDB de sócios."""
    
    def __init__(self):
        self._client = DatabaseManager.get_mongo_client()

    def find_login_data(self, matricula: str):
        """Busca dados de login em cache MongoDB."""
        if not self._client or not self._client._mongo_db:
            return None
        coll = self._client._mongo_db.get_collection('socios_login_cache')
        return coll.find_one({'matricula': matricula})

    def store_login_data(self, socio):
        """Armazena dados de login em cache MongoDB."""
        if not self._client or not self._client._mongo_db:
            return
        coll = self._client._mongo_db.get_collection('socios_login_cache')
        coll.update_one({'matricula': socio.matricula}, {
            '$set': {
                'matricula': socio.matricula,
                'associado': socio.associado,
                'email': socio.email,
                'celular': socio.celular,
                'bloqueio': socio.bloqueio,
                'tipo': socio.tipo,
                'cpf': socio.cpf
            }
        }, upsert=True)

    # === Tentativas & Código de Compra ===
    def get_tentativas(self, matricula: str) -> int:
        if not self._client or not self._client._mongo_db:
            return 0
        coll = self._client._mongo_db.get_collection('tentativas_socios')
        doc = coll.find_one({'matricula': matricula})
        return doc.get('nr_vezes', 0) if doc else 0

    def incrementar_tentativa(self, matricula: str) -> int:
        if not self._client or not self._client._mongo_db:
            return 0
        coll = self._client._mongo_db.get_collection('tentativas_socios')
        doc = coll.find_one_and_update({'matricula': matricula}, {'$inc': {'nr_vezes': 1}}, upsert=True, return_document=True)
        if not doc:  # fallback se driver não retorna doc em versão usada
            doc = coll.find_one({'matricula': matricula})
        return doc.get('nr_vezes', 1)

    def reset_tentativas(self, matricula: str):
        if not self._client or not self._client._mongo_db:
            return
        coll = self._client._mongo_db.get_collection('tentativas_socios')
        coll.delete_one({'matricula': matricula})

    def set_bloqueio_login_cache(self, matricula: str, status: str):
        if not self._client or not self._client._mongo_db:
            return
        coll = self._client._mongo_db.get_collection('socios_login_cache')
        coll.update_one({'matricula': matricula}, {'$set': {'bloqueio': status}})

    def store_codigo_compra(self, matricula: str, codigo: str, associados: dict):
        if not self._client or not self._client._mongo_db:
            return
        coll = self._client._mongo_db.get_collection('codigos_compra')
        from datetime import datetime
        coll.update_one({'matricula': matricula}, {
            '$set': {
                'matricula': matricula,
                'codigo': codigo,
                'data_hora': datetime.now().isoformat(timespec='minutes'),
                **associados
            }
        }, upsert=True)

    def codigo_existe(self, codigo: str) -> bool:
        if not self._client or not self._client._mongo_db:
            return False
        coll = self._client._mongo_db.get_collection('codigos_compra')
        return coll.find_one({'codigo': codigo}) is not None