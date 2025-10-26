# Desbloqueio de Senha - Relatório

## 📋 Status do Desbloqueio

**Data:** 25 de outubro de 2025  
**Operação:** Desbloqueio completo de tentativas de login

### ✅ Resultado da Operação

```
Registros desbloqueados:
- Logins bloqueados: 1 registro
- Tentativas removidas: 2 registros
- Status final: Todos os bloqueios removidos
```

## 🔍 Análise do Bloqueio

### Causa do Bloqueio
O sistema bloqueia automaticamente após tentativas de login com credenciais inválidas:
- **Limite de tentativas:** Configurável em `MAX_TENTATIVAS_CONVENIO`
- **Ação de bloqueio:** Define `bloqueio: 'SIM'` no MongoDB
- **Registro de tentativas:** Armazena contador em collection separada

### Onde o Bloqueio é Verificado
```python
# backend/modules/convenios/service.py (linhas 155-220)

# 1. Verifica bloqueio antes de processar login
if login_doc and login_doc.get('bloqueio') == 'SIM':
    raise AuthenticationError('Usuário bloqueado. Contate suporte.')

# 2. Incrementa tentativas em caso de erro
tentativas = self.mongo.incrementar_tentativas(codigo)
if tentativas >= max_tent:
    self.mongo.bloquear_login(codigo)
    raise AuthenticationError('Usuário bloqueado por tentativas excedidas')
```

## 🛠️ Ferramentas de Desbloqueio

### 1. desbloquear_por_usuario.py
**Melhor opção** - Busca código no MySQL e desbloqueia

```bash
# Desbloquear usuário específico
python3 desbloquear_por_usuario.py <nome_usuario>

# Desbloquear todos
python3 desbloquear_por_usuario.py --todos
```

### 2. desbloquear_senha_direct.py
Desbloqueia por código do convênio

```bash
# Desbloquear por código
python3 desbloquear_senha_direct.py <codigo>

# Desbloquear todos
python3 desbloquear_senha_direct.py --todos
```

### 3. verificar_status_login.py
Verificar status atual dos bloqueios

```bash
# Ver status
python3 verificar_status_login.py

# Limpar tudo
python3 verificar_status_login.py --limpar
```

## 📊 Collections MongoDB Afetadas

### login_convenios
Armazena informações de login incluindo bloqueio:
```json
{
  "_id": ObjectId("..."),
  "codigo": "123",
  "bloqueio": "NAO",  // ou "SIM" quando bloqueado
  "tentativas": 3,    // removido após desbloqueio
  "senha": "$2b$12$..."
}
```

### tentativas_convenio
Armazena contador temporário de tentativas:
```json
{
  "_id": ObjectId("..."),
  "codigo": "123",
  "tentativas": 3
}
```

## 🔐 Sistema de Segurança

### Fluxo de Bloqueio
1. **Tentativa de login com credenciais inválidas**
2. **Incrementa contador** em `tentativas_convenio`
3. **Verifica limite** (`MAX_TENTATIVAS_CONVENIO`)
4. **Bloqueia** se exceder (`bloqueio: 'SIM'`)
5. **Requer desbloqueio manual** ou via "Esqueci a senha"

### Fluxo de Desbloqueio Manual
1. **Executar script** de desbloqueio
2. **Atualiza MongoDB** (`bloqueio: 'NAO'`)
3. **Remove tentativas** (zera contador)
4. **Usuário pode tentar login** novamente

### Desbloqueio Automático
- Via fluxo "Alterar Senha" (`#/alterar_senha`)
- Envia código por e-mail
- Reseta bloqueio após alteração bem-sucedida

## 🚨 Logs Importantes

### Mensagens de Bloqueio no Frontend
- "Usuário bloqueado. Contate suporte."
- "Usuário bloqueado por tentativas excedidas"
- "Credenciais inválidas. Tentativas restantes: X"

### Como Identificar Bloqueio
```bash
# Ver logs do backend
grep "bloqueio" backend/logs/*.log

# Ver registros no MongoDB
python3 verificar_status_login.py
```

## 💡 Recomendações

### Para Desenvolvimento
```bash
# Sempre que houver bloqueio em teste
cd backend
python3 desbloquear_por_usuario.py --todos
```

### Para Produção
1. **Não desbloquear automaticamente** - Política de segurança
2. **Orientar usuário** para "Esqueci a senha"
3. **Registrar desbloqueios** manuais em log
4. **Monitorar tentativas** frequentes

## 📝 Alterações Recentes

### Validação de Login Atualizada
- ✅ Suporte a senhas bcrypt (hash `$2b$...`)
- ✅ Compatibilidade com senhas plain text (legado)
- ✅ maxLength aumentado para 255 caracteres
- ✅ Sem restrição de comprimento mínimo
- ✅ Aceita caracteres especiais

### Campos Atualizados
```jsx
// LoginFormMaterial.jsx
{...register('senhaDisplay', { 
  required: true, 
  maxLength: 255  // Era 32, agora 255
  // Removido: minLength: 4
  // Removido: pattern: /^[A-Za-z0-9]+$/
})}
```

## 🎯 Status Final

- ✅ Todos os bloqueios removidos
- ✅ Tentativas zeradas
- ✅ Sistema pronto para novos logins
- ✅ Ferramentas de desbloqueio documentadas
- ✅ Validações de senha atualizadas

**Sistema operacional e seguro! 🚀**
