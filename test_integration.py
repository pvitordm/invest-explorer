#!/usr/bin/env python3
"""
Teste de integração local: simula login anônimo Supabase + refresh via API.
"""
import urllib.request
import json
import sys

def test_flow():
    print("=" * 60)
    print("TESTE DE INTEGRAÇÃO: Web + API com Login Anônimo")
    print("=" * 60)
    
    # Simulamos um token JWT anônimo do Supabase
    # (Em prod, viria do supabase.auth.signInAnonymously())
    test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImludmVzdC1leHBsb3JlciIsInJvbGUiOiJhdXRoZW50aWNhdGVkIiwidXNlcl9pZCI6ImRldjAwMSJ9.test_token"
    
    # Passo 1: Testar /health (deve trabalhar sem token)
    print("\n✓ Passo 1: Verificar saúde da API")
    try:
        req = urllib.request.Request('http://localhost:8000/health')
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        print(f"  Status: {data['status']}")
        print(f"  Serviço: {data['service']}")
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False
    
    # Passo 2: Testar /refresh com token (simula login anônimo)
    print("\n✓ Passo 2: Chamar /refresh com token de login anônimo")
    try:
        req = urllib.request.Request(
            'http://localhost:8000/refresh',
            data=b'{}',
            headers={
                'Authorization': f'Bearer {test_token}',
                'Content-Type': 'application/json'
            },
            method='POST'
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        
        print(f"  Status: {data['status']}")
        print(f"  Message: {data['message']}")
        print(f"  Assets ao vivo: {data['live_asset_count']}")
        print(f"  Fallback assets: {data['fallback_asset_count']}")
        print(f"  Total: {data['snapshot_asset_count']}")
        print(f"  Usuário detectado: {data['requested_by']}")
        
        # Exibir alguns ativos
        if data.get('data') and data['data'].get('assets'):
            print(f"\n  Primeiros 3 ativos:")
            for asset in data['data']['assets'][:3]:
                print(f"    - {asset['name']} ({asset['symbol']}) @ BRL {asset['valuation_brl']}")
        
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False
    
    # Passo 3: Testar /watchlist com token
    print("\n✓ Passo 3: Chamar /watchlist com token anônimo")
    try:
        req = urllib.request.Request(
            'http://localhost:8000/watchlist',
            headers={
                'Authorization': f'Bearer {test_token}',
                'Content-Type': 'application/json'
            },
            method='GET'
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        
        print(f"  Watchlist: {data['watchlist']['name']}")
        print(f"  Items: {len(data['items'])}")
        print(f"  Owner: {data['owner']}")
        
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ TESTE COMPLETO: Web + API integrando corretamente!")
    print("=" * 60)
    print("\nPróximos passos:")
    print("1. Acessar http://localhost:3000 no navegador")
    print("2. Clicar em 'Entrar anonimamente' em Settings")
    print("3. Clicar em 'Atualizar agora'")
    print("4. Verificar se snapshot aparece em Explore sections")
    return True

if __name__ == '__main__':
    success = test_flow()
    sys.exit(0 if success else 1)
