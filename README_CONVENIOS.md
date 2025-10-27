# Convenios API - Guia Rápido

## Endpoints Principais

| Função | Novo Endpoint | Legacy Compat | Observações |
|--------|---------------|---------------|-------------|
| Login Convênio | `POST /api/convenios/login` | `POST /login_convenios` (delegação) / `POST /legacy/login_convenios_format_old` | Preferir o novo. Legacy antigo será descontinuado. |
| Parcelas | `POST /api/convenios/parcelas` | - | Requer JWT. |
| Compras | `POST /api/convenios/compras` | - | Requer JWT. |
| Enviar Código (logado) | `POST /api/convenios/enviar-codigo` | - | Rate limit aplicado. |
| Alterar Senha com Código (logado) | `POST /api/convenios/alterar-senha-codigo` | - | Requer JWT. |
| Esqueceu: Enviar Código | `POST /api/convenios/esqueceu/enviar-codigo` | - | Rate limit aplicado. |
| Esqueceu: Alterar com Código | `POST /api/convenios/esqueceu/alterar-senha` | - | - |
| Calcular Limite | `POST /api/convenios/limite` | - | Requer JWT. |
| Registrar Venda com Senha | `POST /api/convenios/venda-senha` | - | Requer JWT. |

## Formato de Login (Novo)
Request JSON:
```
{
  "usuario": "LOJA01",
  "senha": "minhaSenha"
}
```

Response (sucesso):
```
{
  "success": true,
  "data": {
    "tokens": {
      "access_token": "...",
      "refresh_token": "...",
      "token_type": "Bearer",
      "fake": false
    },
    "dados": {
      "codigo": "...",
      "nome_razao": "...",
      "usuario": "...",
      "email": "...",
      "cpf_cnpj": "...",
      "fantasia": "...",
      "desconto": 0.0,
      "parcelas": 12,
      "libera": "S",
      "mes_ano": "10-2025"
    }
  },
  "meta": {
    "timestamp": "...",
    "request_id": "...",
    "fake_login": true
  }
}
```

## Formato Legacy Antigo (ainda suportado)
`POST /legacy/login_convenios_format_old`
```
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "Bearer",
  "dados": { ... },
  "fake_login": true
}
```

## Modo Fake de Desenvolvimento
- Ative com `ENABLE_FAKE_LOGIN=true` (variável de ambiente).
- Use a senha especial: `__dev__`.
- Qualquer `usuario` será aceito e retornará um convênio simulado.
- Os tokens conterão claim `fake: true` e a resposta incluirá `meta.fake_login=true`.
- Nunca usar em produção.

## Códigos de Erro Relevantes
| Código | HTTP | Significado |
|--------|------|-------------|
| VALIDATION_ERROR | 400 | Dados inválidos no payload |
| AUTH_ERROR | 401 | Falha de autenticação (credenciais ou bloqueio) |
| BACKEND_UNAVAILABLE | 503 | Infraestrutura (Mongo/MySQL) indisponível |
| INTERNAL_ERROR | 500 | Erro não previsto |

## Campos Alternativos Aceitos no Login
O backend normaliza automaticamente:
- Para usuário: `user`, `username`, `login`, `codigo`, `cnpj`
- Para senha: `password`, `pass`, `senha_convenio`, `pwd`
- Formato antigo: `{ "dados": { "usuario": "...", "senha": "..." } }`

## Estratégia de Descontinuação
1. Incentivar consumo de `/api/convenios/login` imediatamente.
2. Monitorar uso de `/login_convenios` e `/legacy/login_convenios_format_old`.
3. Anunciar remoção após estabilidade (ex: 30 dias sem uso relevante).

## Testes Cobertos
- Login modo fake (payload plano / alternativo / legacy wrapper)
- Infra 503 (simulado)
- Formato legacy old format

## Checklist de Migração Frontend
- [x] Ajustar chamada para `/api/convenios/login`.
- [x] Normalizar resposta nova para formato antigo no front (feito em `Login.jsx`).
- [ ] Exibir aviso visual quando `fake_login` = true (opcional).
- [ ] Centralizar lógica de auth em hook reutilizável (opcional).

