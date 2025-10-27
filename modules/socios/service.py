from datetime import datetime
from pytz import timezone
from typing import Optional

from core.exceptions import AuthenticationError, ValidationError
from core.security import generate_tokens
from config.settings import Settings
from .models import Socio, LoginResult
from .repository import SociosRepository, SociosMongoRepository

class SociosService:
    """Service com regras de negócio para sócios.

    Permite injeção de dependências (repos e token_provider) para facilitar testes.
    """
    
    def __init__(
        self,
        socios_repo: SociosRepository = None,
        mongo_repo: SociosMongoRepository = None,
        settings: Settings = None,
        token_provider=None,
    ):
        self.socios_repo = socios_repo or SociosRepository()
        self.mongo_repo = mongo_repo or SociosMongoRepository()
        self.settings = settings or Settings()
        self.token_provider = token_provider or (lambda identity: generate_tokens(identity=identity))
    
    def authenticate_extrato(self, matricula: str, cpf: str) -> LoginResult:
        """Autentica sócio via matrícula e fragmento de CPF."""
        try:
            # Leitura dinâmica permite que testes ajustem ENABLE_FAKE_LOGIN após criação do service
            if self._is_fake_mode():
                socio = Socio(
                    matricula=matricula,
                    associado='Usuário Demo',
                    email='demo@example.com',
                    celular='11999999999',
                    bloqueio=None,
                    tipo='A',
                    cpf='12345678901'
                )
                tokens = self.token_provider(socio.matricula)
                return LoginResult(socio, tokens, bloqueio_aspma=None, mes_ano=self._get_current_month_year())
            
            cached_data = self.mongo_repo.find_login_data(matricula)
            if cached_data:
                if self._validate_cpf_fragment(cached_data.get('cpf', ''), cpf):
                    socio = Socio(
                        matricula=cached_data['matricula'],
                        associado=cached_data.get('associado'),
                        email=cached_data.get('email'),
                        celular=cached_data.get('celular'),
                        bloqueio=cached_data.get('bloqueio'),
                        tipo=cached_data.get('tipo'),
                        cpf=cached_data.get('cpf')
                    )
                    tokens = self.token_provider(socio.matricula)
                    bloqueio_aspma = self.socios_repo.get_bloqueio_aspma(matricula)
                    mes_ano = self._get_current_month_year()
                    return LoginResult(socio, tokens, bloqueio_aspma, mes_ano)
                else:
                    raise AuthenticationError("CPF não confere")
            
            socio = self.socios_repo.find_by_matricula_cpf(matricula, cpf)
            if not socio:
                raw = self.socios_repo.fetch_login_row(matricula, cpf)
                if raw:
                    socio = Socio.from_row(raw)
                    socio.cpf = raw[6] if len(raw) > 6 else None
                else:
                    raise AuthenticationError("Credenciais inválidas")
            
            bloqueio_aspma = self.socios_repo.get_bloqueio_aspma(matricula)
            tokens = self.token_provider(socio.matricula)
            
            try:
                self.mongo_repo.store_login_data(socio)
            except Exception:
                pass
            
            mes_ano = self._get_current_month_year()
            return LoginResult(socio, tokens, bloqueio_aspma, mes_ano)
        except AuthenticationError:
            raise
        except Exception as e:
            # fallback genérico
            raise AuthenticationError("Credenciais inválidas")
    
    def _validate_cpf_fragment(self, full_cpf: str, fragment: str) -> bool:
        if not full_cpf or not fragment:
            return False
        clean_cpf = ''.join(c for c in full_cpf if c.isdigit())
        if len(clean_cpf) < 11 or len(fragment) not in (5,6):
            return False
        expected5 = clean_cpf[:3] + clean_cpf[-2:]
        if len(fragment) == 5:
            return expected5 == fragment
        # Para fragmento de 6 dígitos (variação adotada em alguns clientes): primeiros 3 + últimos 3
        expected6 = clean_cpf[:3] + clean_cpf[-3:]
        return fragment == expected6 or fragment == expected5
    
    def _get_current_month_year(self) -> str:
        sao_paulo_tz = timezone('America/Sao_Paulo')
        now = datetime.now(sao_paulo_tz)
        return now.strftime('%m-%Y')

    def _is_fake_mode(self) -> bool:
        from os import getenv
        return getenv('ENABLE_FAKE_LOGIN', str(self.settings.ENABLE_FAKE_LOGIN)).lower() in ('true','1','yes')

    # ==== Margem ====
    def calcular_margem(self, matricula: str) -> dict:
        """Calcula a margem disponível replicando lógica legacy de forma segura.
        Regras:
        - Busca tipo, limite, cpf
        - Se tipo==1: consulta matrícula nova em tabela 'matriculas' e (futuro) integra com serviço externo (placeholder)
        - Caso contrário calcula consumo do mês +1 (após dia 9) ou mês atual (até dia 9)
        - Margem = limite - soma(parcelas)
        """
        # Modo fake login: retorna valores simulados sem acessar banco
        if self._is_fake_mode():
            return {
                'margem': 1000.0,
                'limite': 2000.0,
                'consumo': 1000.0,
                'mes_ref': self._get_current_month_year(),
                'tipo': 'A'
            }
        core = self.socios_repo.get_socio_core(matricula)
        if not core:
            raise AuthenticationError("Sócio não encontrado")
        tipo, limite, cpf = core
        try:
            limite_val = float(limite) if limite is not None else 0.0
        except ValueError:
            limite_val = 0.0

        from datetime import date
        hoje = date.today()
        mes = hoje.month
        ano = hoje.year
        if hoje.day > 9:
            if mes == 12:
                mes = 1
                ano += 1
            else:
                mes += 1

        if str(tipo) == '1':
            # Placeholder: lógica externa (Zetra) – retornar None para margem se não implementado
            matricula_nova = self.socios_repo.get_matricula_atual(matricula) or matricula
            # Aqui poderíamos integrar serviço externo. Devolvendo None sinaliza não calculado localmente.
            return { 'margem': None, 'tipo': tipo, 'matricula': matricula_nova }
        else:
            soma = self.socios_repo.get_sum_parcelas(matricula, ano, mes)
            margem = max(limite_val - soma, 0.0)
            return { 'margem': margem, 'limite': limite_val, 'consumo': soma, 'mes_ref': f"{mes:02d}-{ano}", 'tipo': tipo }

    # ==== Extrato (Descontos Mensais) ====
    def listar_descontos_mensais(self, matricula: str, mes_ano: str):
        """Retorna lista de descontos (parcelas) do mês/ano informado.
        mes_ano formato MM-YYYY
        """
        # Modo fake: retorna vazio formatado
        if self._is_fake_mode():
            return {'dados': [], 'total': '0,00'}
        try:
            if not mes_ano or len(mes_ano) != 7 or mes_ano[2] != '-':
                raise ValidationError("mes_ano inválido. Use MM-YYYY")
            mes = int(mes_ano[:2])
            ano = int(mes_ano[-4:])
        except ValueError:
            raise ValidationError("mes_ano inválido. Use MM-YYYY")

        rows = self.socios_repo.list_parcelas_mes(matricula, mes, ano)
        from babel.numbers import format_decimal
        resultado = []
        total = 0.0
        for r in rows:
            pid, conveniado, emissao, parcelas, valor, nrseq = r
            dia = int(emissao.strftime('%d')) if emissao else 1
            mes_ref = int(emissao.strftime('%m')) if emissao else mes
            ano_ref = int(emissao.strftime('%Y')) if emissao else ano
            if dia > 9:
                if mes_ref == 12:
                    mes_ref = 1
                    ano_ref += 1
                else:
                    mes_ref += 1
            # período final ajustando quantidade de parcelas
            fim_mes = mes_ref
            fim_ano = ano_ref
            for _ in range(1, int(parcelas)):
                if fim_mes == 12:
                    fim_mes = 1
                    fim_ano += 1
                else:
                    fim_mes += 1
            periodo = f"{mes_ref:02d}-{ano_ref} a {fim_mes:02d}-{fim_ano}"  # compatível com legacy
            resultado.append({
                'id': pid,
                'nome_do_convenio': conveniado,
                'data_da_venda': emissao.strftime('%d-%m-%Y') if emissao else None,
                'parcela': nrseq,
                'numero_de_parcelas': str(int(parcelas)).strip(),
                'periodo': periodo,
                'valor_da_parcela': format_decimal(valor, format="#,##0.00;-#", locale='pt_BR')
            })
            total += valor
        total_fmt = format_decimal(total, format="#,##0.00;-#", locale='pt_BR')
        return { 'dados': resultado, 'total': total_fmt }

    # ==== Compras Mensais ====
    def listar_compras_mensais(self, matricula: str, mes_ano: str):
        """Retorna lista de compras do mês/ano informado."""
        if self._is_fake_mode():
            return {'dados': [], 'total': '0,00'}
        try:
            if not mes_ano or len(mes_ano) != 7 or mes_ano[2] != '-':
                raise ValidationError("mes_ano inválido. Use MM-YYYY")
            mes = int(mes_ano[:2])
            ano = int(mes_ano[-4:])
        except ValueError:
            raise ValidationError("mes_ano inválido. Use MM-YYYY")
        rows = self.socios_repo.list_compras_mes(matricula, mes, ano)
        from babel.numbers import format_decimal
        resultado = []
        total = 0.0
        for r in rows:
            emissao, conveniado, parcelas, valor_parcela, vid = r
            resultado.append({
                'id': vid,
                'data_da_venda': emissao.strftime('%d-%m-%Y') if emissao else None,
                'nome_do_convenio': conveniado,
                'numero_de_parcelas': str(int(parcelas)).strip(),
                'valor_da_parcela': format_decimal(valor_parcela, format="#,##0.00;-#", locale='pt_BR')
            })
            total += valor_parcela
        total_fmt = format_decimal(total, format="#,##0.00;-#", locale='pt_BR')
        return { 'dados': resultado, 'total': total_fmt }

    # ==== Código de Compra ====
    def gerar_codigo_compra(self, matricula: str, senha: str, cpf_fragment: str, email: str, celular: str, nova_senha: Optional[str] = None) -> dict:
        """Gera código de compra com controle de tentativas.
        Simplificação em relação ao legado: senha verificada contra cache/login (quando disponível) ou aceita no modo fake.
        Bloqueia após 3 tentativas falhas.
        """
        # Fake mode ignora validações pesadas e sempre retorna código fixo
        if self._is_fake_mode():
            return { 'codigo': 'FAKE1234', 'nr_vezes': 0, 'email': email, 'celular': celular }

        # Verificar bloqueio atual (se armazenado)
        # (No legado bloqueio estava em 'socios_login_cache'; aqui seguimos padrão leve.)
        tentativas = self.mongo_repo.get_tentativas(matricula)
        if tentativas >= 3:
            raise AuthenticationError('Matrícula bloqueada por tentativas excedidas')

        # Buscar login cache para validar senha / cpf simplificados
        cache = self.mongo_repo.find_login_data(matricula)
        if not cache:
            # exigir autenticação prévia (login-extrato populando cache)
            raise AuthenticationError('Sessão não autenticada ou expirada')

        # Validação mínima de CPF fragment (mesma regra de login: primeiros 3 + últimos 2)
        if not self._validate_cpf_fragment(cache.get('cpf', ''), cpf_fragment):
            nr = self.mongo_repo.incrementar_tentativa(matricula)
            if nr >= 3:
                self.mongo_repo.set_bloqueio_login_cache(matricula, 'OK')
            raise AuthenticationError('CPF inválido')

        # Verificação de senha: legado usa hash Bcrypt; se armazenada no cache (opcional).
        from bcrypt import checkpw, gensalt, hashpw
        senha_hash = cache.get('senha')
        if senha_hash and not checkpw(senha.encode('utf8'), senha_hash):
            nr = self.mongo_repo.incrementar_tentativa(matricula)
            if nr >= 3:
                self.mongo_repo.set_bloqueio_login_cache(matricula, 'OK')
            raise AuthenticationError('Senha inválida')

        # Reset tentativas em sucesso
        self.mongo_repo.reset_tentativas(matricula)
        self.mongo_repo.set_bloqueio_login_cache(matricula, 'NAO')

        # Atualizar senha se nova_senha fornecida
        associados_update = {}
        if nova_senha:
            associados_update['senha'] = hashpw(nova_senha.encode('utf8'), gensalt())
        associados_update.update({
            'associado': cache.get('associado'),
            'tipo': cache.get('tipo'),
            'cpf': cache.get('cpf'),
            'email': email.lower(),
            'celular': celular,
            'bloqueio': 'NAO'
        })

        # Gerar código único
        import secrets
        codigo = None
        for _ in range(10):  # até 10 tentativas para colisão improvável
            c = secrets.token_hex(3).upper()  # 6 hex chars
            if not self.mongo_repo.codigo_existe(c):
                codigo = c
                break
        if not codigo:
            raise ValidationError('Falha ao gerar código')

        self.mongo_repo.store_codigo_compra(matricula, codigo, associados_update)
        return { 'codigo': codigo, 'nr_vezes': 0, 'email': email.lower(), 'celular': celular }