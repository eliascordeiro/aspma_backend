# Backend ASPMA - Arquitetura MVC

## 📋 Visão Geral

Este projeto implementa uma API RESTful para o sistema ASPMA (Associação de Serviços Públicos Municipal de Aparecida) utilizando arquitetura MVC com Flask.

## 🏗️ Arquitetura

### Estrutura de Pastas

```
backend/
├── config/                 # Configurações da aplicação
│   ├── settings.py         # Configurações baseadas em ambiente
│   └── database.py         # Gerenciamento de conexões BD
├── core/                   # Funcionalidades centrais
│   ├── exceptions.py       # Hierarquia de exceções customizadas
│   ├── responses.py        # Padronização de respostas JSON
│   └── security.py         # JWT, rate limiting, CORS
├── modules/                # Módulos de domínio
│   └── socios/             # Módulo de sócios
│       ├── models.py       # Entidades de domínio
│       ├── repository.py   # Acesso a dados (MySQL/MongoDB)
│       ├── service.py      # Regras de negócio
│       ├── routes.py       # Endpoints da API
│       └── schemas.py      # Validação de entrada/saída
├── app_mvc.py              # Application Factory (nova arquitetura)
├── app.py                  # Aplicação legacy (compatibilidade)
└── requirements.txt        # Dependências Python
```

### Princípios Arquiteturais

- **Separação de Responsabilidades**: Cada camada tem uma responsabilidade específica
- **Injeção de Dependência**: Repositórios e serviços são injetáveis
- **Configuração por Ambiente**: Settings baseadas em variáveis de ambiente
- **Segurança por Design**: Rate limiting, validação, JWT, queries parametrizadas
- **Testabilidade**: Estrutura facilita criação de testes unitários

## 🚀 Execução

### Configuração Inicial

1. **Instalar dependências**:
```bash
pip install -r requirements.txt
```

2. **Configurar ambiente**:
```bash
cp .env.example .env
# Edite .env conforme sua infra (MySQL, Mongo, JWT, etc.)
```

3. **Rodar aplicação (nova arquitetura)**:
```bash
python app_mvc.py
```

4. **Rodar aplicação legacy (opcional durante migração)**:
```bash
python app.py
```

## 🔧 Configuração

### Variáveis de Ambiente

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `FLASK_ENV` | Ambiente de execução | `development` |
| `MYSQL_HOST` | Host do MySQL | `localhost` |
| `MYSQL_PORT` | Porta MySQL | `3306` |
| `MYSQL_USER` | Usuário MySQL | `aspma_user` |
| `MYSQL_PASSWORD` | Senha MySQL | `senha123` |
| `MYSQL_DATABASE` | Database MySQL | `aspma_db` |
| `MONGO_URI` / `MONGODB_URI` | URI do MongoDB | `mongodb://localhost:27017` |
| `MONGO_DATABASE` | Nome database Mongo | `consigexpress` |
| `JWT_SECRET_KEY` | Chave secreta JWT | `chave-super-secreta` |
| `JWT_ACCESS_TOKEN_HOURS` | Horas expiração access | `24` |
| `JWT_REFRESH_TOKEN_DAYS` | Dias expiração refresh | `30` |
| `ENABLE_FAKE_LOGIN` | Modo fake (dev/test) | `true` |
| `CORS_ORIGINS` | Origens CORS | `*` |
| `TOKEN_BLOCKLIST_REDIS_URL` | Redis p/ blocklist | `redis://localhost:6379/0` |
| `MAX_TENTATIVAS_CONVENIO` | Tentativas de login convênio antes de bloqueio | `5` |

## 🛡️ Segurança

### Melhorias Implementadas

- ✅ Queries Parametrizadas (anti SQL Injection)
- ✅ Validação de entrada (Marshmallow)
- ✅ JWT (access + refresh) + refresh endpoint
- ✅ Rate Limiting (flask-limiter)
- ✅ Blocklist de Tokens (in-memory ou Redis)
- ✅ Logs estruturados e centralizados
- ✅ CORS configurável
- ✅ Modo Fake para testes rápidos sem DB

