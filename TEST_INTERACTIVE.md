# 🧪 Guia Completo de Testes Interativos - Invest Explorer MVP

> **Tempo estimado:** 10 minutos  
> **Pré-requisitos:** API + Web rodando, `test_integration.py` passou ✓

---

## 🎯 Teste 1: Login Anônimo Supabase (1 min)

### 📍 Ir para

```
http://localhost:3000
```

### ✅ Esperado

- Página carrega com título "Invest Explorer"
- Subtítulo em português
- Seção "Configurações" visível
- Status: "Sem sessão ativa"

### 🔧 Ação

1. Scroll até "Configurações"
2. Clicar botão azul "Entrar anonimamente"
3. Aguardar 1-2 segundos

### ✅ Resultado Esperado

- Botão desaparece
- Texto muda para "Sessão Supabase ativa"
- Sem mensagens de erro

**❌ Se falhar:**

- Mensagem: "Não foi possível autenticar..." → Anonymous Auth não habilitado no Supabase
- Mensagem: "Configure NEXT_PUBLIC_SUPABASE..." → .env.local não setup

---

## 🎯 Teste 2: Atualizar Snapshot (2 min)

### 📍 Local

Topo da página, botão "Atualizar agora"

### 🔧 Ação

1. Clicar botão "Atualizar agora"
2. Aguardar 5-10 segundos (buscando preços ao vivo)

### ✅ Resultado Esperado

- Mensagem: "Snapshot refreshed with live/fallback prices..."
- Timestamp muda (hora atualizada)
- "Assets ao vivo: 20" (ou próximo a isso)

**Exemplo saída:**

```
Snapshot em 26/3/2026, 14:35:22 • Base: BRL
```

**❌ Se falhar:**

- Timeout → yfinance lento (normal em dev, retry)
- 401 Unauthorized → token expirou (logout + login novamente)
- "Falha ao atualizar snapshot" → verificar API logs

---

## 🎯 Teste 3: Explorar Ativos (3 min)

### 📍 Local

Seção "Explorar" (abaixo de Watchlist)

### ✅ Esperado

- 4 abas: "Top BR", "Top US", "Top JP", "Top Crypto"
- Cada uma com ativos e preços
- Formato: `Nome SÍMBOLO • EXCHANGE • MOEDA`

### 📊 Dados Esperados

**Top BR:**

- Petrobras PN (PETR4) • B3 • BRL → ~48 BRL
- Vale ON (VALE3) • B3 • BRL → ~79 BRL
- Itaú Unibanco (ITUB4) • B3 • BRL → ~42 BRL
- WEG ON (WEGE3) • B3 • BRL → ~...
- Natura &Co (NTCO3) • B3 • BRL → ~...

**Top US:**

- Apple Inc. (AAPL) • NASDAQ • USD → preço USD × 5 = BRL
- Microsoft (MSFT) • NASDAQ • USD → ...
- Amazon (AMZN) • NASDAQ • USD → ...
- Alphabet (GOOGL) • NASDAQ • USD → ...
- Tesla (TSLA) • NASDAQ • USD → ...

**Top JP:**

- Toyota Motor (7203) • TSE • JPY → preço JPY × 0.033 = BRL
- Sony Group (6758) • TSE • JPY → ...
- Honda (7267) • TSE • JPY → ...

**Top Crypto:**

- Bitcoin (BTC) • CRYPTO • USD → 69000 USD × 5 = 345000 BRL
- Ethereum (ETH) • CRYPTO • USD → 3600 USD × 5 = 18000 BRL
- Solana (SOL) • CRYPTO • USD → 189 USD × 5 = 945 BRL
- Cardano (ADA) • CRYPTO • USD → 1.12 USD × 5 = 5.60 BRL

### 🔧 Ações

1. Scroll por cada seção
2. Verificar se preços aparecem
3. Clicar "Ver ativo" em um asset

### ✅ Resultado

- "Ver ativo" clicável
- Ativo aparece em "Últimos ativos vistos"

