from typing import Optional, List, Tuple
from config.database import DatabaseManager
from core.exceptions import DatabaseError

class ConveniosRepository:
    """Acesso a dados MySQL para convênios (apenas MySQL)."""
    def buscar_por_usuario(self, usuario: str):
        """Retorna dados básicos do convênio (para verificação de bloqueio, etc.) sem validar senha.

        Usado em processos de autenticação com política de tentativas.
        """
        query = (
            "SELECT TRIM(convenio.codigo), convenio.razao_soc, convenio.fantasia, convenio.cgc, convenio.email, "
            "convenio.libera, convenio.desconto, convenio.parcelas, convenio.libera, convenio.senha "
            "FROM convenio WHERE TRIM(convenio.usuario)= %s"
        )
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (usuario.upper(),))
                    return cursor.fetchone()
        except Exception as e:
            raise DatabaseError(f"Erro ao buscar convênio por usuário: {e}")
    def buscar_por_usuario_senha(self, usuario: str, senha: str) -> Optional[Tuple]:
        query = (
            "SELECT TRIM(convenio.codigo), convenio.razao_soc, convenio.fantasia, convenio.cgc, convenio.email, "
            "convenio.libera, convenio.desconto, convenio.parcelas, convenio.libera "
            "FROM convenio WHERE TRIM(convenio.usuario)= %s AND TRIM(convenio.senha)= %s"
        )
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (usuario.upper(), senha.strip()))
                    return cursor.fetchone()
        except Exception as e:
            raise DatabaseError(f"Erro ao autenticar convênio: {e}")

    def buscar_codigo_por_email(self, email: str) -> Optional[str]:
        """Fallback: busca o código do convênio por e-mail no MySQL, quando Mongo não está acessível."""
        query = (
            "SELECT TRIM(convenio.codigo) FROM convenio WHERE LOWER(TRIM(convenio.email)) = %s"
        )
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (email.lower().strip(),))
                    row = cursor.fetchone()
                    return row[0] if row and row[0] else None
        except Exception as e:
            raise DatabaseError(f"Erro ao buscar código por e-mail: {e}")

    def buscar_email_por_codigo(self, codigo_convenio: str) -> Optional[str]:
        """Obtém o e-mail cadastrado no MySQL para o código do convênio."""
        query = (
            "SELECT LOWER(TRIM(convenio.email)) FROM convenio WHERE TRIM(convenio.codigo) = %s"
        )
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (codigo_convenio.strip(),))
                    row = cursor.fetchone()
                    return row[0] if row and row[0] else None
        except Exception as e:
            raise DatabaseError(f"Erro ao buscar e-mail por código: {e}")

    def obter_desconto(self, codigo: str) -> float:
        query = "SELECT desconto FROM convenio WHERE codigo = %s"
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (codigo,))
                    row = cursor.fetchone()
                    return float(row[0]) if row and row[0] is not None else 0.0
        except Exception as e:
            raise DatabaseError(f"Erro ao buscar desconto: {e}")

    def listar_parcelas_mes(self, codigo: str, mes: int, ano: int):
        query = (
            "SELECT parcelas.id, parcelas.associado, vendas.emissao, parcelas.parcelas, parcelas.valor, TRIM(parcelas.nrseq) "
            "FROM parcelas LEFT JOIN vendas ON parcelas.matricula = vendas.matricula AND parcelas.sequencia = vendas.sequencia "
            "WHERE MONTH(parcelas.vencimento)= %s AND YEAR(parcelas.vencimento)= %s AND TRIM(parcelas.codconven)= %s ORDER BY parcelas.associado"
        )
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (mes, ano, codigo))
                    return cursor.fetchall()
        except Exception as e:
            raise DatabaseError(f"Erro ao listar parcelas convênio: {e}")

    def listar_compras_mes(self, codigo: str, mes: int, ano: int):
        query = (
            "SELECT vendas.emissao, TRIM(vendas.associado), vendas.parcelas, vendas.valorparcela, vendas.id "
            "FROM vendas WHERE vendas.valorparcela > 0 AND vendas.cancela = '' AND TRIM(vendas.codconven)= %s "
            "AND YEAR(vendas.emissao)= %s AND MONTH(vendas.emissao)= %s ORDER BY vendas.id DESC, vendas.associado"
        )
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (codigo, ano, mes))
                    return cursor.fetchall()
        except Exception as e:
            raise DatabaseError(f"Erro ao listar compras convênio: {e}")

    # Operações Mongo removidas (usando ConveniosMongoRepository separado)

    def atualizar_senha_mysql(self, codigo_convenio: str, senha_hash: bytes):
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE convenio SET senha=%s WHERE TRIM(codigo)= %s", (senha_hash.decode('utf8', errors='ignore'), codigo_convenio))
                    conn.commit()
        except Exception as e:
            raise DatabaseError(f"Erro ao atualizar senha: {e}")

    def atualizar_senha_mysql_plain(self, codigo_convenio: str, senha_plain: str):
        """Atualiza senha em texto puro no MySQL (compatibilidade legacy).

        Use apenas como fallback controlado por feature flag quando a coluna 'senha'
        não comporta o hash (ex.: VARCHAR muito curto) e ainda não houve migração.
        """
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE convenio SET senha=%s WHERE TRIM(codigo)= %s", (senha_plain, codigo_convenio))
                    conn.commit()
        except Exception as e:
            raise DatabaseError(f"Erro ao atualizar senha (plain): {e}")

    # === Limite e Vendas (simplificados) ===
    def fetch_socio_core(self, matricula: str):
        query = ("SELECT tipo, limite, ncompras, associado, cpf, celular FROM socios WHERE TRIM(matricula)= %s")
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (matricula.strip(),))
                    row = cursor.fetchone()
                    if not row:
                        return None
                    return {
                        'tipo': row[0], 'limite': float(row[1] or 0.0), 'sequencia': int((row[2] or 0))+1,
                        'associado': row[3], 'cpf': row[4], 'celular': (row[5] or '')
                    }
        except Exception as e:
            raise DatabaseError(f"Erro ao buscar dados do sócio para limite: {e}")

    def soma_parcelas_mes(self, matricula: str, ano: int, mes: int) -> float:
        query = ("SELECT SUM(parcelas.valor) FROM parcelas WHERE parcelas.valor > 0 AND parcelas.baixa = '' "
                 "AND TRIM(parcelas.matricula)= %s AND YEAR(parcelas.vencimento)= %s AND MONTH(parcelas.vencimento)= %s")
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (matricula.strip(), ano, mes))
                    row = cursor.fetchone()
                    return float(row[0]) if row and row[0] is not None else 0.0
        except Exception as e:
            raise DatabaseError(f"Erro ao somar parcelas para limite: {e}")

    def registrar_venda(self, venda: dict):
        # persiste em vendas + parcelas (similar ao legacy, reduzido)
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO vendas (matricula, sequencia, emissao, associado, codconven, conveniado, parcelas, autorizado, operador, valorparcela, cancela) "
                        "VALUES (%s,%s,CURDATE(),%s,%s,%s,%s,'','',%s,'')",
                        (
                            venda['matricula'], venda['sequencia'], venda['associado'],
                            venda['codigo_convenio'], venda['nome_convenio'], venda['nr_parcelas'], venda['valor_parcela']
                        )
                    )
                    # parcelas
                    ano = venda['ano_inicial']; mes = venda['mes_inicial']
                    for i in range(1, venda['nr_parcelas']+1):
                        cursor.execute(
                            "INSERT INTO parcelas (matricula, sequencia, nrseq, vencimento, valor, associado, codconven, conveniado, parcelas, tipo, baixa) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'')",
                            (
                                venda['matricula'], venda['sequencia'], i,
                                f"{ano:04d}-{mes:02d}-01", venda['valor_parcela'], venda['associado'],
                                venda['codigo_convenio'], venda['nome_convenio'], venda['nr_parcelas'], venda['tipo_flag']
                            )
                        )
                        if i != venda['nr_parcelas']:
                            mes += 1
                            if mes > 12:
                                mes = 1; ano += 1
                    # atualiza sequencia
                    cursor.execute("UPDATE socios SET ncompras = %s WHERE matricula = %s", (venda['sequencia'], venda['matricula']))
                    conn.commit()
        except Exception as e:
            raise DatabaseError(f"Erro ao registrar venda: {e}")

    # === Atualização de cadastro do convênio ===
    def atualizar_cadastro_mysql(self, codigo_convenio: str, usuario: str, email: str, cpf_cnpj: str, fantasia: str, nome_razao: str):
        try:
            with DatabaseManager.get_mysql_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "UPDATE convenio SET usuario=%s, email=%s, cgc=%s, fantasia=%s, razao_soc=%s WHERE TRIM(codigo)= %s",
                        (usuario, email.lower() if email else None, cpf_cnpj, fantasia, nome_razao, codigo_convenio)
                    )
                    conn.commit()
        except Exception as e:
            raise DatabaseError(f"Erro ao atualizar cadastro do convênio: {e}")