### Vulnerabilidades Corrigidas

| Tipo | Localização Original | Status |
|------|---------------------|--------|
| SQL Injection | `socios.py` linhas 89, 152, 203, 267, etc | ✅ Corrigido |
| Credenciais Hardcoded | `convenios.py` linha 45 | ✅ Corrigido |
**Última Atualização**: Outubro 2025
| Validação Insuficiente | Parâmetros de entrada | ✅ Corrigido |

## 📚 Endpoints

### Módulo Sócios

| Método | Endpoint | Descrição | Status |
|--------|----------|-----------|--------|
| `POST` | `/api/socios/login-extrato` | Login via matrícula + CPF | ✅ Migrado |
| `POST` | `/api/socios/margem` | Consulta margem empréstimo | ✅ Migrado |
| `POST` | `/api/socios/extrato` | Extrato consignações | ✅ Migrado |
| `POST` | `/api/socios/compras` | Compras mensais | ✅ Migrado |
| `POST` | `/api/socios/codigo-compra` | Geração de código de compra | ✅ Migrado |
| `POST` | `/api/socios/refresh` | Renovar access token | ✅ Migrado |
| `POST` | `/api/socios/logout` | Revogar tokens (logout) | ✅ Migrado |

### Módulo Convênios

| Método | Endpoint | Descrição | Status |
|--------|----------|-----------|--------|
| `POST` | `/api/convenios/login` | Login convênio (usuario/senha) | ✅ Migrado (identity dict) |
| `POST` | `/api/convenios/parcelas` | Parcelas (mês/ano) | ✅ Migrado |
| `POST` | `/api/convenios/compras` | Compras (mês/ano) | ✅ Migrado |
| `POST` | `/api/convenios/enviar-codigo` | Envia código p/ alteração de senha (autenticado) | ✅ Migrado |
| `POST` | `/api/convenios/alterar-senha-codigo` | Altera senha usando código (autenticado) | ✅ Migrado |
| `POST` | `/api/convenios/esqueceu/enviar-codigo` | Envia código (fluxo esqueceu) | ✅ Migrado |
| `POST` | `/api/convenios/esqueceu/alterar-senha` | Altera senha (fluxo esqueceu) | ✅ Migrado |
| `POST` | `/api/convenios/limite` | Cálculo de limite/saldo (simplificado) | ✅ Migrado (fase 1) |
| `POST` | `/api/convenios/venda-senha` | Registro de venda simplificada | ✅ Migrado (fase 1) |

> Próximos: integração externa (ZETRA / WhatsApp), bloqueio de tentativas, registro completo de vendas.

#### Formato de Identity JWT (Convênios)

Tokens de convênios agora usam um `identity` estruturado armazenado em **claim custom** `identity`. O `sub` (subject) permanece apenas como string simples (o código do convênio) para compatibilidade com validações do PyJWT / Flask-JWT-Extended que exigem `sub` string. Exemplo de payload relevante:
```json
{
  "tipo": "convenio",
  "codigo": "00123",
  "nome_razao": "CONVENIO EXEMPLO LTDA",
  "usuario": "adminconv"
}
```
No token:
```jsonc
{
  "sub": "00123",              // apenas o código (string)
  "identity": {                 // claim custom com o payload completo
    "tipo": "convenio",
    "codigo": "00123",
    "nome_razao": "CONVENIO EXEMPLO LTDA",
    "usuario": "adminconv"
  },
  "exp": 1730860000,
  "iat": 1730773600,
  "jti": "..."
}
```
Para compatibilidade com tokens antigos (onde o dict vinha diretamente em `sub`), um helper `_current_convenio_identity()` foi introduzido em `modules/convenios/routes.py`. Endpoints novos devem usar esse helper ao invés de chamar diretamente `get_jwt_identity()`.

Benefícios:
1. Compatibilidade com validação de subject estritamente string.
2. Payload de identidade rico disponível para auditoria e autorização futura.
3. Camada de extração centralizada reduz duplicação.

Impacto em clientes: nenhum ajuste caso só transmitam o token; apenas consumidores internos precisaram adaptar a extração de identity.

