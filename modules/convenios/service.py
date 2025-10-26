from datetime import datetime
import random, string
from pytz import timezone
from babel.numbers import format_decimal
from typing import Optional
from bcrypt import gensalt, hashpw, checkpw

from core.security import generate_tokens
from core.exceptions import AuthenticationError, ValidationError, AppError
import os, traceback
from config.settings import Settings
from .repository import ConveniosRepository
from .mongo_repository import ConveniosMongoRepository
from .models import ConvenioLogin

class ConveniosService:
    def __init__(self, repo: ConveniosRepository = None, mongo_repo: ConveniosMongoRepository = None, settings: Settings = None):
        self.repo = repo or ConveniosRepository()
        self.mongo = mongo_repo or ConveniosMongoRepository()
        self.settings = settings or Settings()
        # estado efêmero para expor resultado de envio pós-venda ao endpoint
        self._last_whatsapp_sent_post = False
        self._last_phone_mask_post = None

    # === Utilidades internas ===
    def _mask_phone(self, raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        # tenta formatar como (41) 9****-**** mantendo DDD/parte inicial
        digits = ''.join(ch for ch in str(raw) if ch.isdigit())
        if len(digits) < 8:
            return None
        # Heurística: se vier com 8 dígitos (formato legado), prefixa um 9 e usa DDD padrão
        if len(digits) == 8:
            ddd = self.settings.WHATS_DEFAULT_DDD
            restante = '9' + digits
        elif len(digits) >= 10:
            ddd = digits[:2]
            restante = digits[2:]
        else:
            ddd = ''
            restante = digits
        # mascara meio
        if len(restante) >= 5:
            meio = '*****'
            # mantem primeiros e ultimos 2 digitos
            inicio = restante[:1]
            fim = restante[-2:]
            masked = f"({ddd}) {inicio}{meio}{fim}" if ddd else f"{inicio}{meio}{fim}"
        else:
            masked = f"({ddd}) *****" if ddd else "*****"
        return masked

    def _send_whatsapp(self, associado_primeiro_nome: str, convenio: str, id_compra: str,
                        valor_total: str, nr_parcelas: int, valor_parcela: str,
                        contato_celular: str, message_body: Optional[str] = None) -> bool:
        """Envia mensagem via WhatsGw quando habilitado. Retorna True/False.

        Requer variáveis no Settings: WHATSAPP_ENABLED, WHATS_GW_APIKEY, WHATS_GW_SENDER.
        """
        try:
            if not self.settings.WHATSAPP_ENABLED:
                return False
            import requests
            apikey = self.settings.WHATS_GW_APIKEY
            sender = self.settings.WHATS_GW_SENDER
            api_url = self.settings.WHATS_GW_API_URL
            if not apikey or not sender or not api_url:
                return False
            # Monta telefone do contato em E.164. Se já vier com DDI, mantém; caso contrário, prefixa Brasil '55'.
            digits = ''.join(ch for ch in str(contato_celular or '') if ch.isdigit())
            if not digits:
                return False
            # Normaliza para E.164 (Brasil): se 8 dígitos, prefixa 9 e DDD padrão; se 10/11 dígitos, assume já com DDD; se já começa com 55, mantém
            if len(digits) == 8:
                digits = self.settings.WHATS_DEFAULT_DDD + '9' + digits
            if not digits.startswith('55'):
                if len(digits) in (10, 11):
                    contato = '55' + digits
                else:
                    # fallback simples
                    contato = '55' + digits
            else:
                contato = digits
            if not message_body:
                # Mensagem padrão (pré-venda)
                message_body = (
                    f"*Olá, {associado_primeiro_nome}!*\n\n"
                    "*Nova compra ASPMA.*\n"
                    "__________________________________\n\n"
                    f"🏷️ *_CÓDIGO DA COMPRA_:* {id_compra}\n"
                    "__________________________________\n"
                    f"*Convênio:*\n{convenio}\n\n"
                    f"*Valor Total  :* R$ {valor_total}\n"
                    f"*N° parcelas :* {nr_parcelas}\n"
                    f"*Valor da Parcela :* R$ {valor_parcela}\n"
                )
            payload = {
                'apikey': apikey,
                'phone_number': sender,
                'contact_phone_number': contato,
                'message_type': 'text',
                'message_body': message_body
            }
            resp = requests.post(api_url, json=payload, timeout=20)
            resp.raise_for_status()
            return True
        except Exception:
            # Não propaga erro de WhatsApp para não quebrar fluxo principal
            return False

    def autenticar(self, usuario: str, senha: str):
        # Modo fake: se ENABLE_FAKE_LOGIN ligado e senha especial, retorna payload simulado
        enable_fake = os.getenv('ENABLE_FAKE_LOGIN', str(self.settings.ENABLE_FAKE_LOGIN)).lower() in ('true','1','yes')
        if enable_fake and senha == '__dev__':
            mes_ano = datetime.now(timezone('America/Sao_Paulo')).strftime('%m-%Y')
            codigo = 'FAKE123'
            identity_payload = {
                'tipo': 'convenio',
                'codigo': codigo,
                'nome_razao': 'Convênio Fake Dev',
                'usuario': usuario.lower()
            }
            tokens = generate_tokens(identity=identity_payload, additional_claims={'fake': True})
            conv = ConvenioLogin(
                codigo=codigo,
                nome_razao='Convênio Fake Dev',
                fantasia='Fantasia Dev',
                usuario=usuario.lower(),
                email=f'{usuario.lower()}@fake.dev',
                cpf_cnpj='00.000.000/0000-00',
                desconto=0.0,
                parcelas=12,
                libera='S',
                mes_ano=mes_ano
            )
            return conv, tokens

        max_tent = self.settings.MAX_TENTATIVAS_CONVENIO
        # Infra access dentro de try para mapear erros genéricos em AppError 503
        login_doc = None
        mongo_ok = True
        try:
            login_doc = self.mongo.get_login_doc(usuario.upper())
        except Exception:
            # Degrada: se Mongo falha, continua sem bloquear login.
            mongo_ok = False

        if not login_doc:
            try:
                row_user = self.repo.buscar_por_usuario(usuario)
                if row_user:
                    codigo_lookup = row_user[0]
                    try:
                        login_doc = self.mongo.get_login_doc(codigo_lookup)
                    except Exception:
                        login_doc = None
            except Exception:
                pass  # continua

        # Bloqueio removido - sistema não bloqueia mais por tentativas
        # if login_doc and login_doc.get('bloqueio') == 'SIM':
        #     raise AuthenticationError('Usuário bloqueado. Contate suporte.')

        # Primeiro busca o usuário para obter o hash/senha armazenada
        try:
            row_with_pwd = self.repo.buscar_por_usuario(usuario)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception(
                "infra_mysql_error", extra={
                    'evento': 'convenios_login_mysql_fail',
                    'usuario': usuario,
                    'mensagem': str(e.__class__.__name__),
                }
            )
            raise AppError('Serviço temporariamente indisponível. Tente novamente em instantes.', code='BACKEND_UNAVAILABLE', status_code=503) from e

        if not row_with_pwd:
            # Usuário não encontrado - bloqueio removido
            raise AuthenticationError('Credenciais inválidas')

        # Extrai a senha armazenada no MySQL (pode ser hash bcrypt ou texto plano)
        codigo, razao, fantasia, cgc, email, libera, desconto, parcelas, libera2, senha_mysql = row_with_pwd
        
        # Verifica se a senha é válida (suporta hash bcrypt ou texto plano legacy)
        senha_valida = False
        if senha_mysql:
            # Tenta verificar como hash bcrypt primeiro
            if senha_mysql.startswith('$2') and len(senha_mysql) >= 59:
                try:
                    senha_valida = checkpw(senha.encode('utf8'), senha_mysql.encode('utf8'))
                except Exception:
                    senha_valida = False
            else:
                # Fallback para senha em texto plano (compatibilidade legacy)
                senha_valida = (senha.strip() == senha_mysql.strip())

        if not senha_valida:
            # Senha incorreta - bloqueio removido
            raise AuthenticationError('Credenciais inválidas')

        # Login bem-sucedido
        try:
            codigo_reset = codigo
            try:
                self.mongo.reset_tentativas(codigo_reset)
            except Exception:
                pass
            # Paridade com legado: grava hash da senha no Mongo e desbloqueia
            try:
                if isinstance(senha, str) and senha:
                    senha_hash = hashpw(senha.encode('utf8'), gensalt())
                    self.mongo.atualizar_senha_mongo(codigo_reset, senha_hash)
            except Exception:
                # Não bloqueia login se operação de conveniência falhar
                pass
            
            # Verifica se a senha tem apenas 4 dígitos (senha insegura)
            senha_4_digitos = bool(senha and len(senha) == 4 and senha.isdigit())
            
            # Dados já obtidos de row_with_pwd
            mes_ano = datetime.now(timezone('America/Sao_Paulo')).strftime('%m-%Y')
            identity_payload = {
                'tipo': 'convenio',
                'codigo': codigo,
                'nome_razao': razao,
                'usuario': usuario.lower(),
                'senha_4_digitos': senha_4_digitos  # Inclui flag no JWT
            }
            tokens = generate_tokens(identity=identity_payload)
            return ConvenioLogin(
                codigo=codigo,
                nome_razao=razao,
                fantasia=fantasia,
                usuario=usuario.lower(),
                email=email.lower() if email else None,
                cpf_cnpj=cgc,
                desconto=float(desconto) if desconto is not None else 0.0,
                parcelas=int(parcelas) if parcelas is not None else 0,
                libera=libera2,
                mes_ano=mes_ano,
                senha_4_digitos=senha_4_digitos  # Adiciona flag ao response
            ), tokens
        except AppError:
            raise
        except AuthenticationError:
            raise
        except Exception as e:
            traceback.print_exc()
            raise AppError('Erro inesperado de autenticação', code='INTERNAL_AUTH', status_code=500) from e

    def autenticar_acao(self, codigo_convenio: str, senha: str) -> bool:
        """Confirma a senha do convênio já autenticado para ações sensíveis.

        - Bloqueio removido - sistema não bloqueia mais por tentativas
        - Em caso de sucesso, reseta tentativas (mantido para compatibilidade).
        - Suporta validação híbrida: bcrypt hash ou senha plain text (legacy).
        """
        max_tent = self.settings.MAX_TENTATIVAS_CONVENIO
        login_doc = self.mongo.get_login_doc(codigo_convenio)
        
        # Bloqueio removido
        # if login_doc and login_doc.get('bloqueio') == 'SIM':
        #     raise AuthenticationError('Senha bloqueada... para desbloquear acesse [Alterar Senha]')

        senha_hash = (login_doc or {}).get('senha')
        if senha_hash and isinstance(senha, str) and checkpw(senha.encode('utf8'), senha_hash):
            try:
                self.mongo.reset_tentativas(codigo_convenio)
            except Exception:
                pass
            return True

        # Fallback: se hash não existe no Mongo ou não confere, tentar validar diretamente no MySQL
        # usando o usuário do token e garantindo que o código retornado case com o JWT atual.
        # SUPORTA SENHA CRIPTOGRAFADA (bcrypt) E PLAIN TEXT (legacy)
        try:
            # Recupera usuário do token através do claim padrão (o endpoint chama este método com contexto ativo)
            from flask_jwt_extended import get_jwt, get_jwt_identity
            claims = get_jwt()
            ident_claim = claims.get('identity') if isinstance(claims, dict) else None
            usuario_token = None
            if isinstance(ident_claim, dict):
                usuario_token = ident_claim.get('usuario')
            if not usuario_token:
                legacy_ident = get_jwt_identity()
                if isinstance(legacy_ident, dict):
                    usuario_token = legacy_ident.get('usuario')
            
            if usuario_token and isinstance(senha, str) and senha:
                # Busca dados do usuário incluindo senha do MySQL
                row_with_pwd = self.repo.buscar_por_usuario(usuario_token)
                if row_with_pwd:
                    # Extrai código e senha do MySQL
                    # Formato: (codigo, razao, fantasia, cgc, email, libera, desconto, parcelas, libera2, senha)
                    codigo_mysql = (row_with_pwd[0] or '').strip()
                    senha_mysql = row_with_pwd[9] if len(row_with_pwd) > 9 else None
                    
                    # Garante que o usuário do token pertence ao mesmo código do JWT
                    if codigo_mysql.upper() == (codigo_convenio or '').strip().upper():
                        # Validação híbrida: bcrypt ou plain text
                        senha_valida = False
                        if senha_mysql:
                            # Detecta se é hash bcrypt (formato: $2a$, $2b$, $2y$ com 60 chars)
                            if senha_mysql.startswith('$2') and len(senha_mysql) >= 59:
                                # Senha criptografada com bcrypt
                                senha_valida = checkpw(senha.encode('utf8'), senha_mysql.encode('utf8'))
                            else:
                                # Senha plain text (legacy)
                                senha_valida = (senha.strip() == senha_mysql.strip())
                        
                        if senha_valida:
                            # Atualiza Mongo para futuras verificações e zera tentativas
                            try:
                                new_hash = hashpw(senha.encode('utf8'), gensalt())
                                self.mongo.atualizar_senha_mongo(codigo_convenio, new_hash)
                                self.mongo.reset_tentativas(codigo_convenio)
                            except Exception:
                                pass
                            return True
        except Exception:
            # Qualquer erro neste fallback não deve vazar detalhes; segue fluxo de erro padrão
            pass

        # Falha: bloqueio removido - apenas retorna erro
        raise AuthenticationError('Senha inválida!')
        
    # === Fluxo de Código por E-mail / Alteração de Senha ===
    def gerar_codigo_email(self, codigo_convenio: str, email: str, mail_sender, allow_dev_bypass: bool = False):
        login_doc = None
        try:
            login_doc = self.mongo.get_login_doc(codigo_convenio)
        except Exception:
            login_doc = None
        # Verifica contra Mongo/MySQL a não ser que bypass de dev esteja habilitado
        email_ok = False
        if allow_dev_bypass:
            email_ok = True
        else:
            if login_doc and (login_doc.get('email') or ''):
                email_ok = (login_doc.get('email','').lower() == email.lower())
            if not email_ok:
                # 1) Verifica e-mail cadastrado para este código (MySQL)
                try:
                    email_mysql = self.repo.buscar_email_por_codigo(codigo_convenio)
                    if email_mysql and email_mysql.lower() == email.lower():
                        email_ok = True
                except Exception:
                    email_ok = False
            if not email_ok:
                # 2) Verifica mapeamento reverso (email -> codigo) no MySQL e confere se pertence ao convênio autenticado
                try:
                    codigo_mysql = self.repo.buscar_codigo_por_email(email)
                    if codigo_mysql and codigo_mysql.strip().upper() == (codigo_convenio or '').strip().upper():
                        email_ok = True
                except Exception:
                    email_ok = False
        if not email_ok:
            raise AuthenticationError('E-mail não encontrado ou divergente do cadastro')
        codigo = ''.join(random.choices(string.digits, k=6))
        self.mongo.armazenar_codigo_email(codigo_convenio, codigo)
        # Envio de e-mail
        try:
            mail_sender.send_codigo(email, codigo)
        except AuthenticationError as e:
            # Propaga mensagem específica (ex.: STRICT_MODE habilitado)
            raise e
        except Exception:
            # Fallback genérico quando não for AuthenticationError específico
            raise AuthenticationError('Falha ao enviar e-mail')
        return True

    def alterar_senha_codigo(self, codigo_convenio: str, codigo: str, nova_senha: str):
        if not self.mongo.validar_codigo_email(codigo_convenio, codigo):
            raise AuthenticationError('Código inválido')
        senha_hash = hashpw(nova_senha.encode('utf8'), gensalt())
        self.mongo.atualizar_senha_mongo(codigo_convenio, senha_hash)
        # Atualiza MySQL; em modo não estrito, tolera falha de infra e segue (dev fallback)
        try:
            self.repo.atualizar_senha_mysql(codigo_convenio, senha_hash)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception(
                "infra_mysql_error", extra={
                    'evento': 'convenios_alterar_senha_mysql_fail',
                    'codigo_convenio': codigo_convenio,
                    'mensagem': str(e.__class__.__name__),
                }
            )
            strict = os.getenv('PASSWORD_STRICT_MODE', 'true').lower() in ('1','true','yes')
            # Fallback opcional: se a coluna 'senha' for curta e o hash não couber, permitir plain
            # apenas quando a flag LEGACY_PASSWORD_PLAIN_FALLBACK=true (compat com schema antigo).
            allow_plain = os.getenv('LEGACY_PASSWORD_PLAIN_FALLBACK', 'false').lower() in ('1','true','yes')
            if allow_plain:
                try:
                    # Atenção: apenas como compatibilidade temporária; Mongo segue com hash.
                    self.repo.atualizar_senha_mysql_plain(codigo_convenio, nova_senha)
                    return True
                except Exception:
                    pass
            if strict:
                from core.exceptions import AppError
                raise AppError('Serviço temporariamente indisponível. Tente novamente em instantes.', code='BACKEND_UNAVAILABLE', status_code=503) from e
            # não estrito (desenvolvimento): prossegue sem atualizar MySQL
            try:
                from flask import current_app
                current_app.log_event('password_update_dev_override', codigo=codigo_convenio)
            except Exception:
                pass
        self.mongo.remover_codigo(codigo_convenio)
        return True

    def alterar_senha_esqueceu(self, codigo: str, nova_senha: str):
        doc = self.mongo.validar_codigo_global(codigo)
        if not doc:
            raise AuthenticationError('Código inválido')
        codigo_convenio = doc['codigo_convenio']
        # Dev bypass: quando o código foi gerado para um e-mail sem convênio conhecido,
        # usamos a chave sintética 'email:<email>' no fallback em memória. Tente resolver
        # o código real do convênio via MySQL antes de prosseguir com a atualização.
        if isinstance(codigo_convenio, str) and codigo_convenio.startswith('email:'):
            email_ref = codigo_convenio.split(':', 1)[1]
            try:
                resolved = self.repo.buscar_codigo_por_email(email_ref)
            except Exception:
                resolved = None
            if not resolved:
                # Não é possível alterar senha sem um convênio real associado
                raise AuthenticationError('Código inválido')
            codigo_convenio = resolved
        senha_hash = hashpw(nova_senha.encode('utf8'), gensalt())
        self.mongo.atualizar_senha_mongo(codigo_convenio, senha_hash)
        # Atualiza MySQL; em modo não estrito, tolera falha de infra e segue (dev fallback)
        try:
            self.repo.atualizar_senha_mysql(codigo_convenio, senha_hash)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception(
                "infra_mysql_error", extra={
                    'evento': 'convenios_alterar_senha_esqueceu_mysql_fail',
                    'codigo_convenio': codigo_convenio,
                    'mensagem': str(e.__class__.__name__),
                }
            )
            strict = os.getenv('PASSWORD_STRICT_MODE', 'true').lower() in ('1','true','yes')
            allow_plain = os.getenv('LEGACY_PASSWORD_PLAIN_FALLBACK', 'false').lower() in ('1','true','yes')
            if allow_plain:
                try:
                    self.repo.atualizar_senha_mysql_plain(codigo_convenio, nova_senha)
                    return True
                except Exception:
                    pass
            if strict:
                from core.exceptions import AppError
                raise AppError('Serviço temporariamente indisponível. Tente novamente em instantes.', code='BACKEND_UNAVAILABLE', status_code=503) from e
            # não estrito (desenvolvimento): prossegue sem atualizar MySQL
            try:
                from flask import current_app
                current_app.log_event('password_update_dev_override', codigo=codigo_convenio)
            except Exception:
                pass
        self.mongo.remover_codigo(codigo_convenio)
        return True

    def solicitar_codigo_esqueceu(self, email: str, mail_sender):
        codigo_convenio = None
        try:
            conv = self.mongo.buscar_por_email(email)
            if conv and conv.get('codigo'):
                codigo_convenio = conv['codigo']
        except Exception:
            # Ignora e tenta fallback
            pass
        if not codigo_convenio:
            try:
                codigo_convenio = self.repo.buscar_codigo_por_email(email)
            except Exception:
                codigo_convenio = None
        if not codigo_convenio:
            # Dev bypass opcional: permite enviar código mesmo sem e-mail cadastrado,
            # armazenando em fallback em memória com chave sintética 'email:<email>'.
            allow_dev = os.getenv('ALLOW_DEV_ESQUECEU_ANY', os.getenv('ALLOW_DEV_EMAIL_ANY', 'false')).lower() in ('1','true','yes')
            if not allow_dev:
                raise AuthenticationError('E-mail não encontrado')
            codigo_convenio = f"email:{email.lower().strip()}"
        codigo = ''.join(random.choices(string.digits, k=6))
        self.mongo.armazenar_codigo_email(codigo_convenio, codigo)
        try:
            mail_sender.send_codigo(email, codigo)
        except AuthenticationError as e:
            raise e
        except Exception:
            raise AuthenticationError('Falha ao enviar e-mail')
        return True

    def listar_parcelas(self, codigo: str, mes_ano: str):
        self._validar_mes_ano(mes_ano)
        mes = int(mes_ano[:2]); ano = int(mes_ano[-4:])
        rows = self.repo.listar_parcelas_mes(codigo, mes, ano)
        resultado = []
        total = 0.0
        for pid, associado, emissao, qtd_parcelas, valor, nrseq in rows:
            dia = int(emissao.strftime('%d')) if emissao else 1
            mes_ref = int(emissao.strftime('%m')) if emissao else mes
            ano_ref = int(emissao.strftime('%Y')) if emissao else ano
            if dia > self.settings.CORTE_DIA:
                if mes_ref == 12:
                    mes_ref = 1; ano_ref += 1
                else:
                    mes_ref += 1
            fim_mes = mes_ref; fim_ano = ano_ref
            for _ in range(1, int(qtd_parcelas)):
                if fim_mes == 12:
                    fim_mes = 1; fim_ano += 1
                else:
                    fim_mes += 1
            periodo = f"{mes_ref:02d}-{ano_ref} a {fim_mes:02d}-{fim_ano}"
            resultado.append({
                'periodo': periodo,
                'n_parcela': nrseq,
                'id': pid,
                'nome': associado,
                'data': emissao.strftime('%d-%m-%Y') if emissao else None,
                'parcelas': str(int(qtd_parcelas)).strip(),
                'valor': format_decimal(valor, format="#,##0.00;-#", locale='pt_BR')
            })
            total += valor
        return {
            'dados': resultado,
            'total': format_decimal(total, format="#,##0.00;-#", locale='pt_BR')
        }

    def listar_compras(self, codigo: str, mes_ano: str):
        self._validar_mes_ano(mes_ano)
        mes = int(mes_ano[:2]); ano = int(mes_ano[-4:])
        rows = self.repo.listar_compras_mes(codigo, mes, ano)
        resultado = []; total = 0.0
        for emissao, associado, parcelas, valor_parcela, vid in rows:
            dia = int(emissao.strftime('%d')) if emissao else 1
            mes_ref = int(emissao.strftime('%m')) if emissao else mes
            ano_ref = int(emissao.strftime('%Y')) if emissao else ano
            if dia > self.settings.CORTE_DIA:
                if mes_ref == 12:
                    mes_ref = 1; ano_ref += 1
                else:
                    mes_ref += 1
            fim_mes = mes_ref; fim_ano = ano_ref
            for _ in range(1, int(parcelas)):
                if fim_mes == 12:
                    fim_mes = 1; fim_ano += 1
                else:
                    fim_mes += 1
            periodo = f"{mes_ref:02d}-{ano_ref} a {fim_mes:02d}-{fim_ano}"
            resultado.append({
                'periodo': periodo,
                'data': emissao.strftime('%d-%m-%Y') if emissao else None,
                'nome': associado,
                'parcelas': str(int(parcelas)).strip(),
                'valor': format_decimal(valor_parcela, format="#,##0.00;-#", locale='pt_BR'),
                'id': vid
            })
            total += valor_parcela
        return {
            'dados': resultado,
            'total': format_decimal(total, format="#,##0.00;-#", locale='pt_BR')
        }

    # === Limite & Vendas Simplificados ===
    def calcular_limite(self, matricula: str, valor: str, nr_parcelas: int):
        socio = self.repo.fetch_socio_core(matricula)
        if not socio:
            raise ValidationError('Matrícula não encontrada')
        # regra de corte
        hoje = datetime.now(timezone('America/Sao_Paulo'))
        mes_ref = hoje.month; ano_ref = hoje.year
        if hoje.day > self.settings.CORTE_DIA:
            if mes_ref == 12:
                mes_ref = 1; ano_ref += 1
            else:
                mes_ref += 1
        utilizado = self.repo.soma_parcelas_mes(matricula, ano_ref, mes_ref) if int(socio['tipo']) != 1 else 0.0
        limite_disponivel = socio['limite'] - utilizado
        bruto = float(valor.replace('.','').replace(',','.'))
        parcela = round(bruto / nr_parcelas, 2)
        if limite_disponivel < parcela:
            return {
                'saldo': round(limite_disponivel,2),
                'insuficiente': True
            }
        # calcular periodo final
        mes_final = mes_ref; ano_final = ano_ref
        for _ in range(1, nr_parcelas):
            mes_final += 1
            if mes_final > 12:
                mes_final = 1; ano_final += 1
        # Gera código curto de confirmação (replicando semântica legacy)
        id_compra = ''.join(random.choice(string.digits) for _ in range(4))
        # Monta resposta base
        resp = {
            'matricula': matricula,
            'associado': socio['associado'],
            'saldo': round(limite_disponivel,2),
            'mes': mes_ref,
            'ano': ano_ref,
            'limite': format_decimal(limite_disponivel, format="#,##0.00;-#", locale='pt_BR'),
            'sequencia': str(socio['sequencia']),
            'valor_total': format_decimal(bruto, format="#,##0.00;-#", locale='pt_BR'),
            'valor_parcela': format_decimal(parcela, format="#,##0.00;-#", locale='pt_BR'),
            'nr_parcelas': nr_parcelas,
            'mes_final': mes_final,
            'ano_final': ano_final,
            'tipo': socio['tipo'],
            'id_compra': id_compra
        }
        # Inclui máscara de celular se disponível
        phone_mask = self._mask_phone(socio.get('celular'))
        if phone_mask:
            resp['phone_mask'] = phone_mask
        # Opcional: disparo de WhatsApp com o código
        whatsapp_sent = False
        try:
            # flag para desativar apenas o envio da etapa de limite (pré-venda)
            pre_enabled = getattr(self.settings, 'WHATSAPP_ENABLED', False) and os.getenv('WHATSAPP_SEND_PRE', 'true').lower() in ('1','true','yes')
            if pre_enabled and socio.get('celular'):
                primeiro_nome = (socio['associado'] or '').split()[0]
                # Busca nome do convênio do JWT quando houver contexto (best effort)
                convenio_nome = ''
                try:
                    from flask_jwt_extended import get_jwt
                    claims = get_jwt() or {}
                    ident = claims.get('identity') if isinstance(claims, dict) else None
                    if isinstance(ident, dict):
                        convenio_nome = ident.get('nome_razao') or ''
                except Exception:
                    pass
                # de-dup: evita enviar 2x para mesma matrícula/id_compra no curto prazo
                try:
                    ttl = int(getattr(self.settings, 'WHATSAPP_DEDUP_TTL_SECONDS', 180))
                except Exception:
                    ttl = 180
                if not self.mongo.has_whatsapp_event('pre', matricula, id_compra, ttl_seconds=ttl):
                    whatsapp_sent = self._send_whatsapp(
                    associado_primeiro_nome=primeiro_nome,
                    convenio=convenio_nome,
                    id_compra=id_compra,
                    valor_total=resp['valor_total'],
                    nr_parcelas=nr_parcelas,
                    valor_parcela=resp['valor_parcela'],
                    contato_celular=socio.get('celular')
                    )
                    if whatsapp_sent:
                        try:
                            self.mongo.record_whatsapp_event('pre', matricula, id_compra)
                        except Exception:
                            pass
                # Log estruturado (não sensível)
                try:
                    from flask import current_app
                    current_app.log_event('convenios_whatsapp_limit', sent=bool(whatsapp_sent), phone_mask=phone_mask, matricula=matricula, convenio=convenio_nome)
                except Exception:
                    pass
        except Exception:
            pass
        resp['whatsapp_sent'] = bool(whatsapp_sent)
        return resp

    def registrar_venda_senha(self, dados: dict, codigo_convenio: str, nome_convenio: str, usuario: str):
        # Pré-condições: saldo validado pelo front usando calcular_limite
        # Validações básicas
        try:
            nr_parcelas = int(dados['nr_parcelas'])
        except Exception:
            raise ValidationError('nr_parcelas inválido')
        if nr_parcelas < 1:
            raise ValidationError('nr_parcelas deve ser >= 1')
        try:
            bruto = float(dados['valor'].replace('.','').replace(',','.'))
        except Exception:
            raise ValidationError('valor inválido')
        if bruto <= 0:
            raise ValidationError('valor deve ser > 0')
        try:
            mes_inicial = int(dados['mes'])
            ano_inicial = int(dados['ano'])
        except Exception:
            raise ValidationError('mes/ano inválidos')
        if not 1 <= mes_inicial <= 12:
            raise ValidationError('mes fora do intervalo 1-12')
        if ano_inicial < 2000:
            raise ValidationError('ano inválido')
        valor_parcela = round(bruto / nr_parcelas, 2)
        # Revalidação interna de limite para consistência (evita confiar 100% no front)
        socio = self.repo.fetch_socio_core(dados['matricula'])
        if not socio:
            raise ValidationError('Matrícula não encontrada')
        # regra de corte igual à de calcular_limite
        hoje = datetime.now(timezone('America/Sao_Paulo'))
        mes_ref = hoje.month; ano_ref = hoje.year
        if hoje.day > self.settings.CORTE_DIA:
            if mes_ref == 12:
                mes_ref = 1; ano_ref += 1
            else:
                mes_ref += 1
        utilizado = self.repo.soma_parcelas_mes(dados['matricula'], ano_ref, mes_ref) if int(socio['tipo']) != 1 else 0.0
        limite_disponivel = socio['limite'] - utilizado
        if int(socio['tipo']) != 1 and limite_disponivel < valor_parcela:
            raise ValidationError('limite insuficiente para valor_parcela')
        mes_final = mes_inicial; ano_final = ano_inicial
        for _ in range(1, nr_parcelas):
            mes_final += 1
            if mes_final > 12:
                mes_final = 1; ano_final += 1
        # Normaliza campos para persistência
        try:
            seq_int = int(dados.get('sequencia') or 0)
        except Exception:
            seq_int = 0
        # codconven no MySQL é numérico; em dev (tokens fake) pode vir algo como 'FAKE123'
        # Mantemos apenas dígitos; se não houver, usa '0' como placeholder de desenvolvimento
        codigo_convenio_str = str(codigo_convenio) if codigo_convenio is not None else ''
        codigo_convenio_num = ''.join(ch for ch in codigo_convenio_str if ch.isdigit()) or '0'

        venda = {
            'matricula': dados['matricula'],
            'associado': dados.get('associado',''),
            'sequencia': seq_int,
            'nr_parcelas': nr_parcelas,
            'valor_parcela': f"{valor_parcela:.2f}",
            'valor_total': f"{bruto:.2f}",
            'codigo_convenio': codigo_convenio_num,
            'nome_convenio': nome_convenio,
            'usuario': usuario,
            'data_hora': datetime.now(timezone('America/Sao_Paulo')).strftime('%d-%m-%Y %H:%M'),
            'mes_inicial': mes_inicial,
            'ano_inicial': ano_inicial,
            'mes_final': mes_final,
            'ano_final': ano_final,
            'tipo_flag': 'X' if int(dados['tipo']) == 1 else ''
        }
        self.repo.registrar_venda(venda)
        # Pós-venda: opcional enviar confirmação por WhatsApp
        try:
            self._last_whatsapp_sent_post = False
            self._last_phone_mask_post = None
            post_enabled = getattr(self.settings, 'WHATSAPP_ENABLED', False) and os.getenv('WHATSAPP_SEND_CONFIRM', 'true').lower() in ('1','true','yes')
            if post_enabled and socio.get('celular'):
                primeiro_nome = (socio['associado'] or '').split()[0]
                mensagem_total = format_decimal(bruto, format="#,##0.00;-#", locale='pt_BR')
                mensagem_parcela = format_decimal(valor_parcela, format="#,##0.00;-#", locale='pt_BR')
                self._last_phone_mask_post = self._mask_phone(socio.get('celular'))
                # de-dup confirmação
                id_compra = str(dados.get('id_compra') or '')
                try:
                    ttl = int(getattr(self.settings, 'WHATSAPP_DEDUP_TTL_SECONDS', 180))
                except Exception:
                    ttl = 180
                can_send = not self.mongo.has_whatsapp_event('confirm', dados.get('matricula'), id_compra, ttl_seconds=ttl)
                if can_send:
                    # monta mensagem de confirmação com saldo restante
                    saldo_restante = float(dados.get('saldo')) - float(valor_parcela)
                    saldo_restante_fmt = format_decimal(saldo_restante, format="#,##0.00;-#", locale='pt_BR')
                    confirm_body = (
                        f"🏷️ *_COMPRA :_* {id_compra}\n"
                        f"*_CONCLUÍDA COM SUCESSO!_*\n"
                        "_____________________________________\n"
                        f"💳 *Saldo Restante :* R$ {saldo_restante_fmt}\n\n"
                        "*Extrato completo disponível em:*\n"
                        "https://aspma.vercel.app"
                    )
                    self._last_whatsapp_sent_post = self._send_whatsapp(
                    associado_primeiro_nome=primeiro_nome,
                    convenio=nome_convenio,
                    id_compra=id_compra,
                    valor_total=mensagem_total,
                    nr_parcelas=nr_parcelas,
                    valor_parcela=mensagem_parcela,
                        contato_celular=socio.get('celular'),
                        message_body=confirm_body
                    )
                    if self._last_whatsapp_sent_post:
                        try:
                            self.mongo.record_whatsapp_event('confirm', dados.get('matricula'), id_compra)
                        except Exception:
                            pass
                # Log estruturado pós-venda
                try:
                    from flask import current_app
                    current_app.log_event('convenios_whatsapp_confirm', sent=bool(self._last_whatsapp_sent_post), phone_mask=self._last_phone_mask_post, matricula=dados.get('matricula'), convenio=nome_convenio)
                except Exception:
                    pass
        except Exception:
            # não falha a venda por erro de notificação
            pass
        return True

    def _validar_mes_ano(self, mes_ano: str):
        if not mes_ano or len(mes_ano) != 7 or mes_ano[2] != '-':
            raise ValidationError('mes_ano inválido. Use MM-YYYY')
        try:
            int(mes_ano[:2]); int(mes_ano[-4:])
        except ValueError:
            raise ValidationError('mes_ano inválido. Use MM-YYYY')

    # === Receber Mensais (extrato com desconto e receber) ===
    def listar_receber_mensais(self, codigo: str, mes_ano: str):
        self._validar_mes_ano(mes_ano)
        mes = int(mes_ano[:2]); ano = int(mes_ano[-4:])
        # Reutiliza listar_parcelas para montar "dados" e total
        base = self.listar_parcelas(codigo, mes_ano)
        desconto_percent = self.repo.obter_desconto(codigo)
        try:
            total_float = float(str(base['total']).replace('.', '').replace(',', '.'))
        except Exception:
            # Caso formato inesperado, somar dos itens
            total_float = 0.0
            for item in base['dados']:
                try:
                    total_float += float(str(item['valor']).replace('.', '').replace(',', '.'))
                except Exception:
                    pass
        desconto_val = round(total_float * (desconto_percent/100.0), 2)
        receber_val = round(total_float - desconto_val, 2)
        return {
            'dados': base['dados'],
            'total': format_decimal(total_float, format="#,##0.00;-#", locale='pt_BR'),
            'desconto': format_decimal(desconto_val, format="#,##0.00;-#", locale='pt_BR'),
            'receber': format_decimal(receber_val, format="#,##0.00;-#", locale='pt_BR')
        }

    # === Atualização de Cadastro ===
    def atualizar_cadastro(self, codigo_convenio: str, dados: dict):
        usuario = (dados.get('usuario') or '').lower()
        email = (dados.get('email') or '').lower()
        cpf_cnpj = dados.get('cpf_cnpj') or ''
        fantasia = dados.get('fantasia') or ''
        nome_razao = dados.get('nome_razao') or ''
        if not usuario or not email:
            raise ValidationError('usuario e email são obrigatórios')
        # Atualiza MySQL
        self.repo.atualizar_cadastro_mysql(codigo_convenio, usuario, email, cpf_cnpj, fantasia, nome_razao)
        # Atualiza Mongo (cache login)
        try:
            c = self.mongo._coll('login_convenios')
            if c:
                c.find_one_and_update(
                    {'codigo': codigo_convenio},
                    {'$set': {
                        'usuario': usuario,
                        'email': email,
                        'cpf_cnpj': cpf_cnpj,
                        'fantasia': fantasia,
                        'nomerazao': nome_razao,
                        'bloqueio': 'NAO'
                    }},
                    upsert=True
                )
        except Exception:
            # Falha no cache não deve bloquear operação
            pass
        # Retorna espelho atualizado
        return {
            'usuario': usuario,
            'email': email,
            'cpf_cnpj': cpf_cnpj,
            'fantasia': fantasia,
            'nome_razao': nome_razao
        }