## Exemplo de Uso de Refresh (futuro)
Planejar endpoint `/api/auth/refresh` para renovar tokens (não implementado aqui). Até lá, reautenticar ao expirar.

## Variáveis de Ambiente Relevantes
Configure no arquivo `.env` (não commitar segredos):
```
MYSQL_HOST=...
MYSQL_PORT=3306
MYSQL_USER=...
MYSQL_PASSWORD=...
MYSQL_DATABASE=aspma

MONGO_URI=mongodb://user:pass@host:27017/consigexpress
MONGO_DATABASE=consigexpress

RECAPTCHA_SECRET_KEY=chave_recaptcha
ENABLE_FAKE_LOGIN=false
MAX_TENTATIVAS_CONVENIO=5

# WhatsApp (WhatsGw) - opcional
WHATSAPP_ENABLED=false
WHATS_GW_API_URL=https://app.whatsgw.com.br/api/WhatsGw/Send
WHATS_GW_APIKEY=
WHATS_GW_SENDER=
WHATS_DEFAULT_DDD=41
```

Ao migrar do código legacy `convenios.py`, todos os segredos hard-coded foram removidos e agora são lidos via `config.settings.Settings`.

## Observabilidade / Saúde
- Endpoint: `GET /api/health` retorna status de MySQL e Mongo.
- Produção: configure `RATELIMIT_STORAGE_URL=redis://host:6379/0` (evitar in-memory).

## Deprecação de Endpoints Legacy
Feature flags (variáveis de ambiente / settings):
- `LEGACY_CONVENIOS_ENABLED` (default true) controla registro das rotas antigas.
- `LEGACY_CONVENIOS_SOFT_DEPRECATION` injeta cabeçalhos de aviso.

Cabeçalhos adicionados em modo soft:
```
Deprecation: true
Sunset: 2025-12-31
Link: <https://intranet/convenios/migracao>; rel="deprecation"
```
Teste automatizado: `tests/test_legacy_deprecation.py` valida presença dos cabeçalhos.

Plano de desligamento:
1. Ativar `LEGACY_CONVENIOS_SOFT_DEPRECATION=true` (fase de aviso) – já ativo.
2. Monitorar acessos (logs estruturados).
3. Definir data final e comunicar.
4. Setar `LEGACY_CONVENIOS_ENABLED=false` em staging → validar front.
5. Replicar em produção após 0 erros.

## Integração Frontend (Resumo)
O frontend já usa `/api/convenios/*` e mantém contadores de fallback em `sessionStorage` para medir tentativas de uso de fluxos migrados.
Notificações migradas para `react-hot-toast`; removido `light-toast` (07/10/2025).

## WhatsApp no fluxo de Limite e Pós-Venda
- Quando `WHATSAPP_ENABLED=true` e credenciais válidas forem configuradas, o backend tentará enviar:
  - Uma mensagem ao consultar limite (pré-venda), e
  - Uma confirmação após registrar a venda.
- O envio é best-effort: falhas não bloqueiam o fluxo; eventos são registrados em logs estruturados.

### Campos adicionais nas respostas
- `POST /api/convenios/limite` retorna em `data`:
  - `id_compra`: identificador gerado para o cálculo/fluxo da compra
  - `phone_mask`: telefone mascarado do associado (ex.: (41) 9****-1234), quando disponível
  - `whatsapp_sent`: booleano indicando se a mensagem pré-venda foi enviada

- `POST /api/convenios/venda-senha` retorna em `data`:
  - `whatsapp_confirm_sent`: booleano indicando se a confirmação foi enviada
  - `phone_mask`: o mesmo telefone mascarado usado para a confirmação

Observações:
- A máscara é derivada do campo `celular` do associado, quando existente.
- Para ambientes de desenvolvimento, mantenha `WHATSAPP_ENABLED=false`.


---
Documentação gerada automaticamente durante refatoração (07/10/2025).