#### Rate Limiting Convênios

Endpoints sensíveis receberam limites específicos usando `flask-limiter`:

| Endpoint | Limites | Chave (key_func) | Objetivo |
|----------|---------|------------------|----------|
| `POST /api/convenios/enviar-codigo` | `5/hour; 2/minute` | IP + email | Evitar abuso de envio de código autenticado |
| `POST /api/convenios/esqueceu/enviar-codigo` | `3/hour; 2/10minute` | IP + email | Mitigar enumeração / força bruta de reset |

Resposta quando excedido:
```json
{
  "success": false,
  "message": "Limite de requisições excedido",
  "code": "RATE_LIMIT"
}
```
Configuração global padrão pode ser ajustada via `RATELIMIT_DEFAULT` e backend de armazenamento via `RATELIMIT_STORAGE_URL` (ex.: Redis para pods múltiplos). Falha de backend → fallback em memória.

Desabilitar em desenvolvimento:

- Defina `DISABLE_RATE_LIMIT=true` no `.env` ou inicie com `FLASK_ENV=development` para ativar um `DummyLimiter` que não aplica limites. Útil para testes locais do fluxo de e-mail sem receber 429.


#### Política de Tentativas / Bloqueio (Convênios)

Além de rate limiting por IP+email, há controle de tentativas de autenticação por convênio:

| Item | Descrição |
|------|-----------|
| Persistência | Coleções Mongo: `tentativas_convenio` (contador), `login_convenios` (flag `bloqueio`) |
| Limite | Definido por `MAX_TENTATIVAS_CONVENIO` (padrão 5) |
| Incremento | Cada credencial inválida incrementa contador (upsert) |
| Bloqueio | Ao atingir o limite: `login_convenios.bloqueio = 'SIM'` |
| Reset | No login bem-sucedido o contador é removido (`tentativas_convenio`) |
| Mensagens | Enquanto não bloqueado: inclui tentativas restantes; após bloqueio retorna mensagem de bloqueio |

Fluxo resumido:
1. Verifica se já está bloqueado (flag em `login_convenios`).
2. Autenticação MySQL falhou → incrementa tentativas; se >= limite → marca bloqueio e retorna erro definitivo.
3. Sucesso → reseta tentativas e continua emissão de tokens.

Boas práticas:
* Monitorar métricas de bloqueio (contagem de documentos em `tentativas_convenio` com valor próximo do limite).
* Disponibilizar endpoint administrativo futuro para desbloqueio manual (roadmap).
* Considerar expiração automática (TTL) de tentativas se requisito de negócio surgir.

#### Migração de Configuração (Settings vs Config legacy)

Foi introduzido `config/settings.py` como fonte principal de configuração (carregada no Application Factory `app_mvc.create_app()`). O arquivo legacy `config.py` permanece apenas para compatibilidade temporária e está marcado como **deprecated**. Novos módulos devem importar: 

```python
from config.settings import Settings
settings = Settings()
```

Próximos passos planejados: remover importações diretas de `Config` restantes e finalmente excluir `config.py` após estabilização externa (deploys / scripts).

#### Auditoria & Próximos Itens (Convênios)

Pendentes para próximas iterações:
1. Bloqueio progressivo de login (uso de coleções `tentativas_convenio` + `login_convenios`).
2. Registro estruturado de eventos de venda (auditoria / trilha). 
3. Normalização de logs de segurança (JSON) + correlação por `request_id`.
4. Testes adicionais para limites (casos de corte dia > CORTE_DIA) e revalidação negativa.

#### Login Extrato

**Request**:
```json
{
  "matricula": "123456",
  "cpf": "123456"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "matricula": "123456",
    "nome": "João Silva",
    "email": "joao@email.com", 
    "access_token": "eyJ0eXAiOiJKV1Q...",
    "refresh_token": "eyJ0eXAiOiJKV1Q...",
    "mes_ano": "12-2023"
  },
  "request_id": "req_abc123",
  "timestamp": "2023-12-01T10:00:00Z"
}
```

## 🧪 Testes

Testes implementados:

