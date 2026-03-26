# 🧪 Guia de Teste Manual - Invest Explorer MVP

## Ambiente Local

API rodando em: http://localhost:8000
Web rodando em: http://localhost:3000

## Fluxo de Teste (5 minutos)

### 1. Login Anônimo
```
1. Abrir http://localhost:3000 no navegador
2. Scroll para "Configurações"
3. Clicar em "Entrar anonimamente" (botão azul)
4. Verificar se aparece "Sessão Supabase ativa" na tela
```

### 2. Atualizar Snapshot
```
1. Clicar em "Atualizar agora" (no topo)
2. Aguardar 5-10 segundos (está buscando preços ao vivo do yfinance)
3. Verificar se aparece mensagem de sucesso
4. Verificar se timestamp do snapshot muda
```

### 3. Visualizar Ativos
```
Explorar → Deve aparecer 4 seções:
- Top BR: Petrobras (PETR4), Vale (VALE3), etc
- Top US: Apple (AAPL), Microsoft (MSFT), etc
- Top JP: Toyota (7203), Sony (6758), etc
- Top Crypto: Bitcoin (BTC), Ethereum (ETH), etc

Cada ativo mostra:
- Nome SÍMBOLO • EXCHANGE • MOEDA
- Preço em moeda original
- Valuation em BRL
- Status: LIVE ou FALLBACK
```

### 4. Teste Offline (Opcional)
```
1. Desligar internet / Devtools > Network > Offline
2. Atualizar página
3. Verificar se aparece banner amarelo "Você está offline"
4. Verificar se dados em cache ainda aparecem
5. Tentar clicar "Atualizar agora" - deve estar desabilitado
```

### 5. Language Toggle
```
1. Em Configurações, mudar idioma para "English"
2. Verificar se todos os textos mudam para inglês
3. Voltar para "Português (Brasil)"
```

## O que esperar em cada aba

### Configurações
- Status da sessão (ativo/inativo)
- Seletor de idioma pt-BR/en
- Botão de login anônimo

### Últimos Ativos Vistos
- Lista vazia no início
- Popula conforme clica em "Ver ativo" nos ativos

### Watchlist
- Integrada com Supabase (vazio por enquanto em dev)
- Será preenchido após implementar edição

### Explorar
- 4 seções (Top BR/US/JP/Crypto)
- ~20 ativos com "Ver ativo" para cada um
- Preços em BRL com valuation

## Status Esperado (MVP v1)

✅ Funcional:
- Login anônimo Supabase
- Refresh de snapshot (20 ativos ao vivo via yfinance)
- Display de preços + valuation em BRL
- Language toggle pt-BR/en
- Offline banner + read-only mode

❌ Ainda não pronto:
- Supabase: salvar snapshots (usar fallback por enquanto)
- Watchlist: edição (only viewing structure)
- Portfolio: não implementado
- Scheduler: só refresh manual por agora

## Comandos Úteis

```powershell
# Terminal 1: API
cd "d:\invest-explorer\apps\api"
.venv\Scripts\Activate.ps1
uvicorn main:app --reload

# Terminal 2: Web
cd "d:\invest-explorer\apps\web"
npm run dev

# Terminal 3: Teste
python d:\invest-explorer\test_integration.py
```

## Troubleshooting

| Problema | Solução |
|----------|---------|
| "Falha ao carregar watchlist da API" | Normal em dev, API retorna vazio |
| Preços não atualizam | Verificar conexão internet / yfinance rate limits |
| Web mostra "Sem sessão ativa" | Clicar "Entrar anonimamente" primeiro |
| "Você está offline" mas tem internet | Devtools > Desabilitar "Offline" |

---

**Próximas etapas:** Deploy (Render + Cloudflare Pages) + Supabase integração real
