#!/usr/bin/env python3
"""
Teste de modo offline: simula perda de conexão e verifica cache.
"""
import time

def print_section(title):
print("\n" + "=" _ 60)
print(f" {title}")
print("=" _ 60)

print_section("🔌 TESTE DE MODO OFFLINE")

print("""
Este teste valida que o modo offline funciona corretamente.

📋 MANUAL TEST STEPS (abrir DevTools no navegador):

1️⃣ PREPARAR OFFLINE
□ Abrir http://localhost:3000
□ DevTools > Network tab
□ Abrir devtools (F12 ou Ctrl+Shift+I)

2️⃣ CARREGAR DADOS ONLINE
□ Clicar "Entrar anonimamente" em Settings
□ Clicar "Atualizar agora"
□ Esperar dados aparecerem em Explorar > Top BR/US/JP/Crypto
□ Clicar em alguns ativos para preencher "Últimos Ativos Vistos"

3️⃣ ATIVAR OFFLINE
□ DevTools > Network tab > Selecionar dropdown "Throttling"
□ Selecionar "Offline" (ou ir em Settings > offline)
□ RECARREGAR página (Ctrl+R)

4️⃣ VERIFICAR CACHE
✅ Esperado:
[✓] Banner amarelo "Você está offline" aparece
[✓] Todos os dados permanecem visíveis (do cache)
[✓] Timestamp do snapshot não muda
[✓] "Últimos ativos vistos" continuam lá
[✓] Watchlist vazia permanece vazia
[✓] Botão "Atualizar agora" está DESABILITADO
[✓] Seletor de idioma está DESABILITADO
[✓] Botão "Entrar anonimamente" está DESABILITADO

❌ Se não funcionar:
[✗] Dados desaparecem → IndexedDB não salvou
[✗] Botões ainda clicáveis → readOnlyMode não aplicado
[✗] Banner não aparece → isOffline não detectado

5️⃣ TENTAR AÇÃO OFFLINE (deve fazer nada)
□ Clicar "Atualizar agora" → nada acontece (desabilitado)
□ Clicar "Ver ativo" → nada acontece (desabilitado)
□ Mudar idioma → nada acontece (select desabilitado)

6️⃣ VOLTAR ONLINE
□ DevTools > Network > Selecionar "Online"
□ RECARREGAR página (Ctrl+R)

✅ Esperado:
[✓] Banner desaparece
[✓] Botões ficam HABILITADOS
[✓] Dados ainda estão lá (cache)
[✓] Pode clicar "Atualizar agora" novamente

7️⃣ TESTAR SINCRONIZAÇÃO
□ Online novamente
□ Clicar "Atualizar agora"
□ Novos dados devem aparecer (ou os mesmos se prices não mudaram)
□ Timestamp deve atualizar

---

✅ TESTE PASSOU SE:
• Cache persiste offline
• UI muda para read-only
• Todos botões são desabilitados
• Banner aparece/desaparece corretamente
• Sincroniza quando volta online

📊 CACHE ARMAZENADO NO IndexedDB:
• last_snapshot: snapshot com 20 ativos
• last_watchlist: array de itens (vazio por enquanto)
• last_viewed_assets: ativos clicados

🔍 COMO INSPECIONAR CACHE (Chrome DevTools):
□ DevTools > Application > Storage > IndexedDB
□ invest-explorer-db > kv > Items
□ Ver: last_snapshot, last_watchlist, last_viewed_assets
""")

print_section("⚡ CHECKLIST RÁPIDO")
print("""
ANTES DO TESTE:
□ API rodando em http://localhost:8000/health → 200 OK
□ Web rodando em http://localhost:3000 → 200 OK
□ test_integration.py passou ✓

DURANTE OFFLINE:
□ Banner amarelo visível
□ Dados permanecem
□ Botões desabilitados
□ LocalStorage/IndexedDB funciona

APÓS VOLTA ONLINE:
□ Banner desaparece
□ Botões habilitados
□ Sincroniza com API

---

Próximo: Deploy MVP em Render + Cloudflare Pages
""")
