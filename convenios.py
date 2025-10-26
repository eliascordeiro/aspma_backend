from flask_restful import Resource
import warnings as _warnings
_warnings.warn(
    "[DEPRECATED] O módulo legacy 'convenios.py' será removido após migração. Use modules.convenios.*",
    DeprecationWarning,
    stacklevel=2
)
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, get_jwt_identity
)
from flask import jsonify, request
import json
import pymongo
import pymysql
from babel.numbers import format_decimal
import string
import random
from bcrypt import checkpw, gensalt, hashpw
from pytz import timezone
from bson.json_util import dumps
from datetime import date, datetime
import re
from flask_mail import Mail, Message
from decimal import Decimal
import os

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import requests

# NOVO: usar settings centralizadas (sem segredos hard-coded)
settings = None  # será atribuída se import bem-sucedido
for _candidate in ("config.settings", "settings"):
    if settings is not None:
        break
    try:  # import dinâmico evita erro estático de análise
        import importlib
        mod = importlib.import_module(_candidate)
        if hasattr(mod, 'settings'):
            settings = getattr(mod, 'settings')
    except Exception:  # pragma: no cover - ignorar se não existir
        continue

corte = 9

# ============================================================================
# CONFIGURAÇÃO (LEGACY) - AGORA SEM SEGREDOS HARD-CODED
# ============================================================================
# Esta seção foi sanitizada para remover credenciais expostas anteriormente.
# Os valores são lidos de variáveis de ambiente já suportadas em config/settings.py.
# Caso algum valor esteja ausente, as funções que dependem dele poderão falhar ao
# tentar conectar — o que é preferível a expor segredos no repositório.

if settings:
    connection_properties = {
        'host': settings.MYSQL_HOST,
        'port': settings.MYSQL_PORT,
        'user': settings.MYSQL_USER,
        # PyMySQL aceita 'password' ou 'passwd'; manter 'passwd' para compatibilidade
        'passwd': settings.MYSQL_PASSWORD,
        'db': settings.MYSQL_DATABASE,
        'charset': 'utf8mb4'
    }
else:  # fallback mínimo – NÃO inserir segredos aqui
    connection_properties = {
        'host': None,
        'port': 3306,
        'user': None,
        'passwd': None,
        'db': None
    }

# Conexão MongoDB segura
if settings and settings.MONGO_URI:
    try:
        client = pymongo.MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DATABASE]
    except Exception:
        client = None
        db = None
else:
    client = None
    db = None

