from distutils import core
from lib2to3.refactor import _identity

from flask_restful import Resource

from flask_jwt_extended import (create_access_token, create_refresh_token, jwt_required,
                                get_jwt_identity)

from bcrypt import checkpw, gensalt, hashpw

from flask import jsonify, request

from bson.json_util import dumps

from bson.objectid import ObjectId

import json

import pymongo

import pymysql

import re

from datetime import date, datetime

from babel.numbers import format_decimal

import requests
from requests.adapters import HTTPAdapter, Retry

import string
import random

import bcrypt
from bcrypt import checkpw, gensalt, hashpw

from os import environ

from flask_mail import Mail, Message

#--------------------------------------------------------------------------------------------#

connection_properties = {
    'host': '192.168.0.4',
    'port': 3306,
    'user': 'eliascordeiro',
    'passwd': 'D24m0733@!',
    'db': 'aspma_convenios_teste'
}

'''
connection_properties = {
    'host': '200.98.112.240',
    'port': 3306,
    'user': 'eliascordeiro',
    'passwd': 'D24m0733@!',
    'db': 'aspma_convenios_teste'
}
'''

'''
connection_properties = {
    'host': 'localhost',
    'port': 3306,
    'user': 'araudata',
    'passwd': 'D24m07@!',
    'db': 'aspma_teste_00'
}
'''

#--------------------------------------------------------------------------------------------#

# atlas 'mongodb+srv://araudata:elias157508@cluster0.ubjre.mongodb.net/consigexpress?retryWrites=true&w=majority')

# heroku

client = pymongo.MongoClient(
    "mongodb://araudata:d24m07.ana@consigexpress.mongodb.uhserver.com:27017/consigexpress")
db = client.consigexpress

# local

#mongo = pymongo.MongoClient()
#db = mongo['consigexpress']

#--------------------------------------------------------------------------------------------#


