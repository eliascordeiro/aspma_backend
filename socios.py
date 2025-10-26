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

from datetime import date, datetime, timedelta

from babel.numbers import format_decimal

import requests
from requests.adapters import HTTPAdapter, Retry

import string
import random

import bcrypt
from bcrypt import checkpw, gensalt, hashpw

from os import environ

import socket

from flask_mail import Mail, Message

from pytz import timezone

'''
connection_properties = {
    'host': '200.98.112.240',
    'port': 3306,
    'user': 'eliascordeiro',
    'passwd': 'D24m0733@!',
    'db': 'aspma'
}
'''

"""
connection_properties = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'araudata',
    'passwd': 'D24m07@!',
    'db': 'aspma'
}
"""

#remoto

connection_properties = {
    'host': '192.168.0.4',
    'port': 3306,
    'user': 'eliascordeiro',
    'passwd': 'D24m0733@!',
    'db': 'aspma'
}

#--------------------------------------------------------------------------------------------#

# heroku

client = pymongo.MongoClient(
    "mongodb://araudata:d24m07.ana@consigexpress.mongodb.uhserver.com:27017/consigexpress")
# 'mongodb+srv://araudata:elias157508@cluster0.ubjre.mongodb.net/consigexpress?retryWrites=true&w=majority')
db = client.consigexpress


# local

# mongo = pymongo.MongoClient()
# db = mongo['consigexpress']
#--------------------------------------------------------------------------------------------#

