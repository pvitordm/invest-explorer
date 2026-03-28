# 🚀 Guia de Deploy MVP - Invest Explorer

> Deploy-ready na **Render** (API) + **Cloudflare Pages** (Web)  
> Tempo estimado: 30 minutos

---

## 📋 Pré-requisitos

✅ Repository público em GitHub (pvitordm/invest-explorer)
✅ API + Web testados localmente (test_integration.py passou)
✅ Supabase project criado (https://invest-explorer.supabase.co)
✅ Commits feitos e pusheados para main

---

## 🔧 PARTE 1: Deploy API no Render (5 min)

### 1.1 Criar serviço no Render

1. Ir para https://render.com
2. Sign in com GitHub (ou criar conta)
3. Dashboard → "New" → "Web Service"
4. Conectar GitHub: autorizar pvitordm/invest-explorer

### 1.2 Configurar serviço

| Campo              | Valor                                          |
| ------------------ | ---------------------------------------------- |
| **Repository**     | `pvitordm/invest-explorer`                     |
| **Root Directory** | `apps/api`                                     |
| **Runtime**        | `Python 3`                                     |
| **Build Command**  | `pip install -r requirements.txt`              |
| **Start Command**  | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Environment**    | Select `Python`                                |

### 1.3 Variáveis de Ambiente

No Render Dashboard, seção "Environment":

```env
SUPABASE_URL=https://invest-explorer.supabase.co
SUPABASE_ANON_KEY=<copiar de Supabase > Settings > API Keys > Anon Key>
SUPABASE_SERVICE_ROLE_KEY=<copiar de Supabase > Settings > API Keys > Service Role>
SUPABASE_JWT_SECRET=<copiar de Supabase > Settings > JWT Secret>
SUPABASE_JWT_AUDIENCE=authenticated
ALLOWED_ORIGINS=https://<seu-dominio-cloudflare-pages>.pages.dev,http://localhost:3000
```

> **Onde encontrar no Supabase:**
>
> 1. Ir para https://app.supabase.com
> 2. Selecionar projeto "invest-explorer"
> 3. Settings (⚙️) > API
> 4. Copiar os valores

### 1.4 Deploy

1. Clicar "Create Web Service"
2. Aguardar ~2-3 minutos (primeiro build)
3. Quando terminar, você terá URL como: `https://invest-explorer-api.onrender.com`

### ✅ Teste API

```bash
curl https://invest-explorer-api.onrender.com/health
```

Esperado:

```json
{ "status": "ok", "service": "invest-explorer-api" }
```

---

## 🌐 PARTE 2: Deploy Web no Cloudflare Pages (5 min)

### 2.1 Preparar repo para Cloudflare

Cloudflare Pages auto-detecta Next.js. Precisamos só configurar env vars.

### 2.2 Criar projeto Cloudflare Pages

1. Ir para https://dash.cloudflare.com/
2. Sign in com GitHub (ou criar conta)
3. Pages → "Create a project"
4. Conectar GitHub: autorizar pvitordm/invest-explorer

### 2.3 Configurar build

| Campo                      | Valor                                         |
| -------------------------- | --------------------------------------------- |
| **Framework**              | `Next.js`                                     |
| **Build command**          | `cd apps/web && npm install && npm run build` |
| **Build output directory** | `apps/web/.next/export`                       |
| **Root directory**         | `/` (raiz do monorepo)                        |

### 2.4 Variáveis de Ambiente

No Cloudflare Pages, seção "Environment variables":

```env
NEXT_PUBLIC_SUPABASE_URL=https://invest-explorer.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<mesmo valor do Render>
NEXT_PUBLIC_API_BASE_URL=https://invest-explorer-api.onrender.com
```

### 2.5 Deploy

1. Clicar "Save and Deploy"
2. Aguardar ~3-5 minutos (build + upload)
3. Quando terminar, você terá URL como: `https://invest-explorer-xxx.pages.dev`

### ✅ Teste Web

Abrir no navegador: `https://invest-explorer-xxx.pages.dev`

Esperado:

- Página carrega
- Pode clicar "Entrar anonimamente"
- Botão "Atualizar agora" funciona

---

## 🔄 PARTE 3: Configurar CORS (5 min)

### 3.1 Atualizar ALLOWED_ORIGINS no Render

Se o deploy web tem URL diferente, atualizar:

1. Ir para Render Dashboard
2. Seu serviço invest-explorer-api
3. Settings → Environment > ALLOWED_ORIGINS
4. Atualizar para: `https://<seu-dominio-cloudflare>.pages.dev`
5. Clicar "Save"

---

## 🎯 PARTE 4: Testes Pós-Deploy (5 min)

### 4.1 Teste de Saúde

```bash
# API
curl https://invest-explorer-api.onrender.com/health

# Web (abrir no navegador)
https://invest-explorer-xxx.pages.dev
```

### 4.2 Teste de Fluxo Completo

1. Abrir web em novo navegador/incógnito
2. Clicar "Entrar anonimamente"
3. Clicar "Atualizar agora"
4. Aguardar 5-10 segundos
5. Verificar se dados aparecem em Explorar

**Esperado:**

```
✓ Login anônimo Supabase
✓ 20 ativos carregados
✓ Preços em BRL aparecem
✓ Sem erros no console
```

### 4.3 Verificar Logs

**Render:**

```bash
# In Render Dashboard
Logs → procurar por erros
```

**Cloudflare Pages:**

```bash
# In Cloudflare Dashboard > Pages
Deployments → clicar no último
View logs → procurar por erros
```

---

## 🛠️ Troubleshooting

| Erro                 | Causa                         | Solução                    |
| -------------------- | ----------------------------- | -------------------------- |
| `502 Bad Gateway`    | Build falhou                  | Verificar Render logs      |
| `401 Unauthorized`   | Token Supabase inválido       | Verificar ALLOWED_ORIGINS  |
| "Cannot find module" | Dependências não instaladas   | Verify requirements.txt    |
| Web não carrega      | Cloudflare Pages build falhou | Verificar output directory |
| "Failed to fetch"    | CORS não configurado          | Atualizar ALLOWED_ORIGINS  |

---

## 📍 URLs Finais

Após deploy, você terá:

- **API:** `https://invest-explorer-api.onrender.com`
  - GET `/health` → verifica saúde
  - POST `/refresh` → atualiza snapshot

- **Web:** `https://invest-explorer-xxx.pages.dev`
  - Login anônimo Supabase
  - Refresh de dados
  - Offline read-only

---

## ✅ Checklist de Deploy

```
PRÉ-DEPLOY:
□ Commits pusheados para main
□ test_integration.py passou
□ API + Web funcionam localmente

RENDER (API):
□ Serviço criado
□ Build command correto
□ Environment vars setadas
□ /health retorna 200 OK

CLOUDFLARE PAGES (Web):
□ Projeto criado
□ Build command correto
□ Environment vars setadas
□ Página carrega sem 404

PRODUTO:
□ Login (Entrar anonimamente) funciona
□ Refresh retorna dados
□ Offline mode funciona
□ Sem erros 4xx/5xx
```

---

## 🚀 Deploy Concluído!

App está agora em produção:

- **Web:** `https://invest-explorer-xxx.pages.dev`
- **API:** `https://invest-explorer-api.onrender.com`

Próximos passos:

- Monitorar logs
- Testar em mobile
- Considerar custom domain
- Planejar scheduler 3x/dia para v1.1

---

## 📱 Teste em Mobile

A app é PWA (Progressive Web App). Em mobile:

1. Abrir URL da web (Chrome/Safari)
2. Menu (⋯) → "Install app" ou "Add to Home Screen"
3. App funciona mesmo offline

---

**Deploy MVP concluído! 🎉**