def id_generator(size=6, chars=string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def _requests_retry_session(
        retries=5,
        backoff_factor=3,
        status_forcelist=(500, 502, 503, 504),
        session=None, **kwargs) -> requests.Session:
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session


def internet():
    url = 'http://www.google.com/'
    timeout = 5
    try:
        _ = requests.get(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        return False

#---------------------------------------------------------------------------------#

# variaveis globais


corte = 9

#---------------------------------------------------------------------------------#


class Login_Convenio_Teste(Resource):
    def post(self):

        _json = request.json

        _dados = dict(_json['dados'])

        _data = datetime.now()
        _mes_ano = _data.strftime('%m-%Y')

        # captcha_response = _dados['catchaResponse']

        _cl = db['login_convenios']

        _find = _cl.find_one({'usuario': _dados['usuario']})
        
        try:
            # and is_human(captcha_response):
            if checkpw(_dados['senha'].encode('utf8'), _find["senha"]):

                dados = {'codigo': _find['codigo'],
                         'nome_razao': _find['nomerazao'],
                         'usuario': _find['usuario'].lower(),
                         'email': _find['email'],
                         'cpf_cnpj': _find['cpf_cnpj'],
                         'fantasia': _find['fantasia'],
                         'desconto': _find['desconto'],
                         'parcelas': _find['parcelas'],
                         'mes_ano': _mes_ano}

                access_token = create_access_token(identity=dados)
                refresh_token = create_refresh_token(identity=dados)

                return {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'dados': dados
                }
            else:
                return
        except:    

            try:
                con = pymysql.connect(**connection_properties)
                print('conectou')
            except pymysql.err.OperationalError:
                return {'error': 'Falha na conexão... Tente novamente!'}

            try:

                with con.cursor() as cur:

                    cur.execute("SELECT TRIM(convenio.codigo), convenio.razao_soc, convenio.fantasia, convenio.cgc, convenio.email, convenio.libera, convenio.desconto, convenio.parcelas FROM convenio WHERE TRIM(convenio.usuario) = " +
                            "'" + _dados['usuario'].upper() + "'" + " AND TRIM(convenio.senha) = " + "'" + _dados['senha'].strip() + "'")

                    rows = cur.fetchall()

                for row in rows:
                    __dados = {'codigo': row[0],
                               'nome_razao': row[1],
                               'usuario': _dados['usuario'].lower(),
                               'email': row[4].lower(),
                               'cpf_cnpj': row[3],
                               'fantasia': row[2],
                               'desconto': row[6],
                               'parcelas': row[7],
                               'mes_ano': _mes_ano
                               }

                access_token = create_access_token(identity=__dados)
                refresh_token = create_refresh_token(identity=__dados)

                if row[0]:  # and is_human(captcha_response):
                    _cl = db['login_convenios']

                    _find = _cl.find_one({'codigo': row[0]})

                    if not _find:
                        _cl.find_one_and_update({'codigo': row[0]}, {
                            "$set": {
                            'codigo': row[0],
                            'nomerazao': row[1],
                            'fantasia': row[2],
                            'desconto': row[6],
                            'parcelas': row[7],
                            'cpf_cnpj': row[3],
                            'email': row[4].lower(),
                            'tipo': 'banco' if row[5] == 'X' else 'comercio',
                            'usuario': _dados['usuario'].lower(),
                            'senha': hashpw(_dados['senha'].encode('utf8'), gensalt()),
                            'bloqueio': 'NAO'
                        }}, upsert=True)

                    return {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'dados': __dados
                    }

            finally:

                con.close()

        return {'error': 'Credenciais inválidas!'}


def is_human(captcha_response):

    secret = "6Ld-PwUcAAAAAC8xSRntYWBpRI4nLffIkbYxkyR-"

    payload = {'response': captcha_response, 'secret': secret}
    response = requests.post(
        "https://www.google.com/recaptcha/api/siteverify", payload)

    response_text = json.loads(response.text)

    return response_text['success']


class Receber_Mensal_Teste(Resource):
    @jwt_required()
    def post(self):

        _json = request.json
        _mes_ano = _json["mes_ano"]

        _id = get_jwt_identity()

        _codigo = _id['codigo']

        _data = "'" + _mes_ano[-4:] + '-' + _mes_ano[:2] + '-' + '07' + "'"

        try:
            con = pymysql.connect(**connection_properties)
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        try:

            with con.cursor() as cur:

                cur.execute(
                    "SELECT desconto FROM convenio WHERE codigo = " + _codigo.strip())

                _rows = cur.fetchall()

                _desconto = 0.00

                for _row in _rows:
                    _desconto = _row[0]

                cur.execute("SELECT vendas.id, vendas.associado, vendas.emissao, vendas.parcelas, vendas.valorparcela, vendas.cancela FROM vendas " +
                            "WHERE vendas.valorparcela > 0 AND vendas.cancela='' AND TRIM(vendas.codconven)= " +
                            _codigo.strip() + " AND DATE(" + _data + ") BETWEEN " +
                            "if( day(vendas.emissao) > " + str(corte) + ", DATE( DATE_ADD( CONCAT(LEFT(vendas.emissao,8),'04'), INTERVAL 30 DAY)), DATE( CONCAT(LEFT(vendas.emissao,8),'04') ) ) AND " +
                            "if( day(vendas.emissao) > " + str(corte) + ", DATE( DATE_ADD( DATE_ADD( CONCAT( LEFT(vendas.emissao,8),'04'), INTERVAL 30 DAY), INTERVAL (vendas.parcelas) * 30 DAY) ), DATE( DATE_ADD( CONCAT(LEFT(vendas.emissao,8),'04'), INTERVAL (vendas.parcelas) * 30 DAY) ) ) " +
                            "ORDER BY vendas.associado, vendas.emissao")

                rows = cur.fetchall()

                _campos = {}
                _res = []
                _total = 0

                for row in rows:
                    
                    _dia = int(row[2].strftime("%d"))
                    _mes = int(row[2].strftime("%m"))
                    _ano = int(row[2].strftime("%Y"))
                    
                    n_parcela = 1
                    
                    if _dia > corte:
                        if _mes == 12:
                           _mes = 1
                           _ano = _ano + 1
                        else:
                           _mes = _mes + 1
                           _ano = _ano
                           
                    mes_ano_inicial = str(_mes).zfill(2) + '-' + str(_ano).zfill(4)
                    
                    for _n in range(1,int(row[3])):
                        
                        if _mes == 12:
                           _mes = 1
                           _ano = _ano + 1
                        else:
                           _mes = _mes + 1
                           _ano = _ano
                           
                        if _mes_ano[:2] == str(_mes).zfill(2):
                            n_parcela = _n+1
                           
                    mes_ano_final = str(_mes).zfill(2) + '-' + str(_ano).zfill(4)
                    
                    _campos['periodo'] =  mes_ano_inicial + ' a ' + mes_ano_final
                    _campos['n_parcela'] =  n_parcela
                    
                    _campos['id'] = row[0]
                    _campos['Nome'] = row[1]
                    _campos['Data'] = row[2].strftime("%d-%m-%Y")
                    _campos['Parcelas'] = str(int(row[3])).strip()
                    _campos['Valor'] = format_decimal(
                        row[4], format="#,##0.00;-#", locale='pt_BR')

                    _res.append(dict(_campos))

                    _total += row[4]

        finally:

            con.close()

        __total = format_decimal(_total, format="#,##0.00;-#", locale='pt_BR')

        __desconto = format_decimal(
            _total/100*_desconto, format="#,##0.00;-#", locale='pt_BR')

        __receber = format_decimal(
            _total - (_total/100*_desconto), format="#,##0.00;-#", locale='pt_BR')

        retorno = {'dados': dumps(_res), 'total': __total,
                   'desconto': __desconto, 'receber': __receber}

        return retorno


class Compras_Mensal_Teste(Resource):
    @jwt_required()
    def post(self):

        _json = request.json

        _mes_ano = _json["mes_ano"]

        _id = get_jwt_identity()

        _codigo = _id['codigo']

        try:
            con = pymysql.connect(**connection_properties)
            print('conectou')
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        try:

            with con.cursor() as cur:

                cur.execute("SELECT vendas.emissao, TRIM(vendas.associado), vendas.parcelas, vendas.valorparcela, vendas.id FROM vendas WHERE vendas.valorparcela > 0 AND vendas.cancela = '' AND TRIM(vendas.codconven) = " +
                            _codigo + " AND YEAR(vendas.emissao) = " + _mes_ano[-4:] + " AND MONTH(vendas.emissao) = " + _mes_ano[:2] + " ORDER BY vendas.id desc, vendas.associado")

                rows = cur.fetchall()

                _campos = {}
                _res = []
                _total = 0

                for row in rows:

                    _dia = int(row[0].strftime("%d"))
                    _mes = int(row[0].strftime("%m"))
                    _ano = int(row[0].strftime("%Y"))
                    
                    
                    if _dia > corte:
                        if _mes == 12:
                           _mes = 1
                           _ano = _ano + 1
                        else:
                           _mes = _mes + 1
                           _ano = _ano
                           
                    mes_ano_inicial = str(_mes).zfill(2) + '-' + str(_ano).zfill(4)

                    for _n in range(1,int(row[2])):
                        if _mes == 12:
                           _mes = 1
                           _ano = _ano + 1
                        else:
                           _mes = _mes + 1
                           _ano = _ano
                           
                    mes_ano_final = str(_mes).zfill(2) + '-' + str(_ano).zfill(4)
                    
                    _campos['periodo'] =  mes_ano_inicial + ' a ' + mes_ano_final
                    

                    _campos['Data'] = row[0].strftime("%d-%m-%Y")
                    _campos['Nome'] = row[1]
                    _campos['Parcelas'] = str(int(row[2])).strip()
                    _campos['Valor'] = format_decimal(row[3], format="#,##0.00;-#", locale='pt_BR')
                    _campos['id'] = row[4]

                    _res.append(dict(_campos))

                    _total += row[3]

        finally:

            con.close()

        _total = format_decimal(_total, format="#,##0.00;-#", locale='pt_BR')

        retorno = {'dados': dumps(_res), 'total': _total}

        return retorno

#-----------------------------------------------------------------------------------------------#


class Autenticacao_Teste(Resource):
    @jwt_required()
    def post(self):

        _json = request.json

        _id = get_jwt_identity()

        _codigo = _id['codigo']

        _dados = dict(_json['dados'])

        _cl = db['login_convenios']

        _find = _cl.find_one({'codigo': _codigo})

        if _find['bloqueio'] == 'SIM':
            return {'msg': 'Senha bloqueada... para desbloquear accesse [Alterar Senha]'}

        if _find and checkpw(_dados['senha'].encode('utf8'), _find["senha"]):

            _cl = db['tentativas_convenio']
            _cl.find_one_and_delete({'codigo': _codigo})

            return {'msg': 'ok'}

        _tentativas = 1

        _cl = db['tentativas_convenio']

        _find = _cl.find_one({'codigo': _codigo})

        if _find:
            _tentativas = _find['tentativas'] + 1

            if _tentativas == 3:
                __cl = db['login_convenios']

                __cl.find_one_and_update({'codigo': _codigo}, {
                    "$set": {
                        'bloqueio': 'SIM'
                    }}, upsert=True)

        _cl.find_one_and_update({'codigo': _codigo}, {
            "$set": {
                'tentativas': _tentativas
            }}, upsert=True)

        return {'msg': 'Senha inválida! Tentativa ' + str(_tentativas) + ' de 3.'}
#-----------------------------------------------------------------------------------------------#


class Grava_Vendas_Teste(Resource):
    @jwt_required()
    def post(self):

        if not internet():
            return {'msg': 'Verifique sua conexão com a Internet!'}

        _json = request.json

        _id = get_jwt_identity()

        _dados = dict(_json['dados'])

        _cl = db['codigo_para_compra']

        _find = _cl.find_one(
            {'codigo': _dados['codigo']})

        if not _find:
            return {'msg': 'Código da Compra Inválido!'}

        # _exclui = liquida_consig_teste()

        # return _exclui

        busca_limite = limite(_find)

        _sequencia = busca_limite['sequencia']

        _data_hora = datetime.now().strftime('%d-%m-%Y %H:%M')

        _valor = _dados['valor'].replace('.', '')
        _valor = float(_valor.replace(',', '.'))
        
        _valor = round(_valor,2)
        
        _valor_parcela = float(_valor )
        _valor_parcela = _valor_parcela / int(_dados['nr_parcelas'])
        _valor_parcela = round(_valor_parcela,2)
        
        if busca_limite['saldo'] == 'Falhou':
            return {'msg': 'Operação não concluída! Tente novamente.'}
        elif busca_limite['saldo'] < _valor_parcela:
            return {'msg': 'Saldo insufíciente!'}

        _mt = _find['matricula']
        _ct = 'M' + str(_find['matricula']) + 'S' + _sequencia
        _np = int(_dados['nr_parcelas'])

        data = {"matricula": _mt,
                "sequencia": _ct,
                "qtParcela": _np,
                "vlParcela": _valor_parcela,
                "valorTotal": _valor}

        if int(_find['tipo']) == 1 and not grava_consig(data):
            return {'msg': 'Servidor consig-plus indisponível.. repita o processo!'}

        _valor = "%.2f" % _valor
        _valor_parcela = "%.2f" % _valor_parcela

        lMes = busca_limite['mes']
        lAno = busca_limite['ano']

        mes_inicial = lMes
        ano_inicial = lAno

        for x in range(1, int(_dados['nr_parcelas']) + 1):

            if x != int(_dados['nr_parcelas']):
                lMes = lMes + 1

                if (lMes > 12):
                    lMes = 1
                    lAno = lAno + 1

        dados_insert = {
            'matricula': _find['matricula_aspma'],
            'nome_socio': _find['associado'],
            'consignataria': _find['tipo'],
            'sequencia': _sequencia,
            'codigo_da_compra': _dados['codigo'],
            'nr_parcelas': _dados['nr_parcelas'],
            'valor_total': _valor,
            'valor_parcela': _valor_parcela,
            'codigo_convenio': _id['codigo'],
            'nome_convenio': _id['nome_razao'],
            'usuario': _id['usuario'],
            'data_hora': _data_hora,
            'mes_inicial': mes_inicial,
            'ano_inicial': ano_inicial,
            'mes_final': lMes,
            'ano_final': lAno
        }

        try:
            _cl = db['vendas']
            _cl.insert_one(dados_insert)

        except:
            if int(_find['tipo']) == 1:
                exclui_consig(data)

            return {'msg': 'Operação não concluída! Tente novamente.'}

        if grava_mysql(dados_insert):

            db['codigo_para_compra'].delete_one(
                {'matricula': _find['matricula']})

            return {'msg': 'Operaçao realizada com sucesso!'}

        db['vendas'].delete_one(
            {'matricula': _find['matricula_aspma'], 'sequencia': _sequencia})

        if int(_find['tipo']) == 1:
            exclui_consig(data)

        return {'msg': 'Operação não concluída! Tente novamente.'}

#--------------------------------------------------------------------------------------------#


def exclui_consig(data):

    session = _requests_retry_session(method_whitelist=False)
    # resp = session.post('http://aspmaphp.herokuapp.com/liquida_mobile_consig.php',
    #                    params=data, verify=False, timeout=(10, 10))

    resp = session.post('http://200.98.145.36/aspma/php/liquida_mobile_consig.php',
                        params=data, verify=False, timeout=(10, 10))

    return True
#--------------------------------------------------------------------------------------------#


def limite(find):

    try:
        con = pymysql.connect(**connection_properties)
        print('conectou')
    except pymysql.err.OperationalError:
        print("não conectou")

    _margem = ''
    _total = ''

    x = date.today()

    lMes = x.month
    lAno = x.year

    if x.day > 9:
        if lMes == 12:
            lMes = 1
            lAno = lAno + 1
        else:
            lMes = lMes + 1
            lAno = lAno

    try:

        with con.cursor() as cur:

            cur.execute(
                "SELECT socios.limite,socios.ncompras FROM socios WHERE TRIM(socios.matricula) = " + find['matricula_aspma'])

            rows = cur.fetchall()

            _limite = float(0)

            if rows:
                for row in rows:
                    if row[0] != None:
                        _limite = float(row[0])
                        _sequencia = int(row[1]) + 1
    except:

        return {"saldo": "Falhou"}

    if int(find['tipo']) != 1:

        try:

            with con.cursor() as cur:

                cur.execute("SELECT sum(parcelas.valor) FROM parcelas LEFT JOIN vendas ON parcelas.matricula = vendas.matricula AND parcelas.sequencia = vendas.sequencia WHERE parcelas.valor > 0 AND parcelas.baixa = '' AND vendas.cancela = '' AND TRIM(parcelas.matricula) = " +
                            find['matricula_aspma'] + " AND YEAR(parcelas.vencimento) = " + str(lAno) + " AND month(parcelas.vencimento) = " + str(lMes))

                rows = cur.fetchall()

                _total = float(0)

                if rows:
                    for row in rows:
                        if row[0] != None:
                            _total = float(row[0])

                saldo = _limite - _total

                _ret = {"saldo": float(saldo),
                        "mes": lMes,
                        "ano": lAno,
                        "sequencia": str(_sequencia)}

        except:

            return {"saldo": "Falhou"}

        finally:

            con.close()

    else:

        try:
            mat = str(find['matricula'])

            data = {"matricula": mat}
            
            data = {"cliente": 'ASPMA', "convenio": 'ASPMA-ARAUCARIA', "usuario": 'aspma_xml', "senha": 'dcc0bd05', "matricula" : mat, "cpf": _cpf,  "valorParcela": '1.00'}

            session = _requests_retry_session(method_whitelist=False)

            # resp = session.post('http://aspmaphp.herokuapp.com/teste_margem.php',
            #                    params=data, verify=False, timeout=(10, 10))

            resp = session.post('http://200.98.112.240/aspma/php/consultaMargemZetra.php',
                                params=data, verify=False, timeout=(10, 10))
            
            '''
            _margem = re.search('<margem>(.+?)</', resp.text).group(1)

            _ret = {'saldo': float(_margem),
                    'mes': lMes,
                    'ano': lAno,
                    'sequencia': str(_sequencia)}
            '''

        except:

            return {"saldo": "Falhou"}

    return _ret

#--------------------------------------------------------------------------------------------#


def grava_consig(data):

    session = _requests_retry_session(method_whitelist=False)

    # resp = session.post('http://aspmaphp.herokuapp.com/grava_mobile_consig.php',
    #                    params=data, verify=False, timeout=(10, 10))

    resp = session.post('http://200.98.112.240/aspma/php/zetra/grava_mobile_consig.php',
                        params=data, verify=False, timeout=(10, 10))

    extrai_resp = re.search('<string>(.+?)</', resp.text).group(1)

    if extrai_resp != 'Contrato cadastrado com sucesso!':
        return False

    return True

#--------------------------------------------------------------------------------------------#


def grava_mysql(_dados):

    try:
        con = pymysql.connect(**connection_properties)
        print('ok')
    except pymysql.err.OperationalError:
        print("Não conectou")

    try:

        # vendas

        inserts_vendas = []

        _data_e_hora_atuais = datetime.now()

        campos_vendas = "(matricula,sequencia,emissao,associado,codconven,conveniado,parcelas,autorizado,operador,valorparcela,cancela)"

        dados_vendas = [_dados['matricula'],
                        _dados['sequencia'],
                        _data_e_hora_atuais.strftime('%Y-%m-%d'),
                        _dados['nome_socio'],
                        _dados['codigo_convenio'],
                        _dados['nome_convenio'],
                        _dados['nr_parcelas'],
                        '',
                        '',
                        _dados['valor_parcela'],
                        '']

        inserts_vendas.append(dados_vendas)

        esses_vendas = '('

        for _nx in range(0, len(dados_vendas)):
            esses_vendas += '%s,' if _nx < len(dados_vendas)-1 else '%s)'

        # parcelas

        inserts = []

        lAno = _dados['ano_inicial']
        lMes = _dados['mes_inicial']

        tipo = 'X' if int(_dados['consignataria']) == 1 else ''

        for x in range(1, int(_dados['nr_parcelas']) + 1):

            _vcto = str(lAno).zfill(4) + '-' + \
                str(lMes).zfill(2) + "-" + '01'

            dados = [_dados['matricula'],
                     _dados['sequencia'],
                     int(x),
                     _vcto,
                     _dados['valor_parcela'],
                     _dados['nome_socio'],
                     _dados['codigo_convenio'],
                     _dados['nome_convenio'],
                     _dados['nr_parcelas'],
                     tipo,
                     '']

            inserts.append(dados)

            if x != int(_dados['nr_parcelas']):
                lMes = lMes + 1

                if (lMes > 12):
                    lMes = 1
                    lAno = lAno + 1

        campos = "(matricula, sequencia, nrseq, vencimento, valor, associado, codconven, conveniado, parcelas, tipo, baixa)"

        esses = '('

        for _nx in range(0, len(dados)):
            esses += '%s,' if _nx < len(dados)-1 else '%s)'

        # grava_tudo

        with con.cursor() as cursor:
            cursor.executemany("insert into vendas" +
                               campos_vendas + " values " + esses_vendas, inserts_vendas)

            cursor.executemany("insert into parcelas" +
                               campos + " values " + esses, inserts)

            cursor.execute("update socios set ncompras = " +
                           _dados['sequencia'] + ' where matricula = ' + _dados['matricula'])

            con.commit()
            # exit()

    except:

        return False

    finally:

        con.close()

    return True
#--------------------------------------------------------------------------------------------#


class Envia_Email_Codigo_Teste(Resource):
    @ jwt_required()
    def post(self):

        if not internet():
            return {'msg': 'Verifique sua conexão com a Internet!'}

        mail = Mail()

        _id = get_jwt_identity()

        _cl = db['login_convenios']

        find = _cl.find_one({"codigo": _id['codigo']})

        if find:

            code = id_generator()

            msg = Message('Código de Segurança A.S.P.M.A.',
                          sender='consigexpress@consigexpress.com.br', recipients=[find['email']])

            msg.html = "<p style='font-size: 22px'>INFORME ESTE CÓDIGO QUANDO SOLICITADO: " + code + "</p>"

            mail.send(msg)

            _cl = db['codigo_altera_senha_convenio']

            _cl.find_one_and_update({'codigo_convenio': _id['codigo']}, {
                "$set": {'codigo': code}}, upsert=True)

            return {'msg': 'ok'}

        return {'msg': 'E-Mail não enviado! Verifique seu E-Mail ou atualize seu cadastro.'}

#---------------------------------------------------------------------------------#


class Altera_Senha_Convenio_Teste(Resource):
    @ jwt_required()
    def post(self):

        _json = request.json

        _id = get_jwt_identity()

        _dados = dict(_json['dados'])

        _cl = db['codigo_altera_senha_convenio']

        _find = _cl.find_one(
            {'codigo_convenio': _id['codigo'], 'codigo': _dados['codigo']})

        if not _find:
            return {'msg': 'Código inválido! verifique novamente seu E-Mail ou repita o pŕocesso novamente.'}

        _cl = db['login_convenios']

        _cl.find_one_and_update({'codigo': _id['codigo']}, {
            "$set": {
                'bloqueio': 'NAO',
                'senha': hashpw(_dados['nova_senha'].encode('utf8'), gensalt())
            }}, upsert=True)

        _cl = db['tentativas_convenio']
        _cl.find_one_and_delete({'codigo': _id['codigo']})

        _cl = db['codigo_altera_senha_convenio']
        _cl.delete_one({'codigo_convenio': _id['codigo']})
        
        ## alerar senha mysql

        return {'msg': 'Senha alterada com sucesso!'}


#---------------------------------------------------------------------------------#


class Grava_Regs_Teste(Resource):
    @ jwt_required()
    def post(self):

        _json = request.json

        _id = get_jwt_identity()

        _dados = dict(_json['dados'])

        print(_dados)

        try:
            con = pymysql.connect(**connection_properties)
            print('ok')
        except pymysql.err.OperationalError:
            print("Não conectou")

        try:
            with con.cursor() as cursor:

                cursor.execute(
                    "UPDATE convenio SET usuario = " + "'" + _dados['usuario'] + "'" +
                    ", email = " + "'" + _dados['email'] + "'" +
                    ", cgc = " + "'" + _dados['cpf_cnpj'] + "'" +
                    ", fantasia = " + "'" + _dados['fantasia'] + "'" +
                    ", razao_soc = " + "'" +
                    _dados['nome_razao'] + "'" +
                    " WHERE codigo = " + _id['codigo']
                )

                con.commit()

        except pymysql.err.OperationalError:

            return jsonify({"msg": AttributeError})

        finally:

            con.close()

        _cl = db[_json['tb']]

        _cl.find_one_and_update({'codigo': _id['codigo']}, {
            "$set": {
                'nomerazao': _dados['nome_razao'],
                'fantasia': _dados['fantasia'],
                'cpf_cnpj': _dados['cpf_cnpj'],
                'email': _dados['email'].lower(),
                'usuario': _dados['usuario'].lower(),
                'bloqueio': 'NAO'
            }}, upsert=True)

        return _dados

#--------------------------------------------------------------------------------------------#


class Envia_Email_Codigo_Esqueceu_Teste(Resource):
    def post(self):
        mail = Mail()

        _json = request.json

        _dados = dict(_json['dados'])

        _email = _dados['email'].lower()

        _cl = db['login_convenios']

        find = _cl.find_one({"email": _email})

        if find:

            code = id_generator()

            msg = Message('Código de Segurança A.S.P.M.A.',
                          sender='consigexpress@consigexpress.com.br', recipients=[_email])

            msg.html = "<p style='font-size: 22px'>INFORME ESTE CÓDIGO QUANDO SOLICITADO: " + code + "</p>"

            mail.send(msg)

            _cl = db['codigo_altera_senha_convenio']

            _cl.find_one_and_update({'codigo_convenio': find['codigo']}, {
                "$set": {'codigo': code}}, upsert=True)

            return {'msg': 'ok'}

        return {'msg': 'E-Mail não enviado! Verifique seu E-Mail ou atualize seu cadastro.'}

#---------------------------------------------------------------------------------#


class Altera_Senha_Esqueceu_Convenio_Teste(Resource):
    def post(self):

        _json = request.json

        _dados = dict(_json['dados'])

        _cl = db['codigo_altera_senha_convenio']

        _find = _cl.find_one(
            {'codigo': _dados['codigo']})

        if not _find:
            return {'msg': 'Código inválido! verifique novamente seu E-Mail ou repita o pŕocesso.'}

        _cl = db['login_convenios']

        _cl.find_one_and_update({'codigo': _find['codigo_convenio']}, {
            "$set": {
                'bloqueio': 'NAO',
                'senha': hashpw(_dados['nova_senha'].encode('utf8'), gensalt())
            }}, upsert=True)

        _cl = db['tentativas_convenio']
        _cl.find_one_and_delete({'codigo': _find['codigo_convenio']})

        _cl = db['codigo_altera_senha_convenio']
        _cl.delete_one({'codigo_convenio': _find['codigo_convenio']})

        return {'msg': 'Senha alterada com sucesso!'}


#---------------------------------------------------------------------------------#

def liquida_consig_teste():

    contrato = "M749102S265"

    data = {"matricula": '749102', "sequencia": contrato,
            "qtParcela": '1', "vlParcela": '0.01', "valorTotal": '0.01'}

    session = _requests_retry_session(method_whitelist=False)

    # resp = session.post('http://aspmaphp.herokuapp.com/liquida_mobile_consig.php',
    #                    params=data, verify=False, timeout=(10, 10))

    resp = session.post('http://200.98.145.36/aspma/php/liquida_mobile_consig.php',
                        params=data, verify=False, timeout=(10, 10))

    extrai_resp = re.search('<string>(.+?)</', resp.text).group(1)

    print(extrai_resp)

    return {'msg': extrai_resp}


#--------------------------------------------------------------------------------------------#


def pega_matricula(_matricula):

    _mat = ''
    
    _cl = db['login_socios']
    
    _find = _cl.find_one({'matricula': _matricula})
    
    if _find:
        print(_find['senha'])

    try:
        con = pymysql.connect(**connection_properties)
        print('conectou')
    except pymysql.err.OperationalError:
        print("não conectou")

    try:

        with con.cursor() as cur:

            # cur.execute(
            #    "SELECT matricula_atual FROM matriculas WHERE TRIM(matricula_antiga) = " + _matricula.strip())

            cur.execute(
                "SELECT socios.tipo,socios.limite,socios.ncompras,socios.associado,socios.autorizado,socios.senha,socios.celular,socios.bloqueio,socios.cpf,matriculas.matricula_atual FROM socios LEFT JOIN matriculas ON TRIM(socios.matricula) = TRIM(matriculas.matricula_antiga) WHERE TRIM(socios.matricula) = " + _matricula.strip())

            rows = cur.fetchall()

            for row in rows:

                _mat = {'matricula': _matricula, 
                        'associado': row[3],
                        'tipo': row[0], 
                        'limite': row[1], 
                        'sequencia': row[2]+1, 
                        'autorizados': row[4], 
                        'senha': row[5], 
                        'celular': row[6],
                        'bloqueio': row[7],
                        'cpf': row[8],
                        'matricula_atual': row[9]
                        }

    except:
        
        return 'None'

    finally:

        con.close()

    return json.loads(json.dumps(_mat))

#--------------------------------------------------------------------------------------------#


class Busca_Limite_Teste(Resource):
    @jwt_required()
    def post(self):

        if not internet():
            return {'msg': 'Verifique sua conexão com a Internet!'}

        _json = request.json

        _id = get_jwt_identity()

        _dados = dict(_json['dados'])
        
        """
        _cl = db['conta_senha_convenio']

        _find = _cl.find_one({'matricula': _dados['matricula']})

        if _find and _find['conta'] == 5:
            return {'msg': 'Senha Bloqueada! Execedido o número de Tentativas... Contate a A.S.P.M.A!'}
        """    

        _volta = pega_matricula(_dados['matricula'])
        
        if _volta == '':
            return {'msg': 'Matrícula não encontrada!'}
        
        if _volta['bloqueio'] == 'X':
            return {'msg': 'Senha Bloqueada! Desbloqueio somente na SEDE da A.S.P.M.A.'}
        else:
            db['conta_senha_convenio'].delete_one(
                {'matricula': _dados['matricula']})
        
        #if int(_volta['tipo']) == 1:
            #return {'msg': 'Matrícula não Autorizada... Prefeitura em fase de licitação!'}
        
        _limite = pega_limite(_volta)

        _valor = _dados['valor'].replace('.', '')
        _valor = float(_valor.replace(',', '.'))
        
        _valor = round(_valor,2)
        
        _valor_parcela = float(_valor )
        _valor_parcela = _valor_parcela / int(_dados['nr_parcelas'])
        _valor_parcela = round(_valor_parcela,2)
        
        if _limite['saldo'] < _valor_parcela:
            return {'msg': 'Saldo insuficiente!', 'saldo': _limite['saldo']}

        _limite['valor'] = _dados['valor']
        _limite['nr_parcelas'] = _dados['nr_parcelas']
        _limite['tipo'] = _volta['tipo']
        _limite['senha'] = _volta['senha']
        _limite['autorizados'] = _volta['autorizados']
        _limite['data'] = datetime.now().strftime('%d-%m-%Y %H:%M')
        _limite['valor_total'] = format_decimal(
            _valor, format="#,##0.00;-#", locale='pt_BR'),
        _limite['valor_parcela'] = format_decimal(
            _valor_parcela, format="#,##0.00;-#", locale='pt_BR'),
        _limite['convenio'] = _id['nome_razao']
        _limite['celular'] = _volta['celular']
        _limite['matricula_atual'] = str(_volta['matricula_atual'])
        _limite['cpf'] = _volta['cpf']

        return {'msg': _limite}

#--------------------------------------------------------------------------------------------#


def pega_limite(_items):

    try:
        con = pymysql.connect(**connection_properties)
        print('conectou')
    except pymysql.err.OperationalError:
        print("não conectou")

    _total = ''

    x = date.today()

    lMes = x.month
    lAno = x.year

    if x.day > 9:
        if lMes == 12:
            lMes = 1
            lAno = lAno + 1
        else:
            lMes = lMes + 1
            lAno = lAno

    try:
        
        if int(_items['tipo']) != 1:
            
            with con.cursor() as cur:

                #cur.execute("SELECT sum(parcelas.valor) FROM parcelas LEFT JOIN vendas ON parcelas.matricula = vendas.matricula AND parcelas.sequencia = vendas.sequencia WHERE parcelas.valor > 0 AND parcelas.baixa = '' AND vendas.cancela = '' AND TRIM(parcelas.matricula) = " +
                #           _items['matricula'].strip() + " AND YEAR(parcelas.vencimento) = " + str(lAno) + " AND month(parcelas.vencimento) = " + str(lMes))
            
            
                cur.execute("SELECT sum(parcelas.valor) FROM parcelas WHERE parcelas.valor > 0 AND parcelas.baixa = '' AND TRIM(parcelas.matricula) = " +
                       _items['matricula'].strip() + " AND YEAR(parcelas.vencimento) = " + str(lAno) + " AND month(parcelas.vencimento) = " + str(lMes))

                rows = cur.fetchall()

                _total = float(0)

                if rows:
                    for row in rows:
                        if row[0] != None:
                            _total = float(row[0])
    
                saldo = float(_items['limite']) - _total

                _ret = {"matricula": _items['matricula'],
                        "associado": _items['associado'],
                        "saldo": float(saldo),
                        "mes": lMes,
                        "ano": lAno,
                        "limite": format_decimal(saldo, format="#,##0.00;-#", locale='pt_BR'),
                        "sequencia": str(int(_items['sequencia']))}
        else:
            data = {"cliente": "ASPMA", 
                    "convenio": "ASPMA-ARAUCARIA", 
                    "usuario": "aspma_xml", 
                    "senha": "dcc0bd05", 
                    "matricula" : _items['matricula_atual'], 
                    "cpf": _items['cpf'],  
                    "valorParcela": "1.00"}
    
            session = _requests_retry_session(method_whitelist=False)
 
            resp = session.post('http://200.98.112.240/aspma/php/consultaMargemZetra.php', params=data, verify=False, timeout=(10, 10))
    
            try:
                _margem = re.search('<ns6:valorMargem xmlns:ns6="InfoMargem">(.+?)</', resp.text).group(1)    
                _ret = {"matricula": _items['matricula'],
                        "associado": _items['associado'],
                        "saldo": float(_margem),
                        "mes": lMes,
                        "ano": lAno,
                        "limite": format_decimal(_margem, format="#,##0.00;-#", locale='pt_BR'),
                        "sequencia": str(int(_items['sequencia']))}
                
            except:    
                _ret = {"saldo": "Falhou"}

    except:

        _ret = {"saldo": "Falhou"}

    finally:

        con.close()

    return _ret

#--------------------------------------------------------------------------------------------#



class Grava_Vendas_Senha_Teste(Resource):
    @jwt_required()
    def post(self):

        if not internet():
            return {'msg': 'Verifique sua conexão com a Internet!'}

        _json = request.json

        _id = get_jwt_identity()

        _dados = dict(_json['dados'])

        _sequencia = _dados['sequencia']

        _data_hora = datetime.now().strftime('%d-%m-%Y %H:%M')
        
        _valor = _dados['valor'].replace('.', '')
        _valor = float(_valor.replace(',', '.'))
        
        _valor = round(_valor,2)
        
        _valor_parcela = float(_valor )
        _valor_parcela = _valor_parcela / int(_dados['nr_parcelas'])
        _valor_parcela = round(_valor_parcela,2)
        
        if type(_dados['saldo']) is float:
            _dados['saldo'] = round(_dados['saldo'])
        
        _saldo_restante = _dados['saldo'] - _valor_parcela

        if _dados['saldo'] == 'Falhou':
            return {'msg': 'Operação não concluída! Tente novamente.'}
        elif _dados['saldo'] < _valor_parcela:
            return {'msg': 'Saldo insufíciente!'}

        _valor = "%.2f" % _valor
        _valor_parcela = "%.2f" % _valor_parcela

        lMes = _dados['mes']
        lAno = _dados['ano']

        mes_inicial = lMes
        ano_inicial = lAno
        
        if int(_dados['tipo']) == 1 and not grava_venda_zetra(_dados, _valor_parcela):
            return {'msg': 'Servidor ZETRA indisponível.. repita o processo!'}

        for x in range(1, int(_dados['nr_parcelas']) + 1):

            if x != int(_dados['nr_parcelas']):
                lMes = lMes + 1

                if (lMes > 12):
                    lMes = 1
                    lAno = lAno + 1

        dados_insert = {
            'matricula': _dados['matricula'],
            'nome_socio': _dados['associado'],
            'consignataria': _dados['tipo'],
            'sequencia': _sequencia,
            'nr_parcelas': _dados['nr_parcelas'],
            'valor_total': _valor,
            'valor_parcela': _valor_parcela,
            'codigo_convenio': _id['codigo'],
            'nome_convenio': _id['nome_razao'],
            'usuario': _id['usuario'],
            'data_hora': _data_hora,
            'mes_inicial': mes_inicial,
            'ano_inicial': ano_inicial,
            'mes_final': lMes,
            'ano_final': lAno
        }

        '''
        try:
            _cl = db['vendas']
            _cl.insert_one(dados_insert)

        except:
            return {'msg': 'Operação não concluída! Tente novamente.'}
        '''    

        if grava_mysql(dados_insert):
            db['conta_senha_convenio'].delete_one({'matricula': _dados['matricula']})
            envia_sms(dados_insert, _id['nome_razao'], _dados['celular'], _saldo_restante)
            return {'msg': 'Operaçao realizada com sucesso!'}
        
        exclui_zetra(_dados)

        #db['vendas'].delete_one(
        #    {'matricula': _dados['matricula'], 'sequencia': _sequencia})

        return {'msg': 'Operação não concluída! Tente novamente.'}

#--------------------------------------------------------------------------------------------#


class Conta_Senha_Convenio_Teste(Resource):
    @jwt_required()
    def post(self):

        if not internet():
            return {'msg': 'Verifique sua conexão com a Internet!'}

        _json = request.json
        
        _dados = dict(_json['dados'])
        
        _volta = pega_matricula(_dados['matricula'])
        
        _cl = db['conta_senha_convenio']

        _find = _cl.find_one({'matricula': _dados['matricula']})

        if _find:
            if _find['conta'] == 5 and _volta['bloqueio'] == 'X':
                return {'msg': 'Senha Bloqueada! Informe a A.S.P.M.A.'}

            _conta = _find['conta'] + 1 
        else:
            _conta = 1

        dados_insert = {
            'matricula': _dados['matricula'],
            'conta': _conta
        }

        try:
            _cl = db['conta_senha_convenio']

            _cl.find_one_and_update({'matricula': _dados['matricula']}, {
                "$set":
                    dados_insert
            }, upsert=True)

        except:
            return {'msg': 'Operação não concluída! Tente novamente.'}
        
        if _conta >= 5:
            
            try:
                con = pymysql.connect(**connection_properties)
                print('conectou')
            except pymysql.err.OperationalError:
                print("não conectou")

            try:

                with con.cursor() as cur:
                    
                    cur.execute("update socios set bloqueio = 'X' where matricula = " + _dados['matricula'])

                    con.commit()

            except:

                return False

            finally:

                con.close()
            

        return {'msg': _conta}

#--------------------------------------------------------------------------------------------#

def envia_sms(_dados,_convenio,_celular,_saldo):
    
    _vl_parcelas = format_decimal(float(_dados['valor_parcela']), format="#,##0.00;-#", locale='pt_BR')
    _saldo = format_decimal(float(_saldo), format="#,##0.00;-#", locale='pt_BR')
    
    iSenha = "send"
    iCodigo = "dg7bLOD3ic"
    iUser = "aspma"
    iCelular = "5541" + _celular[-9:].replace(' ','')
    iMsg = "A.S.P.M.A informa! Matricula utilizada em: " + _convenio + \
           " Valor: " + _dados['nr_parcelas'] + " X " + _vl_parcelas + \
           " Saldo restante: " + _saldo #+ " Extrato completo em: aspma.vercel.app"
    
    url = "http://system.human.com.br:8080/GatewayIntegration/msgSms.do?dispatch=" + \
        iSenha+"&account="+iUser+"&code="+iCodigo+"&to="+iCelular+"&msg="+iMsg

    data = requests.get(url).json
    
    return True

#--------------------------------------------------------------------------------------------#

def grava_venda_zetra(dados, valor_parcela):
    
    #exclui_zetra(dados)
    
    #return False
    
    data = {"cliente": "ASPMA", 
            "convenio": "ASPMA-ARAUCARIA", 
            "usuario": "aspma_xml", 
            "senha": "dcc0bd05", 
            "matricula" : dados['matricula_atual'], 
            "cpf": dados['cpf'],  
            "valorParcela": valor_parcela,
            "valorLiberado": valor_parcela,
            "prazo": int(dados['nr_parcelas']),
            "codVerba": '441',
            "servicoCodigo": '018',
            "adeIdentificador": 'M' + dados['matricula_atual'].strip() + 'S' + dados['sequencia'].strip()}
    
    session = _requests_retry_session(method_whitelist=False)

    resp = session.post('http://200.98.112.240/aspma/php/zetra/reservarMargemZetra.php',
                        params=data, verify=False, timeout=(10, 10))

    try:
        extrai_resp = re.search('<ns10:mensagem>(.+?)</', resp.text).group(1)
    except:    
        return False
    
    if extrai_resp[-8:] != 'sucesso.':
       return False

    return True

#--------------------------------------------------------------------------------------------#

def exclui_zetra(dados):
    
    data = {"cliente": "ASPMA", 
            "convenio": "ASPMA-ARAUCARIA", 
            "usuario": "aspma_xml", 
            "senha": "dcc0bd05", 
            "adeIdentificador": 'M' + dados['matricula_atual'] + 'S' + dados['sequencia'],
            "codigoMotivoOperacao": "99",
            "obsMotivoOperacao": "aspma"}
    
    session = _requests_retry_session(method_whitelist=False)

    resp = session.post('http://200.98.112.240/aspma/php/zetra/reservarExluirZetra.php',
                        params=data, verify=False, timeout=(10, 10))

    try:
        extrai_resp = re.search('<ns10:mensagem>(.+?)</', resp.text).group(1)
    except:    
        return False
    
    if extrai_resp[-8:] != 'sucesso.':
       return False

    return True

#--------------------------------------------------------------------------------------------#

def consulta_zetra(dados):
    
    data = {"cliente": "ASPMA", 
            "convenio": "ASPMA-ARAUCARIA", 
            "usuario": "aspma_xml", 
            "senha": "dcc0bd05", 
            "matricula" : dados['matricula_atual'], 
            "cpf": dados['cpf'],  
            "adeIdentificador": "M374401S420"}
    
    session = _requests_retry_session(method_whitelist=False)

    resp = session.post('http://200.98.112.240/aspma/php/zetra/consultarConsignacaoZetra.php',
                        params=data, verify=False, timeout=(10, 10))
    
    print(resp.text)

    return True

#--------------------------------------------------------------------------------------------#