---

## 🎯 Teste 4: Language Toggle (1 min)

### 📍 Local

Seção "Configurações" → Seletor de idioma

### 🔧 Ação

1. Mudar de "Português (Brasil)" para "English"
2. Verificar mudanças
3. Voltar para português

### ✅ Resultado Esperado

| Português                                   | English                                       |
| ------------------------------------------- | --------------------------------------------- |
| Invest Explorer                             | Invest Explorer                               |
| Explorador de investimentos com base em BRL | Investment explorer with BRL as base currency |
| Configurações                               | Settings                                      |
| Explorar                                    | Explore                                       |
| Atualizar agora                             | Refresh now                                   |
| Entrar anonimamente                         | Sign in anonymously                           |
| Sessão Supabase ativa                       | Supabase session is active                    |
| Você está offline                           | You are offline                               |

---

## 🎯 Teste 5: Modo Offline (3 min)

### 📍 Como ativar offline

**Opção A: Chrome DevTools**

1. Abrir DevTools (F12)
2. Network tab
3. Throttling dropdown → "Offline"
4. Recarregar página (Ctrl+R)

**Opção B: Web API (console)**

```javascript
// No console do DevTools:
window.dispatchEvent(new Event("offline"));
// Recarregar página
```

### ✅ Resultado Esperado Offline

- ✓ Banner amarelo aparece: "Você está offline..."
- ✓ Todos dados continuam visíveis (do cache)
- ✓ "Atualizar agora" está DESABILITADO (cinza)
- ✓ "Entrar anonimamente" está DESABILITADO (cinza)
- ✓ "Ver ativo" botões estão DESABILITADOS (cinza)
- ✓ Seletor de idioma está DESABILITADO (cinza)
- ✓ Mensagem: "Modo somente leitura ativo (offline). Edições desabilitadas."

### ✅ Resultado Esperado Online Novamente

1. DevTools > Throttling → "Online" (ou remover offline)
2. Recarregar página
3. Banner desaparece
4. Todos botões HABILITADOS novamente

---

## 🎯 Teste 6: Últimos Ativos Vistos (1 min)

### 📍 Local

Seção "Últimos ativos vistos"

### 🔧 Ação

1. Clicar "Ver ativo" em 3-4 ativos diferentes
2. Voltar para o topo
3. Verificar seção "Últimos ativos vistos"

### ✅ Resultado

- Ativos aparecem na ordem inversa (mais recentes primeiro)
- Máximo 12 ativos armazenados
- Formato: `Nome SÍMBOLO • EXCHANGE • MOEDA`
- Persiste ao recarregar página (saved em IndexedDB)

---

## 📋 Checklist Final

```
ONLINE E AUTENTICADO:
□ Login anônimo funciona
□ Refresh retorna 20 ativos
□ Dados aparecem em 4 seções
□ Language toggle funciona
□ Últimos ativos vistos popula

OFFLINE:
□ Banner amarelo aparece
□ Dados permanecem visíveis
□ Botões desabilitados
□ Modo somente leitura ativo
□ Cache persiste após reload

ONLINE NOVAMENTE:
□ Banner desaparece
□ Botões ficam habilitados
□ Pode fazer refresh novamente
□ IndexedDB atualiza
```

---

## 🚨 Troubleshooting

| Problema                       | Solução                                 |
| ------------------------------ | --------------------------------------- |
| "Falha ao carregar watchlist"  | Normal em dev (vazio mesmo)             |
| Preços não aparecem            | Verificar API /health; aguarde 10s      |
| Offline não detecta            | Recarregar página após ativar offline   |
| Cache vazio offline            | Fazer refresh online primeiro           |
| Botões não desabilitam offline | Limpar cache (DevTools > clear storage) |

---

## ✅ Teste Passou!

Se todos os testes acima funcionarem, **MVP v1 está pronto para deploy**.

Próximo passo: Deploy em **Render** (API) + **Cloudflare Pages** (Web)