def internet():
    url = 'http://www.google.com/'
    timeout = 5
    try:
        _ = requests.get(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        return False


# variaveis globais
corte = 9


class UserRegistration(Resource):
    def post(self):

        _json = request.json

        _json['cpf']

        if Credenciais.query.filter(Credenciais.cpfcnpj == _json['cpf']).first():
            return {"error": "Usuário já cadastrado!"}

        u = Credenciais(cpfcnpj=_json['cpf'], senha=hashpw(
            _json["senha"].encode('utf8'), gensalt()))
        u.save()

        access_token = create_access_token(identity=_json['cpf'])
        refresh_token = create_refresh_token(identity=_json['cpf'])

        return {
            'cpfcnpj': _json['cpf'],
            'access_token': access_token,
            'refresh_token': refresh_token
        }


class UserLogin(Resource):
    def post(self):

        _json = request.json

        _cl = db['credenciais']

        current_user = _cl.find_one({'cpfcnpj': _json['cpf']})

        if not current_user:
            return {"error": "Usuário não cadastrado!"}

        if checkpw(_json['senha'].encode('utf8'), current_user['senha']):

            access_token = create_access_token(identity=_json['cpf'])
            refresh_token = create_refresh_token(identity=_json['cpf'])

            return {
                'cpfcnpj': current_user['cpfcnpj'],
                'access_token': access_token,
                'refresh_token': refresh_token,
                'nomerazao': current_user['nomerazao']
            }
        else:
            return {'error': 'Credenciais inválidas!'}



class Usuarios(Resource):
    @jwt_required()
    def post(self):
        """
        cpf_cnpj = get_jwt_identity()

        _cl = db.credenciais

        _pq = _cl.find_one({'cpfcnpj': cpf_cnpj})

        print(_pq['nomerazao'])
        """

        _json = request.json

        _cl = db[_json['tb']]

        _pesq = _cl.find(_json['psq'])

        _lista = list(_pesq)
        _ret = dumps(_lista)

        return _ret


class Edita(Resource):
    @jwt_required()
    def post(self):

        _json = request.json

        _cl = db[_json['tb']]

        for key in _json['psq']:
            if key == "_id":
                _json['psq']['_id'] = ObjectId(_json['psq']['_id'])

        _pesq = _cl.find_one(_json['psq'])

        return dumps(_pesq)



class Salva(Resource):
    @jwt_required()
    def post(self):
        _json = request.json

        _cl = db[_json['tb']]

        _cl.insert_one(dict(_json['dados']))

        return _json['dados']


class Altera(Resource):
    @jwt_required()
    def post(self):
        _json = request.json

        _cl = db[_json['tb']]

        for key in dict(_json['psq']):
            if key == "_id":
                _json['psq']['_id'] = ObjectId(_json['psq']['_id'])

        for key in dict(_json['dados']):
            if key == "_id":
                del _json['dados']['_id']

        _cl.update_one(_json['psq'], {"$set": _json['dados']})

        return _json['dados']


class Exclui(Resource):
    @jwt_required()
    def post(self):

        _json = request.json

        _cl = db[_json['tb']]

        for key in dict(_json['psq']):
            if key == "_id":
                _json['psq']['_id'] = ObjectId(_json['psq']['_id'])

        _cl.delete_one(_json['psq'])

        return jsonify('ok')


class Login_Extrato(Resource):
    def post(self):

        # ver matricula bloqueada em aspma

        _json = request.json

        _dados = dict(_json['dados'])

        _bloqueio_aspma = ''

        try:
            con = pymysql.connect(**connection_properties)
            print('conectou')
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        try:

            with con.cursor() as cur:

                cur.execute("SELECT socios.bloqueio FROM socios WHERE socios.matricula = " +
                            _dados['matricula'])

                rows = cur.fetchall()

            for row in rows:
                _bloqueio_aspma = row[0]

        except:

            None

        _data = datetime.now()
        _mes_ano = _data.strftime('%m-%Y')

        _cl = db['login_socios']

        _find = _cl.find_one({'matricula': _dados['matricula']})

        # captcha_response = _dados['catchaResponse']

        if _find and _find["cpf"][-6:].replace('-', '') == _dados['cpf']:

            # and is_human(captcha_response):

            access_token = create_access_token(identity=_find['matricula'])
            refresh_token = create_refresh_token(identity=_find['matricula'])

            return {'cpfcnpj': _find['cpf'],
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'nomerazao': _find['associado'],
                    'existe': 'X',
                    'email': _find['email'],
                    'celular': _find['celular'],
                    'bloqueio': _find['bloqueio'],
                    'tipo': _find['tipo'],
                    'bloqueio_aspma': _bloqueio_aspma,
                    'mes_ano': _mes_ano}

        try:

            with con.cursor() as cur:

                cur.execute("SELECT socios.matricula, socios.associado, socios.email, socios.celular, socios.bloqueio, socios.tipo FROM socios WHERE socios.matricula = " +
                            _dados['matricula'] + " AND RIGHT(socios.cpf,2) = " + _dados['cpf'][-2:] + " AND SUBSTR(socios.cpf, 9,3) = " + _dados['cpf'][:3])

                rows = cur.fetchall()

            for row in rows:

                access_token = create_access_token(identity=row[0])
                refresh_token = create_refresh_token(identity=row[0])

            return {
                'cpfcnpj': row[0],
                'access_token': access_token,
                'refresh_token': refresh_token,
                'nomerazao': row[1],
                'existe': 'X' if _find else 'Y',
                'email': row[2].lower(),
                'celular': row[3],
                'bloqueio_aspma': row[4],
                'tipo': row[5],
                'mes_ano': _mes_ano
            }

        finally:

            con.close()

        return {'error': 'Credenciais inválidas!'}


def is_human(captcha_response):

    secret = "6LcEHcsUAAAAAANOgwXoyU49fISRLAmSM0b_7o3J"

    payload = {'response': captcha_response, 'secret': secret}
    response = requests.post(
        "https://www.google.com/recaptcha/api/siteverify", payload)

    response_text = json.loads(response.text)

    return response_text['success']


class Descontos_Mensais_Socios(Resource):
    @jwt_required()
    def post(self):

        _json = request.json
        _mes_ano = _json["mes_ano"]

        _matricula = get_jwt_identity()

        #_data = "'" + _mes_ano[-4:] + '-' + _mes_ano[:2] + '-' + '07' + "'"

        try:
            con = pymysql.connect(**connection_properties)
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        try:

            with con.cursor() as cur:

                cur.execute("SELECT parcelas.id, parcelas.conveniado, vendas.emissao, parcelas.parcelas, parcelas.valor, TRIM(parcelas.nrseq) FROM parcelas LEFT JOIN vendas ON parcelas.matricula = vendas.matricula AND parcelas.sequencia = vendas.sequencia WHERE parcelas.baixa = '' AND MONTH(parcelas.vencimento) = " + _mes_ano[:2] + " AND YEAR(parcelas.vencimento) = " + _mes_ano[-4:] + " AND TRIM(parcelas.matricula) = " + _matricula.strip() + " ORDER BY parcelas.associado")

                rows = cur.fetchall()

                _campos = {}
                _res = []
                _total = 0

                for row in rows:
                    
                    _dia = int(row[2].strftime("%d"))
                    _mes = int(row[2].strftime("%m"))
                    _ano = int(row[2].strftime("%Y"))
                    
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
                           
                    mes_ano_final = str(_mes).zfill(2) + '-' + str(_ano).zfill(4)
                    
                    _campos['id'] = row[0]
                    _campos['nome_do_convenio'] = row[1]
                    _campos['data_da_venda'] = row[2].strftime("%d-%m-%Y")
                    _campos['parcela'] =  row[5]
                    _campos['numero_de_parcelas'] = str(int(row[3])).strip()
                    _campos['periodo'] =  mes_ano_inicial + ' a ' + mes_ano_final
                    _campos['valor_da_parcela'] = format_decimal(
                        row[4], format="#,##0.00;-#", locale='pt_BR')

                    _res.append(dict(_campos))

                    _total += row[4]

        finally:

            con.close()

        _total = format_decimal(_total, format="#,##0.00;-#", locale='pt_BR')

        retorno = {'dados': dumps(_res), 'total': _total}

        return retorno


class Compras_Mensais_Socios(Resource):
    @jwt_required()
    def post(self):

        _json = request.json
        _mes_ano = _json["mes_ano"]

        _matricula = get_jwt_identity()

        try:
            con = pymysql.connect(**connection_properties)
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        try:

            with con.cursor() as cur:

                cur.execute("SELECT vendas.emissao, TRIM(vendas.conveniado), vendas.parcelas, vendas.valorparcela, vendas.id FROM vendas WHERE vendas.valorparcela > 0 AND vendas.cancela = '' AND TRIM(vendas.matricula) = " +
                            _matricula.strip() + " AND YEAR(vendas.emissao) = " + _mes_ano[-4:] + " AND MONTH(vendas.emissao) = " + _mes_ano[:2] + " ORDER BY vendas.id desc")

                rows = cur.fetchall()

                _campos = {}
                _res = []
                _total = 0

                for row in rows:

                    _campos['data_da_venda'] = row[0].strftime("%d-%m-%Y")
                    _campos['nome_do_convenio'] = row[1]
                    _campos['numero_de_parcelas'] = str(int(row[2])).strip()
                    _campos['valor_da_parcela'] = format_decimal(
                        row[3], format="#,##0.00;-#", locale='pt_BR')
                    _campos['id'] = row[4]

                    _res.append(dict(_campos))

                    _total += row[3]

        finally:

            con.close()

        _total = format_decimal(_total, format="#,##0.00;-#", locale='pt_BR')

        retorno = {'dados': dumps(_res), 'total': _total}

        return retorno


class Margem(Resource):
    @jwt_required()
    def post(self):

        try:
            con = pymysql.connect(**connection_properties)
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        _margem = ''

        _matricula = get_jwt_identity()
        
        try:

            with con.cursor() as cur:

                cur.execute(
                    "SELECT tipo, limite, cpf FROM socios WHERE TRIM(matricula) = " + _matricula.strip())

                rows = cur.fetchall()

                for row in rows:

                    _tipo = row[0]
                    _limite = row[1]
                    _cpf = row[2]

        except AttributeError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        if int(_tipo) == 1:

            try:

                with con.cursor() as cur:

                    cur.execute(
                        "SELECT matricula_atual FROM matriculas WHERE TRIM(matricula_antiga) = " + _matricula.strip())

                    rows = cur.fetchall()

                    for row in rows:
                        _mat = row[0]
                        
            except AttributeError:
                return {'error': 'Falha na conexão... Tente novamente!'}

            try:
                
                data = {"cliente": 'ASPMA', "convenio": 'ASPMA-ARAUCARIA', "usuario": 'aspma_xml', "senha": 'dcc0bd05', "matricula" : _mat, "cpf": _cpf,  "valorParcela": '1.00'}

                session = _requests_retry_session(method_whitelist=False)

                resp = session.post('http://200.98.112.240/aspma/php/consultaMargemZetra.php',
                                    params=data, verify=False, timeout=(20, 20))
            
                #zetra
                _margem = re.search('<ns6:valorMargem xmlns:ns6="InfoMargem">(.+?)</', resp.text).group(1)

            except AttributeError:
                _margem = ''

        else:

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

                    cur.execute("SELECT sum(parcelas.valor) FROM parcelas WHERE TRIM(parcelas.matricula) = " + _matricula.strip() +
                                " AND YEAR(parcelas.vencimento) = " + str(lAno) + " AND MONTH(parcelas.vencimento) = " + str(lMes) + " AND parcelas.baixa = ''")

                    rows = cur.fetchall()
                    
                    for row in rows:
                        _margem = _limite if row[0] == None else (
                            float(_limite) - row[0])

            except AttributeError:
                print('erro')
            finally:

                con.close()

        _margem = format_decimal(_margem, format="#,##0.00;-#", locale='pt_BR')

        return {'margem': _margem}

class Codigo_Compra(Resource):
    @jwt_required()
    def post(self):

        try:
            con = pymysql.connect(**connection_properties)
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        _json = request.json

        _matricula = get_jwt_identity()

        _mt = get_jwt_identity()

        _dados = dict(_json['dados'])

        _tipo = ''

        _cl = db['login_socios']

        _find = _cl.find_one({'matricula': _matricula})

        if not _find:

            _cpf = _dados['cpf'][:3] + '.' + _dados['cpf'][-3:]

            try:
                with con.cursor() as cur:
                    cur.execute("SELECT socios.tipo, matriculas.matricula_atual, socios.cpf, socios.email, socios.celular, socios.nascimento, socios.associado, socios.matricula, socios.limite FROM socios LEFT JOIN matriculas ON matriculas.matricula_antiga=socios.matricula WHERE socios.matricula = " +
                                _matricula + " AND socios.senha = " + "'" + _dados['senha'] + "'" + " AND LEFT(socios.cpf,7) = " + "'" + _cpf + "'" + " GROUP BY socios.matricula")

                    rows = cur.fetchall()

                    for row in rows:
                        _tipo = row[0]
                        _matricula = _matricula if row[1] == None else row[1]
                        _cpf = row[2]
                        _email = _dados['email']
                        _celular = _dados['celular']
                        _nascimento = row[5]
                        _associado = row[6]
                        _mt_aspma = row[7]

                    if _tipo:
                        _cl.find_one_and_update({'matricula': _mt_aspma}, {
                            "$set": {
                                'associado': _associado,
                                'mt_grava': _matricula,
                                'tipo': _tipo,
                                'cpf': _cpf,
                                'email': _email.lower(),
                                'celular': _celular,
                                'nascimento': _nascimento.strftime('%Y-%m-%d'),
                                'bloqueio': 'NAO',
                                'senha': hashpw(_dados['nova_senha'].encode('utf8'), gensalt())
                            }}, upsert=True)

            except:
                return {'error': 'Falha na conexão... Tente novamente!'}
            finally:
                con.close()

        else:

            if _find and checkpw(_dados['senha'].encode('utf8'), _find["senha"]):
                _tipo = _find['tipo']
                _matricula = _find['mt_grava']
                _email = _find['email']
                _celular = _find['celular']
                _nascimento = _find['nascimento']
                _associado = _find['associado']

        _codigo = ''

        _nr_vezes = 0

        if _tipo != '':

            _cl = db['tentativas_socios']
            _cl.delete_one({'matricula': _mt})

            _cl = db['login_socios']
            _cl.update_one({'matricula': _mt}, {
                "$set": {'bloqueio': 'NAO'}})

            _cl = db[_json['tb']]
            _codigo = id_compra()

            _find = _cl.find_one({'codigo': _codigo})

            while _find:
                _codigo = id_compra()
                _find = _cl.find_one({'codigo': _codigo})

            _data_e_hora = datetime.now().strftime('%d-%m-%Y %H:%M')

            _cl.find_one_and_update({'matricula': _matricula}, {
                                    "$set": {'matricula_aspma': _mt, 'associado': _associado, 'tipo': _tipo, 'codigo': _codigo, 'data_hora': _data_e_hora}}, upsert=True)

            _volta = {'codigo': _codigo, 'nr_vezes': _nr_vezes,
                      'email': _email, 'nascimento': _nascimento, 'celular': _celular}

        else:
            _cl = db['tentativas_socios']

            _find = _cl.find_one({'matricula': _matricula})

            if _find:
                _nr_vezes = _find['nr_vezes']

            _nr_vezes = _nr_vezes + 1

            _cl.find_one_and_update({'matricula': _mt}, {
                                    "$set": {'nr_vezes': _nr_vezes}}, upsert=True)

            if _nr_vezes == 3:
                _cl = db['login_socios']
                _cl.update_one({'matricula': _mt}, {
                    "$set": {'bloqueio': 'OK'}})

            _volta = {'codigo': _codigo, 'nr_vezes': _nr_vezes}

        return jsonify(_volta)


class Gera_Codigo(Resource):
    @jwt_required()
    def post(self):

        if not internet():
            return {'msg': 'Verifique sua conexão com a Internet!'}

        mail = Mail()

        _cl = db['login_socios']

        find = _cl.find_one({"matricula": get_jwt_identity()})

        if find:

            code = id_generator()

            msg = Message('Código de Segurança A.S.P.M.A.',
                          sender='consigexpress@consigexpress.com.br', recipients=[find['email']])

            msg.html = "<p style='font-size: 22px'>INFORME ESTE CÓDIGO QUANDO SOLICITADO: " + \
                code + "</p>"

            mail.send(msg)

            _cl = db['codigo_altera_senha']

            _cl.find_one_and_update({'matricula': get_jwt_identity()}, {
                                    "$set": {'codigo': code}}, upsert=True)

            return {'codigo': code}

        return {'msg': 'E-Mail não cadastrado em A.S.P.M.A'}


class Altera_Senha(Resource):
    @jwt_required()
    def post(self):

        _json = request.json

        _matricula = get_jwt_identity()

        _dados = dict(_json['dados'])

        _cl = db['codigo_altera_senha']

        _find = _cl.find_one(
            {'matricula': _matricula, 'codigo': _dados['codigo']})

        if _find:

            _cl = db['login_socios']

            _cl.find_one_and_update({'matricula': _matricula}, {
                "$set": {
                    'bloqueio': 'NAO',
                    'senha': hashpw(_dados['nova_senha'].encode('utf8'), gensalt())
                }}, upsert=True)

            _cl = db['tentativas_socios']
            _cl.delete_one({'matricula': _matricula})

            _cl = db['codigo_altera_senha']
            _cl.delete_one({'matricula': _matricula})

            return {'msg': 'Senha alterada com sucesso!'}

        return {'msg': 'Código inválido! verifique novamente seu E-Mail ou repita o pŕocesso novamente.'}


class Altera_Cadastro(Resource):
    @jwt_required()
    def post(self):

        _json = request.json

        _matricula = get_jwt_identity()

        _dados = dict(_json['dados'])

        _cl = db['login_socios']

        _find = _cl.find_one({'matricula': _matricula})

        if _find and checkpw(_dados['senha'].encode('utf8'), _find["senha"]):

            _cl = db['tentativas_socios']
            _cl.delete_one({'matricula': _matricula})

            return jsonify(0)

        _nr_vezes = 1

        _cl = db['tentativas_socios']

        _find = _cl.find_one({'matricula': _matricula})

        if _find:
            _nr_vezes = _find['nr_vezes'] + 1

        _cl.find_one_and_update({'matricula': _matricula}, {
            "$set": {'nr_vezes': _nr_vezes}}, upsert=True)

        if _nr_vezes == 3:
            _cl = db['login_socios']
            _cl.update_one({'matricula': _matricula}, {
                "$set": {'bloqueio': 'OK'}})

        return jsonify(_nr_vezes)


class Altera_Dados_Cadastro(Resource):
    @jwt_required()
    def post(self):

        _json = request.json

        _matricula = get_jwt_identity()

        _dados = dict(_json['dados'])

        _cl = db['login_socios']

        _cl.find_one_and_update({'matricula': _matricula}, {
            "$set": {'email': _dados['email'].lower(), 'celular': _dados['celular']}}, upsert=True)

        return {'email': _dados['email'].lower(), 'celular': _dados['celular']}


class Altera_Dados_Unico(Resource):
    @jwt_required()
    def post(self):

        try:
            con = pymysql.connect(**connection_properties)
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        _json = request.json

        _matricula = get_jwt_identity()

        _dados = dict(_json['dados'])

        _tipo = ''

        _cl = db['login_socios']

        _find = _cl.find_one({'matricula': _matricula})

        if not _find:

            _cpf = _dados['cpf'][:3] + '.' + _dados['cpf'][-3:]

            try:
                with con.cursor() as cur:
                    cur.execute("SELECT socios.tipo, matriculas.matricula_atual, socios.cpf, socios.email, socios.celular, socios.nascimento, socios.associado, socios.matricula FROM socios LEFT JOIN matriculas ON matriculas.matricula_antiga=socios.matricula WHERE socios.matricula = " +
                                _matricula + " AND socios.senha = " + "'" + _dados['senha'] + "'" + " AND LEFT(socios.cpf,7) = " + "'" + _cpf + "'" + " GROUP BY socios.matricula")

                    rows = cur.fetchall()

                    for row in rows:
                        _tipo = row[0]
                        _matricula = _matricula if row[1] == None else row[1]
                        _cpf = row[2]
                        _email = _dados['email']
                        _celular = _dados['celular']
                        _nascimento = row[5]
                        _associado = row[6]
                        _mt_aspma = row[7]

                    if _tipo:
                        _cl.find_one_and_update({'matricula': _mt_aspma}, {
                            "$set": {
                                'associado': _associado,
                                'mt_grava': _matricula,
                                'tipo': _tipo,
                                'cpf': _cpf,
                                'email': _email.lower(),
                                'celular': _celular,
                                'nascimento': _nascimento.strftime('%Y-%m-%d'),
                                'bloqueio': 'NAO',
                                'senha': hashpw(_dados['nova_senha'].encode('utf8'), gensalt())
                            }}, upsert=True)

            except:
                return {'error': 'Falha na conexão... Tente novamente!'}
            finally:
                con.close()

        else:

            if _find and checkpw(_dados['senha'].encode('utf8'), _find["senha"]):
                _tipo = _find['tipo']
                _matricula = _find['mt_grava']
                _email = _find['email']
                _celular = _find['celular']
                _nascimento = _find['nascimento']

        _codigo = ''

        _nr_vezes = 0

        if _tipo != '':

            _cl = db['tentativas_socios']
            _cl.delete_one({'matricula': _matricula})

            _volta = {'codigo': _codigo, 'nr_vezes': _nr_vezes,
                      'email': _email, 'nascimento': _nascimento, 'celular': _celular}

        else:
            _cl = db['tentativas_socios']

            _find = _cl.find_one({'matricula': _matricula})

            if _find:
                _nr_vezes = _find['nr_vezes']

            _nr_vezes = _nr_vezes + 1

            _cl.find_one_and_update({'matricula': _matricula}, {
                                    "$set": {'nr_vezes': _nr_vezes}}, upsert=True)

            if _nr_vezes == 3:
                _cl = db['login_socios']
                _cl.update_one({'matricula': _matricula}, {
                    "$set": {'bloqueio': 'OK'}})

            _volta = {'codigo': _codigo, 'nr_vezes': _nr_vezes}

        return jsonify(_volta)


def id_generator(size=6, chars=string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def id_compra(size=4, chars=string.digits):
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


class Compras(Resource):
    @jwt_required()
    def post(self):

        _json = request.json
        
        _id = get_jwt_identity()
        
        _matricula = _id
        
        try:
            _mes_ano = _json["mes_ano"]
        except:
            data_e_hora_atuais = datetime.now()
            fuso_horario = timezone('America/Sao_Paulo')
            data_e_hora_sao_paulo = data_e_hora_atuais.astimezone(fuso_horario)
            data_e_hora_sao_paulo_em_texto = data_e_hora_sao_paulo.strftime(
                '%m/%Y')

            _mes_ano = data_e_hora_sao_paulo_em_texto

        try:
            con = pymysql.connect(**connection_properties)
            print('conectou')
        except pymysql.err.OperationalError:

            print('falou')

            return {'error': 'Falha na conexão... Tente novamente!'}

        try:

            with con.cursor() as cur:
                
                cur.execute(
                    "SELECT contratos.*, " +
                    "socios.associado AS nome_do_associado, " +
                    "socios.consignataria AS codigo_da_consignataria, " +
                    "consignatarias.nome AS nome_da_consignataria, " +
                    "convenio.razao_soc AS nome_do_convenio " +
                    "FROM contratos " +
                    "LEFT JOIN socios ON TRIM(socios.matricula) = TRIM(contratos.matricula_do_associado) " +
                    "LEFT JOIN consignatarias ON socios.consignataria = consignatarias.codigo " +
                    "LEFT JOIN convenio ON convenio.codigo = contratos.codigo_do_convenio " +
                    "WHERE contratos.matricula_do_associado = " + _matricula + " AND YEAR(contratos.data_da_venda) = " + _mes_ano[-4:] + " AND MONTH(contratos.data_da_venda) = " + _mes_ano[:2] + " " +
                    "ORDER BY contratos.id desc, nome_do_convenio")

                field_type = [i[0] for i in cur.description]

                rows = cur.fetchall()

                _campos = {}
                _res = []
                _total = 0
                _nr_parcela = 0

                for row in rows:
                    for x in range(0, len(field_type)):
                        _data = row[x]
                        if field_type[x] == 'numero_de_parcelas':
                            _nr_parcela = _data
                        if field_type[x] == 'valor_da_parcela':
                            _total += _data * _nr_parcela
                            _total_da_venda = _data * _nr_parcela
                        if field_type[x] == 'valor_total':
                            _data = _total_da_venda
                        if type(_data) is float:
                            _data = format_decimal(
                                _data, format="#,##0.00;-#", locale='pt_BR')
                        if type(_data) is date:
                            if _data == None:
                                _data = ''
                            else:
                                _data = str(row[x])
                            try:
                                _data = datetime.fromisoformat(_data)
                                _data = _data.strftime('%d-%m-%Y')
                            except:
                                _data = ''

                        _campos[field_type[x]] = _data

                    _res.append(dict(_campos))

        finally:

            con.close()
            
        _total = format_decimal(_total, format="#,##0.00;-#", locale='pt_BR')

        retorno = {'dados': dumps(_res), 'total': _total  }

        return retorno

class Descontos(Resource):
    @jwt_required()
    def post(self):

        _json = request.json
        _mes_ano = _json["mes_ano"]
        
        _id = get_jwt_identity()
        
        _matricula = _id
        
        try:
            con = pymysql.connect(**connection_properties)
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        try:

            with con.cursor() as cur:
                
                cur.execute(
                    "SELECT parcelas.id, " +
                    "convenio.razao_soc AS nome_do_convenio, " +
                    "contratos.data_da_venda AS data_contrato, " +
                    "contratos.numero_de_parcelas AS numero_parcelas, " +
                    "parcelas.nrseq, " +
                    "parcelas.valor " +
                    "FROM parcelas " +
                    "LEFT JOIN socios ON TRIM(socios.matricula) = TRIM(parcelas.matricula_do_associado) " +
                    "LEFT JOIN contratos ON TRIM(contratos.matricula_do_associado) = TRIM(parcelas.matricula_do_associado) AND TRIM(contratos.numero_do_contrato) = TRIM(parcelas.numero_do_contrato) " +
                    "LEFT JOIN convenio ON convenio.codigo = contratos.codigo_do_convenio " +
                    "WHERE parcelas.matricula_do_associado = " + _matricula + " AND LEFT(parcelas.vencimento,2) = " + _mes_ano[:2] + " AND RIGHT(parcelas.vencimento,4) = " + _mes_ano[-4:] + " AND parcelas.baixa <> 'X' " +
                    "ORDER BY parcelas.id")

                rows = cur.fetchall()
                
                _campos = {}
                _res = []
                _total = 0

                for row in rows:
                    try:
                        _campos['id'] = row[0]
                        _campos['nome_do_convenio'] = row[1]
                        _campos['data_da_venda'] = row[2].strftime("%d-%m-%Y")
                        _campos['numero_de_parcelas'] = str(int(row[3]))
                        _campos['parcela'] = str(int(row[4]))
                        _campos['valor_da_parcela'] = format_decimal(
                            row[5], format="#,##0.00;-#", locale='pt_BR')
                        
                        _res.append(dict(_campos))

                        _total += row[5]
                    except:
                        continue    

        finally:

            con.close()
            
        __total = format_decimal(_total, format="#,##0.00;-#", locale='pt_BR')
        
        retorno = {'dados': dumps(_res), 'total': __total}
        
        return retorno


class Lista_Convenios(Resource):
    @jwt_required()
    def post(self):

        try:
            con = pymysql.connect(**connection_properties)
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        try:

            with con.cursor() as cur:

                cur.execute("SELECT id, razao_soc, fantasia, endereco, fone FROM convenio ORDER BY razao_soc")

                rows = cur.fetchall()

                _campos = {}
                _res = []

                for row in rows:
                    try:
                        _campos['id'] = row[0]
                        _campos['nome_do_convenio'] = row[1]
                        _campos['fantasia'] = row[2]
                        _campos['endereco'] = row[3]
                        _campos['telefone'] = row[4]
                        
                        _res.append(dict(_campos))

                    except:
                        continue    

        finally:

            con.close()
            
        retorno = {'dados': dumps(_res) }
        
        return retorno


class Autentica_Socios(Resource):
    @jwt_required()
    def post(self):

        _json = request.json

        _dados = dict(_json['dados'])
        
        _id = get_jwt_identity()
        
        _matricula = _id

        try:
            con = pymysql.connect(**connection_properties)
            print('conectou')
        except pymysql.err.OperationalError:
            return {'error': 'Falha na conexão... Tente novamente!'}

        try:

            with con.cursor() as cur:
                
                _exec = "SELECT matricula FROM socios WHERE TRIM(matricula) = " + _matricula + " AND TRIM(senha) = " + _dados['senha']
                
                cur.execute(_exec)
                
                _rows = cur.fetchall()
                _achou = ''

                for _row in _rows:
                    _achou = _row[0]
                
                if _achou == '':
                    return {'msg': 'Senha inválida!'}
                
                _exec = "UPDATE socios SET bloqueio = 'X' WHERE TRIM(matricula) = " + _matricula + " AND TRIM(senha) = " + _dados['senha']

                cur.execute(_exec)
                con.commit()

        except:

            return {'msg': 'Senha inválida!'}

        finally:

            con.close()

        return {'msg': 'Senha bloqueada com sucesso!'}
