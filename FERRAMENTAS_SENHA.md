# Ferramentas de Gerenciamento de Senha - Convênios

## Scripts Criados

### 1. desbloquear_senha_direct.py

Script direto que conecta ao MongoDB sem importar o Flask app.

#### Uso:

```bash
# Listar todos os convênios bloqueados
python3 desbloquear_senha_direct.py --listar

# Desbloquear um convênio específico
python3 desbloquear_senha_direct.py <codigo_convenio>

# Desbloquear todos os convênios
python3 desbloquear_senha_direct.py --todos
```

#### Exemplos:

```bash
# Ver quais convênios estão bloqueados
cd /media/araudata/829AE33A9AE328FD/UBUNTU/consig-express-315/backend
python3 desbloquear_senha_direct.py --listar

# Desbloquear o convênio com código "123"
python3 desbloquear_senha_direct.py 123

# Desbloquear todos de uma vez (útil para desenvolvimento)
python3 desbloquear_senha_direct.py --todos
```

## O que o script faz:

1. **Remove o bloqueio** na collection `login_convenios` (muda `bloqueio` de "SIM" para "NAO")
2. **Reseta tentativas** (remove o campo `tentativas`)
3. **Remove registros** da collection `tentativas_convenio`

## Configuração do MongoDB

O script usa as variáveis de ambiente:
- `MONGO_URI` (padrão: `mongodb://localhost:27017/`)
- `MONGO_DB` (padrão: `aspmadb`)

## Estrutura das Collections

### login_convenios
```json
{
  "codigo": "123",
  "bloqueio": "SIM",  // ou "NAO"
  "tentativas": 3,
  "senha": "$2b$12$..."  // hash bcrypt
}
```

### tentativas_convenio
```json
{
  "codigo": "123",
  "tentativas": 3
}
```

## Atualizações de Autenticação

### Login e Autenticação Híbridos

Ambos os métodos agora suportam:

1. **Senhas criptografadas com bcrypt** (formato: `$2b$12$...`)
2. **Senhas em texto plano** (legado/compatibilidade)

#### Detecção automática:
```python
if senha_mysql.startswith('$2') and len(senha_mysql) >= 59:
    # Usa bcrypt checkpw()
else:
    # Compara texto plano
```

### Endpoints Atualizados

#### `/api/convenios/login` (POST)
- Verifica primeiro MongoDB (hash bcrypt)
- Fallback para MySQL com validação híbrida
- Atualiza MongoDB após login bem-sucedido

#### `/api/convenios/autenticacao` (POST)
- Confirma senha para ações sensíveis
- Mesma lógica híbrida do login
- Mantém sistema de bloqueio e tentativas

### Segurança Mantida

- Limite de tentativas configurável (`MAX_TENTATIVAS_CONVENIO`)
- Bloqueio automático após exceder tentativas
- Reset de tentativas em login bem-sucedido
- Atualização progressiva para bcrypt (migração gradual)

## Fluxo de Migração de Senhas

1. **Senha legado (plain text)** → Login com sucesso → **Cria hash bcrypt no MongoDB**
2. **Próximos logins** → Usa hash do MongoDB (mais rápido)
3. **Alterar senha** → Cria hash bcrypt e salva no MySQL
4. **Compatibilidade total** → Funciona com senhas antigas e novas

## Troubleshooting

### Problema: Convênio bloqueado
**Solução:**
```bash
python3 desbloquear_senha_direct.py <codigo_convenio>
```

### Problema: Senha não funciona após alteração
**Causa:** Pode estar usando bcrypt mas login não detectando
**Solução:** Já corrigido! O sistema agora detecta automaticamente.

### Problema: MongoDB não conecta
**Verificar:**
1. MongoDB está rodando? `sudo systemctl status mongod`
2. Variáveis de ambiente corretas? Ver `.env` ou `config.py`
3. Porta correta? Padrão é 27017

## Desenvolvimento Local

Para desbloquear tudo durante desenvolvimento:
```bash
cd backend
python3 desbloquear_senha_direct.py --todos
```

Isso reseta todos os bloqueios e tentativas, útil para testar fluxos de autenticação.