# Funções auxiliares
def id_generator(size=6, chars=string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def _requests_retry_session(
    retries=5,
    backoff_factor=3,
    status_forcelist=(500, 502, 503, 504),
    allowed_methods=None,  # ✅ substitui method_whitelist
    session=None
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=allowed_methods  # ✅ novo nome do parâmetro
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def is_connected_to_internet():
    try:
        requests.get('http://www.google.com/', timeout=5)
        return True
    except requests.ConnectionError:
        return False

# Controle simples de de-dup (somente memória) para evitar mensagens repetidas no legado
_WHATS_DEDUP = {}

def _wh_dedup_ttl():
    try:
        return int(getattr(settings, 'WHATSAPP_DEDUP_TTL_SECONDS', 180))
    except Exception:
        return 180

def _dedup_key(stage, contact, id_compra):
    stage = (stage or '').strip().lower() or 'pre'
    return f"{stage}:{(contact or '').strip()}:{(id_compra or '').strip()}"

def _should_send(stage, contact, id_compra):
    try:
        key = _dedup_key(stage, contact, id_compra)
        ts = _WHATS_DEDUP.get(key)
        if ts:
            # usa UTC para simplicidade
            now = datetime.utcnow()
            if (now - ts).total_seconds() < _wh_dedup_ttl():
                return False
        return True
    except Exception:
        return True

def _record_sent(stage, contact, id_compra):
    try:
        key = _dedup_key(stage, contact, id_compra)
        _WHATS_DEDUP[key] = datetime.utcnow()
    except Exception:
        pass

# Classe principal
class LoginConvenio(Resource):
    def post(self):
        user_data = dict(request.json.get('dados', {}))
        if not user_data:
            return {'error': 'Requisição inválida: corpo JSON deve conter {"dados": {"usuario", "senha"}}'}, 400
        current_month_year = datetime.now(timezone('America/Sao_Paulo')).strftime('%m-%Y')
        # Evita consulta inicial ao Mongo para não falhar quando o servidor é antigo/incompatível
        convenios_collection = None
        if db is not None:
            try:
                convenios_collection = db['login_convenios']
            except Exception:
                convenios_collection = None

        '''
        if user_record and checkpw(user_data['senha'].encode('utf8'), user_record["senha"]):
            user_details = {
                'codigo': user_record['codigo'],
                'nome_razao': user_record['nomerazao'],
                'usuario': user_record['usuario'].lower(),
                'email': user_record['email'],
                'cpf_cnpj': user_record['cpf_cnpj'],
                'fantasia': user_record['fantasia'],
                'desconto': user_record['desconto'],
                'parcelas': user_record['parcelas'],
                'libera': user_record['libera'],
                'mes_ano': current_month_year
            }

            access_token = create_access_token(identity=user_record['usuario'].lower())
            refresh_token = create_refresh_token(identity=user_record['usuario'].lower())

            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'dados': user_details
            }
        '''
        # Fallback para banco MySQL
        try:
            connection = pymysql.connect(**connection_properties)
            print('Conexão com o banco de dados secundário bem-sucedida.')
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão com o banco de dados... Tente novamente!'}

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT 
                        TRIM(convenio.codigo), 
                        convenio.razao_soc, 
                        convenio.fantasia, 
                        convenio.cgc, 
                        convenio.email, 
                        convenio.libera, 
                        convenio.desconto, 
                        convenio.parcelas,
                        convenio.libera 
                    FROM convenio 
                    WHERE 
                        TRIM(convenio.usuario) = %s AND 
                        TRIM(convenio.senha) = %s
                """
                cursor.execute(query, (user_data['usuario'].upper(), user_data['senha'].strip()))
                rows = cursor.fetchall()

            for row in rows:
                user_details_secondary = {
                    'codigo': row[0],
                    'nome_razao': row[1],
                    'usuario': user_data['usuario'].lower(),
                    'email': row[4].lower(),
                    'cpf_cnpj': row[3],
                    'fantasia': row[2],
                    'desconto': row[6],
                    'parcelas': row[7],
                    'libera': row[8],
                    'mes_ano': current_month_year
                }

                # Gera tokens com o código vindo do MySQL (evita depender de Mongo)
                access_token = create_access_token(identity=row[0])
                refresh_token = create_refresh_token(identity=row[0])

                # Atualiza espelho no Mongo se disponível; ignora erros de compatibilidade
                if convenios_collection is not None:
                    try:
                        convenios_collection.find_one_and_update(
                            {'codigo': row[0]},
                            {
                                "$set": {
                                    'codigo': row[0],
                                    'nomerazao': row[1],
                                    'fantasia': row[2],
                                    'desconto': row[6],
                                    'parcelas': row[7],
                                    'libera': row[8],
                                    'cpf_cnpj': row[3],
                                    'email': row[4].lower(),
                                    'tipo': 'banco' if row[8] == 'X' else 'comercio',
                                    'usuario': user_data['usuario'].lower(),
                                    'senha': hashpw(user_data['senha'].encode('utf8'), gensalt()),
                                    'bloqueio': 'NAO'
                                }
                            },
                            upsert=True
                        )
                    except Exception:
                        # Ignora qualquer falha de Mongo (ex.: servidor antigo wireVersion<6)
                        pass

                return {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'dados': user_details_secondary
                }

        finally:
            connection.close()

        return {'error': 'Credenciais inválidas!'}

# Verificação de reCAPTCHA (usa variável de ambiente RECAPTCHA_SECRET_KEY)
def is_human(captcha_response):
    if not captcha_response:
        return False
    secret = getattr(settings, 'RECAPTCHA_SECRET_KEY', None) if settings else None
    if not secret:
        # Sem secret configurado tratamos como falha de verificação (padrão seguro)
        return False
    try:
        payload = {'response': captcha_response, 'secret': secret}
        response = requests.post("https://www.google.com/recaptcha/api/siteverify", payload, timeout=5)
        return json.loads(response.text).get('success', False)
    except Exception:
        return False

class Receber_Mensal(Resource):
    @jwt_required()
    def post(self):
        payload = request.json
        mes_ano = payload.get("mes_ano")
        usuario_id = get_jwt_identity()

        try:
            connection = pymysql.connect(**connection_properties)
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        try:
            with connection.cursor() as cursor:
                # Buscar desconto do convênio
                cursor.execute("SELECT desconto FROM convenio WHERE codigo = %s", (usuario_id,))
                resultado_desconto = cursor.fetchone()
                desconto_percentual = resultado_desconto[0] if resultado_desconto else 0.00

                # Buscar parcelas do mês/ano
                query = """
                    SELECT 
                        parcelas.id, 
                        parcelas.associado, 
                        vendas.emissao, 
                        parcelas.parcelas, 
                        parcelas.valor, 
                        TRIM(parcelas.nrseq) 
                    FROM parcelas 
                    LEFT JOIN vendas 
                        ON parcelas.matricula = vendas.matricula 
                        AND parcelas.sequencia = vendas.sequencia 
                    WHERE 
                        MONTH(parcelas.vencimento) = %s 
                        AND YEAR(parcelas.vencimento) = %s 
                        AND TRIM(parcelas.codconven) = %s 
                    ORDER BY parcelas.associado
                """
                cursor.execute(query, (mes_ano[:2], mes_ano[-4:], usuario_id))
                resultados = cursor.fetchall()

                parcelas = []
                total_valor = 0

                for parcela_id, associado, emissao, num_parcelas, valor, nrseq in resultados:
                    dia = int(emissao.strftime("%d"))
                    mes = int(emissao.strftime("%m"))
                    ano = int(emissao.strftime("%Y"))

                    # Ajuste do mês inicial com base no corte
                    if dia > corte:
                        mes = 1 if mes == 12 else mes + 1
                        ano += 1 if mes == 1 else 0

                    mes_ano_inicial = f"{str(mes).zfill(2)}-{str(ano).zfill(4)}"

                    # Cálculo do mês final
                    mes_final = mes
                    ano_final = ano
                    for _ in range(1, int(num_parcelas)):
                        mes_final = 1 if mes_final == 12 else mes_final + 1
                        ano_final += 1 if mes_final == 1 else 0

                    mes_ano_final = f"{str(mes_final).zfill(2)}-{str(ano_final).zfill(4)}"

                    parcela = {
                        'periodo': f"{mes_ano_inicial} a {mes_ano_final}",
                        'n_parcela': nrseq,
                        'id': parcela_id,
                        'nome': associado,
                        'data': emissao.strftime("%d-%m-%Y"),
                        'parcelas': str(int(num_parcelas)).strip(),
                        'valor': format_decimal(valor, format="#,##0.00;-#", locale='pt_BR')
                    }

                    parcelas.append(parcela)
                    total_valor += valor

        finally:
            connection.close()

        total_formatado = format_decimal(total_valor, format="#,##0.00;-#", locale='pt_BR')
        desconto_formatado = format_decimal(total_valor * desconto_percentual / 100, format="#,##0.00;-#", locale='pt_BR')
        receber_formatado = format_decimal(total_valor - (total_valor * desconto_percentual / 100), format="#,##0.00;-#", locale='pt_BR')

        retorno = {
            'dados': dumps(parcelas),
            'total': total_formatado,
            'desconto': desconto_formatado,
            'receber': receber_formatado
        }

        return retorno

class Compras_Mensal(Resource):
    @jwt_required()
    def post(self):
        payload = request.json
        mes_ano = payload.get("mes_ano")
        usuario_id = get_jwt_identity()

        try:
            connection = pymysql.connect(**connection_properties)
            print('Conectado ao banco de dados.')
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT 
                        vendas.emissao, 
                        TRIM(vendas.associado), 
                        vendas.parcelas, 
                        vendas.valorparcela, 
                        vendas.id 
                    FROM vendas 
                    WHERE 
                        vendas.valorparcela > 0 
                        AND vendas.cancela = '' 
                        AND TRIM(vendas.codconven) = %s 
                        AND YEAR(vendas.emissao) = %s 
                        AND MONTH(vendas.emissao) = %s 
                    ORDER BY vendas.id DESC, vendas.associado
                """
                cursor.execute(query, (usuario_id, mes_ano[-4:], mes_ano[:2]))
                resultados = cursor.fetchall()

                compras = []
                total_valor = 0

                for emissao, associado, parcelas, valor_parcela, venda_id in resultados:
                    dia = int(emissao.strftime("%d"))
                    mes = int(emissao.strftime("%m"))
                    ano = int(emissao.strftime("%Y"))

                    # Ajuste do mês inicial com base no corte
                    if dia > corte:
                        mes = 1 if mes == 12 else mes + 1
                        ano += 1 if mes == 1 else 0

                    mes_ano_inicial = f"{str(mes).zfill(2)}-{str(ano).zfill(4)}"

                    # Cálculo do mês final
                    mes_final = mes
                    ano_final = ano
                    for _ in range(1, int(parcelas)):
                        mes_final = 1 if mes_final == 12 else mes_final + 1
                        ano_final += 1 if mes_final == 1 else 0

                    mes_ano_final = f"{str(mes_final).zfill(2)}-{str(ano_final).zfill(4)}"

                    compra = {
                        'periodo': f"{mes_ano_inicial} a {mes_ano_final}",
                        'data': emissao.strftime("%d-%m-%Y"),
                        'nome': associado,
                        'parcelas': str(int(parcelas)).strip(),
                        'valor': format_decimal(valor_parcela, format="#,##0.00;-#", locale='pt_BR'),
                        'id': venda_id
                    }

                    compras.append(compra)
                    total_valor += valor_parcela

        finally:
            connection.close()

        total_formatado = format_decimal(total_valor, format="#,##0.00;-#", locale='pt_BR')
        return {'dados': dumps(compras), 'total': total_formatado}

class Autenticacao(Resource):
    @jwt_required()
    def post(self):
        payload = request.json
        usuario_id = get_jwt_identity()
        dados_login = dict(payload.get('dados', {}))

        colecao_login = db['login_convenios']
        registro_login = colecao_login.find_one({'codigo': usuario_id})

        if registro_login and registro_login.get('bloqueio') == 'SIM':
            return {'msg': 'Senha bloqueada... para desbloquear acesse [Alterar Senha]'}

        if registro_login and checkpw(dados_login['senha'].encode('utf8'), registro_login["senha"]):
            db['tentativas_convenio'].find_one_and_delete({'codigo': usuario_id})
            return {'msg': 'ok'}

        # Controle de tentativas
        tentativas = 1
        colecao_tentativas = db['tentativas_convenio']
        registro_tentativa = colecao_tentativas.find_one({'codigo': usuario_id})

        if registro_tentativa:
            tentativas = registro_tentativa['tentativas'] + 1
            if tentativas >= 3:
                colecao_login.find_one_and_update(
                    {'codigo': usuario_id},
                    {"$set": {'bloqueio': 'SIM'}},
                    upsert=True
                )

        colecao_tentativas.find_one_and_update(
            {'codigo': usuario_id},
            {"$set": {'tentativas': tentativas}},
            upsert=True
        )

        return {'msg': f'Senha inválida! Tentativa {tentativas} de 3.'}

class Grava_Vendas(Resource):
    @jwt_required()
    def post(self):
        if not is_connected_to_internet():
            return {'msg': 'Verifique sua conexão com a Internet!'}

        payload = request.json
        usuario_info = get_jwt_identity()
        dados_requisicao = dict(payload.get('dados', {}))

        colecao_codigos = db['codigo_para_compra']
        registro_codigo = colecao_codigos.find_one({'codigo': dados_requisicao.get('codigo')})

        if not registro_codigo:
            return {'msg': 'Código da compra inválido!'}

        limite_info = limite(registro_codigo)
        sequencia = limite_info.get('sequencia')
        data_hora = datetime.now().strftime('%d-%m-%Y %H:%M')

        valor_bruto = dados_requisicao.get('valor', '0').replace('.', '').replace(',', '.')
        valor_total = round(float(valor_bruto), 2)
        numero_parcelas = int(dados_requisicao.get('nr_parcelas', 1))
        valor_parcela = round(valor_total / numero_parcelas, 2)

        if limite_info.get('saldo') == 'Falhou':
            return {'msg': 'Operação não concluída! Tente novamente.'}
        elif limite_info.get('saldo', 0) < valor_parcela:
            return {'msg': 'Saldo insuficiente!'}

        matricula = registro_codigo.get('matricula')
        sequencia_formatada = f"M{matricula}S{sequencia}"

        dados_consig = {
            "matricula": matricula,
            "sequencia": sequencia_formatada,
            "qtParcela": numero_parcelas,
            "vlParcela": valor_parcela,
            "valorTotal": valor_total
        }

        if int(registro_codigo.get('tipo')) == 1 and not grava_consig(dados_consig):
            return {'msg': 'Servidor consig-plus indisponível. Repita o processo!'}

        valor_total_str = f"{valor_total:.2f}"
        valor_parcela_str = f"{valor_parcela:.2f}"

        mes_inicial = limite_info.get('mes')
        ano_inicial = limite_info.get('ano')
        mes_final = mes_inicial
        ano_final = ano_inicial

        for i in range(1, numero_parcelas + 1):
            if i != numero_parcelas:
                mes_final += 1
                if mes_final > 12:
                    mes_final = 1
                    ano_final += 1

        dados_venda = {
            'matricula': registro_codigo.get('matricula_aspma'),
            'nome_socio': registro_codigo.get('associado'),
            'consignataria': registro_codigo.get('tipo'),
            'sequencia': sequencia,
            'codigo_da_compra': dados_requisicao.get('codigo'),
            'nr_parcelas': numero_parcelas,
            'valor_total': valor_total_str,
            'valor_parcela': valor_parcela_str,
            'codigo_convenio': usuario_info.get('codigo'),
            'nome_convenio': usuario_info.get('nome_razao'),
            'usuario': usuario_info.get('usuario'),
            'data_hora': data_hora,
            'mes_inicial': mes_inicial,
            'ano_inicial': ano_inicial,
            'mes_final': mes_final,
            'ano_final': ano_final
        }

        try:
            db['vendas'].insert_one(dados_venda)
        except:
            if int(registro_codigo.get('tipo')) == 1:
                exclui_consig(dados_consig)
            return {'msg': 'Operação não concluída! Tente novamente.'}

        if grava_mysql(dados_venda):
            db['codigo_para_compra'].delete_one({'matricula': registro_codigo.get('matricula')})
            return {'msg': 'Operação realizada com sucesso!'}

        db['vendas'].delete_one({
            'matricula': registro_codigo.get('matricula_aspma'),
            'sequencia': sequencia
        })

        if int(registro_codigo.get('tipo')) == 1:
            exclui_consig(dados_consig)

        return {'msg': 'Operação não concluída! Tente novamente.'}

def exclui_consig(dados_consig):
    session = _requests_retry_session(method_whitelist=False)
    try:
        session.post(
            'http://200.98.145.36/aspma/php/liquida_mobile_consig.php',
            params=dados_consig,
            verify=False,
            timeout=(10, 10)
        )
        return True
    except requests.RequestException:
        return False


def limite(registro):
    try:
        connection = pymysql.connect(**connection_properties)
        print('Conexão estabelecida.')
    except pymysql.err.OperationalError:
        print("Falha na conexão com o banco.")
        return {"saldo": "Falhou"}

    hoje = date.today()
    mes_referencia = hoje.month
    ano_referencia = hoje.year

    if hoje.day > 9:
        mes_referencia = 1 if mes_referencia == 12 else mes_referencia + 1
        ano_referencia += 1 if mes_referencia == 1 else 0

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT socios.limite, socios.ncompras FROM socios WHERE TRIM(socios.matricula) = %s",
                (registro.get('matricula_aspma'),)
            )
            resultado = cursor.fetchone()

            limite_valor = float(resultado[0]) if resultado and resultado[0] is not None else 0.0
            sequencia = int(resultado[1]) + 1 if resultado and resultado[1] is not None else 1

    except Exception:
        return {"saldo": "Falhou"}

    if int(registro.get('tipo')) != 1:
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT SUM(parcelas.valor)
                    FROM parcelas
                    LEFT JOIN vendas ON parcelas.matricula = vendas.matricula AND parcelas.sequencia = vendas.sequencia
                    WHERE parcelas.valor > 0
                        AND parcelas.baixa = ''
                        AND vendas.cancela = ''
                        AND TRIM(parcelas.matricula) = %s
                        AND YEAR(parcelas.vencimento) = %s
                        AND MONTH(parcelas.vencimento) = %s
                """, (registro.get('matricula_aspma'), ano_referencia, mes_referencia))

                resultado = cursor.fetchone()
                total_utilizado = float(resultado[0]) if resultado and resultado[0] is not None else 0.0

            saldo_disponivel = limite_valor - total_utilizado

            return {
                "saldo": round(saldo_disponivel, 2),
                "mes": mes_referencia,
                "ano": ano_referencia,
                "sequencia": str(sequencia)
            }

        except Exception:
            return {"saldo": "Falhou"}
        finally:
            connection.close()

    else:
        try:
            dados_margem = {
                "cliente": "ASPMA",
                "convenio": "ASPMA-ARAUCARIA",
                "usuario": "aspma_xml",
                "senha": "dcc0bd05",
                "matricula": str(registro.get('matricula')),
                "cpf": registro.get('cpf'),
                "valorParcela": "1.00"
            }

            session = _requests_retry_session(method_whitelist=False)
            response = session.post(
                'http://200.98.112.240/aspma/php/consultaMargemZetra.php',
                params=dados_margem,
                verify=False,
                timeout=(20, 20)
            )

            # Aqui você pode extrair a margem do XML se necessário:
            # margem = re.search('<margem>(.+?)</', response.text).group(1)

            # return {
            #     "saldo": float(margem),
            #     "mes": mes_referencia,
            #     "ano": ano_referencia,
            #     "sequencia": str(sequencia)
            # }

        except Exception:
            return {"saldo": "Falhou"}

    return {"saldo": "Falhou"}

def grava_consig(dados_consig):
    session = _requests_retry_session(method_whitelist=False)
    try:
        response = session.post(
            'http://200.98.112.240/aspma/php/zetra/grava_mobile_consig.php',
            params=dados_consig,
            verify=False,
            timeout=(10, 10)
        )
        mensagem = re.search('<string>(.+?)</', response.text)
        if not mensagem or mensagem.group(1) != 'Contrato cadastrado com sucesso!':
            return False
        return True
    except requests.RequestException as e:
        print(f"Erro ao enviar contrato: {e}")
        return False


def grava_mysql(dados_venda):
    try:
        connection = pymysql.connect(**connection_properties)
        print('Conexão com MySQL estabelecida.')
    except pymysql.err.OperationalError as e:
        print(f"Erro de conexão: {e}")
        return False

    try:
        # Dados para tabela `vendas`
        vendas_fields = "(matricula, sequencia, emissao, associado, codconven, conveniado, parcelas, autorizado, operador, valorparcela, cancela)"
        registro_venda = [
            dados_venda.get('matricula'),
            dados_venda.get('sequencia'),
            datetime.now(timezone('America/Sao_Paulo')).strftime('%Y-%m-%d'),
            dados_venda.get('nome_socio'),
            dados_venda.get('codigo_convenio'),
            dados_venda.get('nome_convenio'),
            dados_venda.get('nr_parcelas'),
            '',
            '',
            dados_venda.get('valor_parcela'),
            ''
        ]
        vendas_placeholders = ', '.join(['%s'] * len(registro_venda))

        # Dados para tabela `parcelas`
        parcelas_fields = "(matricula, sequencia, nrseq, vencimento, valor, associado, codconven, conveniado, parcelas, tipo, baixa)"
        parcelas_inserts = []
        ano = dados_venda.get('ano_inicial')
        mes = dados_venda.get('mes_inicial')
        tipo = 'X' if int(dados_venda.get('consignataria')) == 1 else ''

        for i in range(1, int(dados_venda.get('nr_parcelas')) + 1):
            vencimento = f"{str(ano).zfill(4)}-{str(mes).zfill(2)}-01"
            registro_parcela = [
                dados_venda.get('matricula'),
                dados_venda.get('sequencia'),
                i,
                vencimento,
                dados_venda.get('valor_parcela'),
                dados_venda.get('nome_socio'),
                dados_venda.get('codigo_convenio'),
                dados_venda.get('nome_convenio'),
                dados_venda.get('nr_parcelas'),
                tipo,
                ''
            ]
            parcelas_inserts.append(registro_parcela)

            if i != int(dados_venda.get('nr_parcelas')):
                mes += 1
                if mes > 12:
                    mes = 1
                    ano += 1

        parcelas_placeholders = ', '.join(['%s'] * len(parcelas_inserts[0]))

        with connection.cursor() as cursor:
            cursor.executemany(
                f"INSERT INTO vendas {vendas_fields} VALUES ({vendas_placeholders})",
                [registro_venda]
            )
            cursor.executemany(
                f"INSERT INTO parcelas {parcelas_fields} VALUES ({parcelas_placeholders})",
                parcelas_inserts
            )
            cursor.execute(
                "UPDATE socios SET ncompras = %s WHERE matricula = %s",
                (dados_venda.get('sequencia'), dados_venda.get('matricula'))
            )
            connection.commit()

    except Exception as e:
        print(f"Erro ao gravar no MySQL: {e}")
        return False

    finally:
        connection.close()

    return True


class Envia_Email_Codigo(Resource):
    @jwt_required()
    def post(self):
        if not is_connected_to_internet():
            return {'msg': 'Verifique sua conexão com a Internet!'}

        mail = Mail()
        usuario_info = get_jwt_identity()
        codigo_convenio = usuario_info.get('codigo')

        colecao_convenios = db['login_convenios']
        registro_convenio = colecao_convenios.find_one({"codigo": codigo_convenio})

        if not registro_convenio or not registro_convenio.get('email'):
            return {'msg': 'E-mail não enviado! Verifique seu cadastro.'}

        codigo_seguranca = id_generator()

        mensagem = Message(
            subject='Código de Segurança A.S.P.M.A.',
            sender='consigexpress@consigexpress.com.br',
            recipients=[registro_convenio['email']]
        )
        mensagem.html = f"<p style='font-size: 22px'>INFORME ESTE CÓDIGO QUANDO SOLICITADO: {codigo_seguranca}</p>"

        try:
            mail.send(mensagem)
        except Exception as e:
            print(f"Erro ao enviar e-mail: {e}")
            return {'msg': 'Falha ao enviar o e-mail. Tente novamente.'}

        db['codigo_altera_senha_convenio'].find_one_and_update(
            {'codigo_convenio': codigo_convenio},
            {"$set": {'codigo': codigo_seguranca}},
            upsert=True
        )

        return {'msg': 'ok'}

class Altera_Senha_Convenio(Resource):
    @jwt_required()
    def post(self):
        try:
            # Retrieve the incoming request data
            request_data = request.json
            user_identity = get_jwt_identity()

            if 'dados' not in request_data:
                return {'msg': 'Dados não fornecidos.'}, 400

            dados = request_data['dados']
            convenio_codigo = user_identity['codigo']
            provided_code = dados.get('codigo')
            new_password = dados.get('nova_senha')

            if not provided_code or not new_password:
                return {'msg': 'Código ou nova senha não fornecidos.'}, 400

            # Verify the code in the MongoDB collection
            code_collection = db['codigo_altera_senha_convenio']
            code_entry = code_collection.find_one({
                'codigo_convenio': convenio_codigo,
                'codigo': provided_code
            })

            if not code_entry:
                return {'msg': 'Código inválido! Verifique seu E-Mail ou repita o processo novamente.'}, 404

            # Update the user's password and unblock the account in MongoDB
            login_collection = db['login_convenios']
            login_collection.find_one_and_update(
                {'codigo': convenio_codigo},
                {
                    "$set": {
                        'bloqueio': 'NAO',
                        'senha': new_password  # Directly storing the new password
                    }
                },
                upsert=True
            )

            # Remove previous attempts and temporary codes
            attempts_collection = db['tentativas_convenio']
            attempts_collection.find_one_and_delete({'codigo': convenio_codigo})

            code_collection.delete_one({'codigo_convenio': convenio_codigo})

            try:
                # Connect to MySQL
                connection = pymysql.connect(**connection_properties)

                with connection.cursor() as cursor:
                    query = "UPDATE convenio SET senha = %s WHERE TRIM(codigo) = %s"
                    values = (new_password, str(convenio_codigo))  # Directly storing the new password

                    cursor.execute(query, values)
                    connection.commit()

                    if cursor.rowcount == 0:
                        return {'msg': 'Erro ao atualizar senha: código não encontrado.'}, 404

            except pymysql.err.OperationalError as e:
                return {'msg': 'Erro ao conectar ao banco de dados MySQL.'}, 500

            except Exception as e:
                return {'msg': 'Erro ao atualizar senha no banco de dados MySQL.'}, 500

            finally:
                if connection:
                    connection.close()

            return {'msg': 'Senha alterada com sucesso!'}, 200

        except Exception as e:
            return {'msg': 'Erro ao processar sua solicitação.'}, 500


class Grava_Regs(Resource):
    @jwt_required()
    def post(self):
        payload = request.json
        usuario_info = get_jwt_identity()
        dados_registro = dict(payload.get('dados', {}))
        nome_tabela_mongo = payload.get('tb')

        try:
            connection = pymysql.connect(**connection_properties)
            print('Conexão com MySQL estabelecida.')
        except pymysql.err.OperationalError:
            print("Falha ao conectar ao banco de dados.")
            return {'msg': 'Erro de conexão com o banco de dados.'}

        try:
            with connection.cursor() as cursor:
                query = """
                    UPDATE convenio SET 
                        usuario = %s,
                        email = %s,
                        cgc = %s,
                        fantasia = %s,
                        razao_soc = %s
                    WHERE TRIM(codigo) = %s
                """
                cursor.execute(query, (
                    dados_registro.get('usuario'),
                    dados_registro.get('email'),
                    dados_registro.get('cpf_cnpj'),
                    dados_registro.get('fantasia'),
                    dados_registro.get('nome_razao'),
                    usuario_info.get('codigo')
                ))
                connection.commit()
        except Exception as e:
            print(f"Erro ao atualizar MySQL: {e}")
            return {'msg': 'Erro ao atualizar os dados.'}
        finally:
            connection.close()

        try:
            colecao_mongo = db[nome_tabela_mongo]
            colecao_mongo.find_one_and_update(
                {'codigo': usuario_info.get('codigo')},
                {"$set": {
                    'nomerazao': dados_registro.get('nome_razao'),
                    'fantasia': dados_registro.get('fantasia'),
                    'cpf_cnpj': dados_registro.get('cpf_cnpj'),
                    'email': dados_registro.get('email', '').lower(),
                    'usuario': dados_registro.get('usuario', '').lower(),
                    'bloqueio': 'NAO'
                }},
                upsert=True
            )
        except Exception as e:
            print(f"Erro ao atualizar MongoDB: {e}")
            return {'msg': 'Erro ao atualizar os dados no MongoDB.'}

        return dados_registro

class Envia_Email_Codigo_Esqueceu(Resource):
    def options(self):
        from flask import make_response
        return make_response('', 204)

    def post(self):
        mail = Mail()
        payload = request.json
        dados_requisicao = dict(payload.get('dados', {}))
        email = dados_requisicao.get('email', '').lower()

        colecao_convenios = db['login_convenios']
        registro_convenio = colecao_convenios.find_one({"email": email})

        if not registro_convenio or not registro_convenio.get('codigo'):
            return {'msg': 'E-mail não enviado! Verifique seu e-mail ou atualize seu cadastro.'}

        codigo_seguranca = id_generator()

        mensagem = Message(
            subject='Código de Segurança A.S.P.M.A.',
            sender='consigexpress@consigexpress.com.br',
            recipients=[email]
        )
        mensagem.html = f"<p style='font-size: 22px'>INFORME ESTE CÓDIGO QUANDO SOLICITADO: {codigo_seguranca}</p>"

        try:
            mail.send(mensagem)
        except Exception as e:
            print(f"Erro ao enviar e-mail: {e}")
            return {'msg': 'Falha ao enviar o e-mail. Tente novamente.'}

        db['codigo_altera_senha_convenio'].find_one_and_update(
            {'codigo_convenio': registro_convenio['codigo']},
            {"$set": {'codigo': codigo_seguranca}},
            upsert=True
        )

        return {'msg': 'ok'}

class Altera_Senha_Esqueceu_Convenio(Resource):
    def options(self):
        from flask import make_response
        return make_response('', 204)

    def post(self):
        payload = request.json
        dados_requisicao = dict(payload.get('dados', {}))
        codigo_recebido = dados_requisicao.get('codigo')
        nova_senha = dados_requisicao.get('nova_senha')

        if not codigo_recebido or not nova_senha:
            return {'msg': 'Dados incompletos. Verifique o código e a nova senha.'}

        colecao_codigos = db['codigo_altera_senha_convenio']
        registro_codigo = colecao_codigos.find_one({'codigo': codigo_recebido})

        if not registro_codigo:
            return {'msg': 'Código inválido! Verifique novamente seu e-mail ou repita o processo.'}

        codigo_convenio = registro_codigo.get('codigo_convenio')

        # Atualiza a senha e desbloqueia o acesso
        db['login_convenios'].find_one_and_update(
            {'codigo': codigo_convenio},
            {"$set": {
                'bloqueio': 'NAO',
                'senha': hashpw(nova_senha.encode('utf8'), gensalt())
            }},
            upsert=True
        )

        # Remove tentativas e código usado
        db['tentativas_convenio'].find_one_and_delete({'codigo': codigo_convenio})
        db['codigo_altera_senha_convenio'].delete_one({'codigo_convenio': codigo_convenio})

        return {'msg': 'Senha alterada com sucesso!'}

def liquida_consig_teste():
    contrato_id = "M749102S265"
    dados_contrato = {
        "matricula": "749102",
        "sequencia": contrato_id,
        "qtParcela": "1",
        "vlParcela": "0.01",
        "valorTotal": "0.01"
    }

    session = _requests_retry_session(method_whitelist=False)

    try:
        resposta = session.post(
            "http://200.98.145.36/aspma/php/liquida_mobile_consig.php",
            params=dados_contrato,
            verify=False,
            timeout=(10, 10)
        )

        match = re.search(r"<string>(.+?)</", resposta.text)
        mensagem = match.group(1) if match else "Resposta não reconhecida."

        return {"msg": mensagem}

    except requests.RequestException as e:
        print(f"Erro na requisição: {e}")
        return {"msg": "Falha ao comunicar com o servidor."}

def fetch_user_by_matricula(matricula):
    matricula_data = ''  # Renomeando "_mat" para "matricula_data"

    # Acessando a coleção de "login_socios"
    login_socios_collection = db['login_socios']

    find_result = login_socios_collection.find_one({'matricula': matricula})

    try:
        # Estabelecendo conexão com o banco de dados
        connection = pymysql.connect(**connection_properties)
        print('Conexão estabelecida.')
    except pymysql.err.OperationalError:
        print("Erro ao tentar se conectar ao banco de dados.")

    try:
        with connection.cursor() as cursor:
            # Executando a consulta para buscar informações
            query = (
                "SELECT socios.tipo, socios.limite, socios.ncompras, socios.associado, socios.autorizado, "
                "socios.senha, socios.celular, socios.bloqueio, socios.cpf, matriculas.matricula_atual "
                "FROM socios "
                "LEFT JOIN matriculas ON TRIM(socios.matricula) = TRIM(matriculas.matricula_antiga) "
                "WHERE TRIM(socios.matricula) = %s"
            )
            cursor.execute(query, (matricula.strip(),))
            rows = cursor.fetchall()

            for row in rows:
                matricula_data = {
                    'matricula': matricula,
                    'associado': row[3],
                    'tipo': row[0],
                    'limite': row[1],
                    'sequencia': row[2] + 1,
                    'autorizados': row[4],
                    'senha': row[5],
                    'celular': row[6],
                    'bloqueio': row[7],
                    'cpf': row[8],
                    'matricula_atual': row[9]
                }

    except Exception as e:
        print(f"Erro ao executar a consulta: {e}")
        return None
    finally:
        connection.close()

    return json.loads(json.dumps(matricula_data))

class Busca_Limite(Resource):
    @jwt_required()
    def post(self):
        if not is_connected_to_internet():
            return {'msg': 'Por favor, verifique sua conexão com a Internet!'}

        payload = request.json
        usuario_id = get_jwt_identity()
        dados_requisicao = dict(payload.get('dados', {}))

        associado = fetch_user_by_matricula(dados_requisicao.get('matricula'))
        if not associado:
            return {'msg': 'Matrícula não encontrada!'}

        celular_limpo = associado.get('celular', '').replace(" ", "")
        if len(celular_limpo) != 8:
            return {'msg': 'Associado sem celular cadastrado. Entre em contato com a A.S.P.M.A!'}

        if associado.get('bloqueio') == 'X':
            return {'msg': 'Senha bloqueada! Desbloqueio apenas na SEDE da A.S.P.M.A.'}
        else:
            db['conta_senha_convenio'].delete_one({'matricula': dados_requisicao.get('matricula')})

        limite = fetch_user_limit(associado)

        valor_bruto = dados_requisicao.get('valor', '0').replace('.', '').replace(',', '.')
        valor_total = round(float(valor_bruto), 2)
        numero_parcelas = int(dados_requisicao.get('nr_parcelas', 1))
        valor_parcela = round(valor_total / numero_parcelas, 2)

        if limite.get('saldo', 0) < valor_parcela:
            return {'msg': 'Saldo insuficiente!', 'saldo': limite['saldo']}

        id_compra = ''.join(random.choice(string.digits) for _ in range(4))
        celular_formatado = mascarar_numero(f"(41) {associado['celular']}")

        limite.update({
            'associado': associado.get('associado'),
            'valor': dados_requisicao.get('valor'),
            'nr_parcelas': numero_parcelas,
            'tipo': associado.get('tipo'),
            'senha': associado.get('senha'),
            'autorizados': associado.get('autorizados'),
            'data': datetime.now(timezone('America/Sao_Paulo')).strftime('%d-%m-%Y %H:%M'),
            'valor_total': format_decimal(valor_total, format="#,##0.00;-#", locale='pt_BR'),
            'valor_parcela': format_decimal(valor_parcela, format="#,##0.00;-#", locale='pt_BR'),
            'convenio': usuario_id.get('nome_razao') if isinstance(usuario_id, dict) else usuario_id,
            'celular': associado.get('celular'),
            'matricula_atual': str(associado.get('matricula_atual')),
            'cpf': associado.get('cpf'),
            'saldo_atual': limite.get('saldo'),
            'id_compra': id_compra,
            'phone_mask': celular_formatado
        })

        sent = envia_pr_mensagem(limite)
        try:
            limite['whatsapp_sent'] = bool(sent)
        except Exception:
            pass

        return {'msg': limite}

def mascarar_numero(numero):
    partes = numero.split()
    partes[1] = "*****"  # Substitui o meio do número por asteriscos
    return " ".join(partes)

#--------------------------------------------------------------------------------------------#
def fetch_user_limit(items):
    try:
        # Conectando ao banco de dados
        connection = pymysql.connect(**connection_properties)
        print('Conexão estabelecida com sucesso.')
    except pymysql.err.OperationalError:
        print("Erro ao tentar conectar ao banco de dados.")

    total = ''

    # Obtendo a data e hora de São Paulo
    timezone_sp = timezone('America/Sao_Paulo')
    current_datetime = datetime.now(timezone_sp)
   
    current_month = current_datetime.month
    current_year = current_datetime.year

    # Ajustando o mês e ano dependendo da condição
    if current_datetime.day > 9:
        if current_month == 12:
            next_month = 1
            next_year = current_year + 1
        else:
            next_month = current_month + 1
            next_year = current_year
    else:
         next_month = current_month
         next_year = current_year

    try:
        if int(items['tipo']) != 1:
            with connection.cursor() as cursor:
                query = (
                   "SELECT SUM(parcelas.valor) FROM parcelas "
                   "WHERE parcelas.valor > 0 AND parcelas.baixa = '' "
                   "AND TRIM(parcelas.matricula) = %s "
                   "AND YEAR(parcelas.vencimento) = %s AND MONTH(parcelas.vencimento) = %s"
                )
                    
                cursor.execute(query, (items['matricula'].strip(), next_year, next_month))
                rows = cursor.fetchall()

                total = 0.0
                
                if rows:
                    for row in rows:
                        if row[0] is not None:
                            total = float(row[0])

                # Calculando saldo
                balance = float(items['limite']) - total

                return_data = {
                    "matricula": items['matricula'],
                    "associado": items['associado'],
                    "saldo": float(balance),
                    "mes": next_month,
                    "ano": next_year,
                    "limite": format_decimal(balance, format="#,##0.00;-#", locale='pt_BR'),
                    "sequencia": str(int(items['sequencia']))
                }
        else:
            # Dados para consulta de margem
            request_data = {
                "cliente": "ASPMA",
                "convenio": "ASPMA-ARAUCARIA",
                "usuario": "aspma_xml",
                "senha": "dcc0bd05",
                "matricula": items['matricula_atual'],
                "cpf": items['cpf'],
                "valorParcela": "1.00"
            }

            session = _requests_retry_session(method_whitelist=False)
            response = session.post(
                'http://200.98.112.240/aspma/php/consultaMargemZetra.php',
                 params=request_data, verify=False, timeout=(20, 20)
            )

            try:
                margin_value = re.search(
                    '<ns6:valorMargem xmlns:ns6="InfoMargem">(.+?)</', 
                    response.text
                ).group(1)

                return_data = {
                    "matricula": items['matricula'],
                    "associado": items['associado'],
                    "saldo": float(margin_value),
                    "mes": next_month,
                    "ano": next_year,
                    "limite": format_decimal(margin_value, format="#,##0.00;-#", locale='pt_BR'),
                    "sequencia": str(int(items['sequencia']))
                }
            except Exception:
                return_data = {"saldo": "Falhou"}
    except Exception:
        return_data = {"saldo": "Falhou"}
    finally:
        connection.close()
    return return_data

def envia_pr_mensagem(dados):
    """
    Envia a 1ª mensagem (pré-venda) via WhatsGw com dados do limite.
    Usa settings para credenciais e normaliza o telefone do contato.
    """
    api_url = getattr(settings, 'WHATS_GW_API_URL', 'https://app.whatsgw.com.br/api/WhatsGw/Send') if settings else 'https://app.whatsgw.com.br/api/WhatsGw/Send'
    apikey = getattr(settings, 'WHATS_GW_APIKEY', None) if settings else None
    sender = getattr(settings, 'WHATS_GW_SENDER', None) if settings else None

    # feature-flag global
    if settings and hasattr(settings, 'WHATSAPP_ENABLED') and not getattr(settings, 'WHATSAPP_ENABLED'):
        print('[WhatsApp] Envio pré-venda desativado (WHATSAPP_ENABLED=false).')
        return False
    # feature-flag por etapa (pré)
    if os.getenv('WHATSAPP_SEND_PRE', 'true').lower() not in ('1','true','yes'):
        print('[WhatsApp] Envio pré-venda desativado por WHATSAPP_SEND_PRE=false.')
        return False

    if not apikey or not sender:
        print('[WhatsApp] Envio pré-venda desativado: credenciais ausentes no settings.')
        return False

    # Normaliza telefone do contato
    digits = re.sub(r"\D", "", str(dados.get('celular', '') or ''))
    if len(digits) == 8:
        contact = f"55419{digits}"
    elif len(digits) == 9:
        contact = f"5541{digits}"
    elif len(digits) == 10:
        contact = f"55{digits[:2]}9{digits[2:]}"
    elif len(digits) in (11, 12, 13):
        contact = digits if digits.startswith('55') else f"55{digits}"
    else:
        core = digits[-9:] if len(digits) >= 9 else digits.zfill(8)
        contact = f"5541{core}" if len(core) == 9 and core.startswith('9') else f"55419{core[-8:]}"

    # Mensagem personalizada
    mensagem_body = (
        f"*Olá, {dados['associado'].split()[0]} !*\n\n"
        "*Nova compra ASPMA.*\n"
        "__________________________________\n\n"
        f"🏷️ *_CÓDIGO DA COMPRA_:* {dados['id_compra']}\n"
        "__________________________________\n"
        f"*Convênio:*\n"
        f"{dados['convenio']}\n\n"
        f"*Valor Total  :* R$ {dados['valor_total']}\n"
        f"*N° parcelas :* {dados['nr_parcelas']}\n"
        f"*Valor da Parcela :* R$ {dados['valor_parcela']}\n"
    )

    payload = {
        'apikey': apikey,
        'phone_number': sender,
        'contact_phone_number': contact,
        'message_type': 'text',
        'message_body': mensagem_body
    }

    session = _requests_retry_session(allowed_methods=None)
    try:
        # de-dup simples por (pre, contato, id_compra)
        if not _should_send('pre', contact, dados.get('id_compra')):
            print('[WhatsApp] Pré-venda já enviada recentemente (dedup).')
            return False
        resp = session.post(api_url, json=payload, timeout=(10, 10))
        if resp.ok:
            print('[WhatsApp] Pré-venda enviada.')
            _record_sent('pre', contact, dados.get('id_compra'))
            return True
        snippet = ''
        try:
            snippet = resp.text[:200]
        except Exception:
            snippet = '<sem corpo>'
        print(f"[WhatsApp] Falha pré-venda (status={resp.status_code}): {snippet}")
        return False
    except requests.RequestException as error:
        print(f"[WhatsApp] Erro pré-venda: {error}")
        return False

class Grava_Vendas_Senha(Resource):
    @jwt_required()
    def post(self):
        if not is_connected_to_internet():
            return {'msg': 'Verifique sua conexão com a Internet!'}

        payload = request.json
        dados_venda = dict(payload.get('dados', {}))
        user_info = get_jwt_identity()

        # Verifica se o JWT é um dicionário ou uma string
        if isinstance(user_info, dict):
            codigo_convenio = user_info.get('codigo')
            nome_convenio = user_info.get('nome_razao')
            usuario = user_info.get('usuario')
        else:
            codigo_convenio = user_info
            nome_convenio = ''
            usuario = ''

        sequencia = dados_venda.get('sequencia')
        data_hora = datetime.now(timezone('America/Sao_Paulo')).strftime('%d-%m-%Y %H:%M')

        try:
            valor_total = Decimal(dados_venda.get('valor', '0').replace('.', '').replace(',', '.')).quantize(Decimal('0.01'))
            nr_parcelas = int(dados_venda.get('nr_parcelas', 1))
            valor_parcela = (valor_total / nr_parcelas).quantize(Decimal('0.01'))
        except Exception:
            return {'msg': 'Erro ao calcular valores. Verifique os dados enviados.'}

        saldo = dados_venda.get('saldo')
        if saldo == 'Falhou':
            return {'msg': 'Operação não concluída! Tente novamente.'}
        if isinstance(saldo, float):
            saldo = round(saldo, 2)
        if saldo < float(valor_parcela):
            return {'msg': 'Saldo insuficiente!'}

        mes_inicial = dados_venda.get('mes')
        ano_inicial = dados_venda.get('ano')
        mes_final = mes_inicial
        ano_final = ano_inicial

        if int(dados_venda.get('tipo')) == 1 and not grava_venda_zetra(dados_venda, f"{valor_parcela:.2f}"):
            return {'msg': 'Servidor ZETRA indisponível. Repita o processo!'}

        for i in range(1, nr_parcelas):
            mes_final += 1
            if mes_final > 12:
                mes_final = 1
                ano_final += 1

        dados_insercao = {
            'matricula': dados_venda.get('matricula'),
            'nome_socio': dados_venda.get('associado'),
            'celular': dados_venda.get('celular'),
            'consignataria': dados_venda.get('tipo'),
            'sequencia': sequencia,
            'nr_parcelas': nr_parcelas,
            'valor_total': f"{valor_total:.2f}",
            'valor_parcela': f"{valor_parcela:.2f}",
            'codigo_convenio': codigo_convenio,
            'nome_convenio': nome_convenio,
            'usuario': usuario,
            'data_hora': data_hora,
            'mes_inicial': mes_inicial,
            'ano_inicial': ano_inicial,
            'mes_final': mes_final,
            'ano_final': ano_final
        }

        saldo_restante = saldo - float(valor_parcela)
        format_decimal(saldo_restante, format="#,##0.00;-#", locale='pt_BR')

        if grava_mysql(dados_insercao):
            db['conta_senha_convenio'].delete_one({'matricula': dados_venda.get('matricula')})
            sent = envia_sg_mensagem(dados_insercao['celular'], saldo_restante, dados_venda.get('id_compra'))
            return {'msg': 'Venda WhatsApp', 'whatsapp_confirm_sent': bool(sent)}

        exclui_zetra(dados_venda)
        return {'msg': 'Operação não concluída! Tente novamente.'}

def envia_sg_mensagem(celular, saldo, id_compra):
    """
    Envia a 2ª mensagem (confirmação) via WhatsGw.
    - Usa credenciais do settings (sem hard-code): WHATSGW_API_KEY, WHATSGW_SENDER, WHATSGW_API_URL (opcional)
    - Normaliza o telefone recebendo 8, 9, 10, 11 ou já com 55...
    - Retorna True/False, com logs discretos de falha
    """
    # Configurações (feature-flag simples: se faltar chave/remetente, não envia)
    api_url = getattr(settings, 'WHATS_GW_API_URL', 'https://app.whatsgw.com.br/api/WhatsGw/Send') if settings else 'https://app.whatsgw.com.br/api/WhatsGw/Send'
    apikey = getattr(settings, 'WHATS_GW_APIKEY', None) if settings else None
    sender = getattr(settings, 'WHATS_GW_SENDER', None) if settings else None

    # feature-flag global
    if settings and hasattr(settings, 'WHATSAPP_ENABLED') and not getattr(settings, 'WHATSAPP_ENABLED'):
        print('[WhatsApp] Envio desativado (WHATSAPP_ENABLED=false).')
        return False
    # feature-flag por etapa (confirmação)
    if os.getenv('WHATSAPP_SEND_CONFIRM', 'true').lower() not in ('1','true','yes'):
        print('[WhatsApp] Envio de confirmação desativado por WHATSAPP_SEND_CONFIRM=false.')
        return False

    if not apikey or not sender:
        print('[WhatsApp] Envio desativado: credenciais ausentes no settings (WHATS_GW_APIKEY/WHATS_GW_SENDER).')
        return False

    # Normalização do telefone do contato
    digits = re.sub(r"\D", "", str(celular or ''))
    contact = None
    try:
        if len(digits) == 8:
            # Padrão legado: 8 dígitos armazenados; prefixa DDI+DDD+9
            contact = f"55419{digits}"
        elif len(digits) == 9:
            # 9 dígitos, assume já inclui o 9; prefixa DDI+DDD
            contact = f"5541{digits}"
        elif len(digits) == 10:
            # DDD + 8 dígitos
            contact = f"55{digits[:2]}9{digits[2:]}"
        elif len(digits) in (11, 12, 13):
            # 11: DDD + 9 dígitos; 13: já com 55DDDN...
            contact = digits if digits.startswith('55') else f"55{digits}"
        else:
            # Fallback seguro
            core = digits[-9:] if len(digits) >= 9 else digits.zfill(8)
            if len(core) == 9 and core.startswith('9'):
                contact = f"5541{core}"
            else:
                contact = f"55419{core[-8:]}"
    except Exception:
        contact = f"55419{digits[-8:].zfill(8)}"

    saldo_fmt = format_decimal(saldo, format="#,##0.00;-#", locale='pt_BR')

    mensagem_body = (
        f"🏷️ *_COMPRA :_* {id_compra}\n"
        f"*_CONCLUÍDA COM SUCESSO!_*\n"
        "_____________________________________\n"
        f"💳 *Saldo Restante :* R$ {saldo_fmt}\n\n"
        "*Extrato completo disponível em:*\n"
        "https://aspma.vercel.app"
    )

    payload = {
        'apikey': apikey,
        'phone_number': sender,              # remetente (número da conta)
        'contact_phone_number': contact,     # destinatário normalizado
        'message_type': 'text',
        'message_body': mensagem_body
    }

    # Usa sessão com retry/timeout
    session = _requests_retry_session(allowed_methods=None)
    try:
        # de-dup simples por (confirm, contato, id_compra)
        if not _should_send('confirm', contact, id_compra):
            print('[WhatsApp] Confirmação já enviada recentemente (dedup).')
            return False
        resp = session.post(api_url, json=payload, timeout=(10, 10))
        if resp.ok:
            print('[WhatsApp] Confirmação enviada.')
            _record_sent('confirm', contact, id_compra)
            return True
        # log discreto de falha
        snippet = ''
        try:
            snippet = resp.text[:200]
        except Exception:
            snippet = '<sem corpo>'
        print(f"[WhatsApp] Falha no envio (status={resp.status_code}): {snippet}")
        return False
    except requests.RequestException as error:
        print(f"[WhatsApp] Erro na requisição: {error}")
        return False

class Conta_Senha_Convenio(Resource):
    @jwt_required()
    def post(self):
        if not is_connected_to_internet():
            return {'msg': 'Verifique sua conexão com a Internet!'}

        payload = request.json
        dados_requisicao = dict(payload.get('dados', {}))
        matricula = dados_requisicao.get('matricula')

        if not matricula:
            return {'msg': 'Matrícula não informada.'}

        associado = fetch_user_by_matricula(matricula)
        colecao_conta = db['conta_senha_convenio']
        registro_conta = colecao_conta.find_one({'matricula': matricula})

        if registro_conta:
            if registro_conta.get('conta') == 5 and associado.get('bloqueio') == 'X':
                return {'msg': 'Senha bloqueada! Informe a A.S.P.M.A.'}
            nova_contagem = registro_conta.get('conta', 0) + 1
        else:
            nova_contagem = 1

        try:
            colecao_conta.find_one_and_update(
                {'matricula': matricula},
                {"$set": {'matricula': matricula, 'conta': nova_contagem}},
                upsert=True
            )
        except Exception as e:
            print(f"Erro ao atualizar MongoDB: {e}")
            return {'msg': 'Operação não concluída! Tente novamente.'}

        if nova_contagem >= 5:
            try:
                connection = pymysql.connect(**connection_properties)
                print('Conexão com MySQL estabelecida.')
            except pymysql.err.OperationalError:
                print("Falha ao conectar ao banco de dados.")
                return {'msg': 'Erro ao bloquear senha. Tente novamente.'}

            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE socios SET bloqueio = 'X' WHERE matricula = %s",
                        (matricula,)
                    )
                    connection.commit()
            except Exception as e:
                print(f"Erro ao atualizar MySQL: {e}")
                return {'msg': 'Erro ao bloquear senha no sistema.'}
            finally:
                connection.close()

        return {'msg': nova_contagem}

def grava_venda_zetra(dados, valor_parcela):
    requisicao_data = {
        "cliente": "ASPMA",
        "convenio": "ASPMA-ARAUCARIA",
        "usuario": "aspma_xml",
        "senha": "dcc0bd05",
        "matricula": dados.get('matricula_atual'),
        "cpf": dados.get('cpf'),
        "valorParcela": valor_parcela,
        "valorLiberado": valor_parcela,
        "prazo": int(dados.get('nr_parcelas', 1)),
        "codVerba": "441",
        "servicoCodigo": "018",
        "adeIdentificador": f"M{dados.get('matricula_atual', '').strip()}S{dados.get('sequencia', '').strip()}"
    }

    # Corrigido: substitui method_whitelist por allowed_methods
    session = _requests_retry_session(allowed_methods=None)

    try:
        resposta = session.post(
            "http://200.98.112.240/aspma/php/zetra/reservarMargemZetra.php",
            params=requisicao_data,
            verify=False,
            timeout=(10, 10)
        )

        match = re.search(r"<ns10:mensagem>(.+?)</", resposta.text)
        mensagem = match.group(1) if match else None

        if not mensagem:
            return False

        if len(mensagem) in (31, 32, 33) or mensagem.endswith("realizada com sucesso."):
            return True

        return False

    except Exception as e:
        print(f"Erro ao gravar venda ZETRA: {e}")
        return False


def exclui_zetra(dados):
    requisicao_data = {
        "cliente": "ASPMA",
        "convenio": "ASPMA-ARAUCARIA",
        "usuario": "aspma_xml",
        "senha": "dcc0bd05",
        "adeIdentificador": f"M{dados['matricula_atual']}S{dados['sequencia']}",
        "codigoMotivoOperacao": "99",
        "obsMotivoOperacao": "aspma"
    }

    # Corrigido: substitui method_whitelist por allowed_methods
    session = _requests_retry_session(allowed_methods=None)

    try:
        resposta = session.post(
            'http://200.98.112.240/aspma/php/zetra/reservarExluirZetra.php',
            params=requisicao_data,
            verify=False,
            timeout=(10, 10)
        )

        match = re.search(r'<ns10:mensagem>(.+?)</', resposta.text)
        mensagem = match.group(1) if match else None

        if not mensagem or not mensagem.endswith('sucesso.'):
            return False

        return True

    except Exception as e:
        print(f"Erro ao excluir ZETRA: {e}")
        return False

def consulta_zetra(dados):
    requisicao_data = {
        "cliente": "ASPMA",
        "convenio": "ASPMA-ARAUCARIA",
        "usuario": "aspma_xml",
        "senha": "dcc0bd05",
        "matricula": dados.get('matricula_atual'),
        "cpf": dados.get('cpf'),
        "adeIdentificador": "M374401S420"  # Pode ser dinâmico se necessário
    }

    # Corrigido: substitui method_whitelist por allowed_methods
    session = _requests_retry_session(allowed_methods=None)

    try:
        resposta = session.post(
            "http://200.98.112.240/aspma/php/zetra/consultarConsignacaoZetra.php",
            params=requisicao_data,
            verify=False,
            timeout=(10, 10)
        )
        return True

    except Exception as e:
        print(f"Erro ao consultar ZETRA: {e}")
        return False