| Arquivo | Escopo |
|---------|--------|
| `tests/test_service_login.py` | Serviço de login / autenticação |
| `tests/test_service_margem.py` | Cálculo de margem |
| `tests/test_service_extrato.py` | Descontos mensais |
| `tests/test_service_compras.py` | Compras mensais |
| `tests/test_codigo_compra.py` | Geração de código (negócio) |
| `tests/test_integration_codigo_compra.py` | Integração (fake mode) |
| `tests/test_refresh_token.py` | Fluxo refresh token |
| `tests/test_logout.py` | Revogação e logout |
| `tests/test_convenios_service.py` | Fluxos de senha e identity convênios |
| `tests/test_convenios_limite_venda.py` | Cálculo de limite e registro de venda (validações & revalidação) |
| `tests/test_convenios_ratelimit.py` | Verificação de rate limiting endpoints convênios |
| `tests/test_smoke_app.py` | Smoke (health check + import WSGI) |

Novos testes cobrem:
- Geração de código de alteração de senha (mock mail)
- Alteração de senha (código autenticado e fluxo esqueceu)
- Estrutura de identity no token JWT de convênio

Planejado (convênios):
1. Testes para `calcular_limite` (limites, mês de corte, saldo insuficiente)
2. Testes para `registrar_venda_senha` com repo fake (persistência simulada)
3. Casos de erro (código inválido, email divergente, etc.) já cobertos parcialmente.

Atualização: itens 1 e 2 parcialmente cobertos em `test_convenios_limite_venda.py`; expandir casos de corte e tipos especiais (tipo==1) nas próximas versões.

Planejado: reorganizar em `unit/` e `integration/`, adicionar `conftest.py` com fixtures compartilhadas, mock de DB e cobertura de convênios.

## 📈 Migração

### Estratégia de Migração

1. **Fase 1**: Estrutura base e primeiro endpoint (Login Extrato) ✅
2. **Fase 2**: Migração endpoints restantes do módulo sócios
3. **Fase 3**: Migração módulo convênios
4. **Fase 4**: Migração módulos aspma e araudata
5. **Fase 5**: Remoção código legacy

### Compatibilidade

Durante a migração, ambas aplicações funcionam simultaneamente:
- **Nova arquitetura**: `http://localhost:5000/api/`
- **Legacy com prefixo**: `http://localhost:5000/legacy/`

## 🔍 Monitoramento

### Logs Estruturados

```python
# Exemplo de log
{
  "timestamp": "2023-12-01T10:00:00Z",
  "level": "INFO", 
  "module": "socios.service",
  "message": "Login realizado com sucesso",
  "matricula": "123456",
  "request_id": "req_abc123"
}
```

### Métricas de Segurança

- Tentativas de login por IP
- Requests bloqueados por rate limiting  
- Tokens JWT expirados
- Tentativas de SQL injection detectadas

## 🤝 Contribuição

### Padrões de Código

- **PEP 8**: Estilo de código Python
- **Type Hints**: Tipagem estática quando possível
- **Docstrings**: Documentação de classes e métodos
- **Testes**: Cobertura mínima de 80%

### Fluxo de Desenvolvimento

1. Criar branch feature
2. Implementar testes
3. Implementar funcionalidade
4. Code review
5. Merge para main

---

**Versão**: 1.2.0  
**Última Atualização**: Outubro 2025

---

### 🔐 Blocklist / Redis

Para revogação de tokens em produção recomenda-se Redis:

```bash
TOKEN_BLOCKLIST_REDIS_URL=redis://usuario:senha@host:6379/0
```

Funcionamento:
* Chaves `blk:<jti>` com TTL até expiração do token.
* Falha de conexão → fallback para memória.

Endpoints relacionados:
* `POST /api/socios/refresh` – novo access via refresh.
* `POST /api/socios/logout` – revoga access atual e opcionalmente refresh (enviar `refresh_jti` & `refresh_exp`).

Boas práticas:
1. Rotacionar refresh tokens a cada uso.
2. Access tokens curtos (ex: 15–30m) + refresh longo (7–30d).
3. Monitorar tamanho da blocklist (Redis INFO + contagem de chaves `blk:*`).