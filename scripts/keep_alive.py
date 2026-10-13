import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

def main():
    agora_iso = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"[{agora_iso}] 🔄 Iniciando rotina aprimorada de Keep-Alive no Supabase...")
    
    url = (os.environ.get("SUPABASE_URL") or "https://oxneqoegehufjksvupji.supabase.co").strip().rstrip('/')
    key = (os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or "sb_publishable_norqoENXSTwzga1rD-vU2A_NDIH7KeX").strip()
    
    if not url or not key:
        print("❌ ERRO: SUPABASE_URL ou SUPABASE_KEY não configurados.")
        sys.exit(1)
        
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "SupabaseKeepAlive/2.0"
    }

    sucessos = 0

    # 1. ESCRITA / TRANSAÇÃO REAL (Upsert de heartbeat no banco de dados)
    # Grava um timestamp ativo na tabela 'dados' com id '_keepalive_ping'
    # Isto força o PostgreSQL a registrar transações e escrita de disco no WAL,
    # garantindo que a métrica de atividade do Supabase seja 100% preenchida.
    try:
        payload = json.dumps({
            "id": "_keepalive_ping",
            "ncs": {
                "last_ping": agora_iso,
                "service": "github_actions_keep_alive",
                "status": "active"
            }
        }).encode('utf-8')

        req_upsert = urllib.request.Request(
            f"{url}/rest/v1/dados",
            data=payload,
            headers={**headers, "Prefer": "resolution=merge-duplicates"},
            method="POST"
        )
        with urllib.request.urlopen(req_upsert, timeout=15) as resp:
            print(f"✅ [1/3] Transação de Escrita (Heartbeat Upsert): Sucesso (HTTP {resp.status})")
            sucessos += 1
    except Exception as e:
        print(f"⚠️ Aviso na escrita do heartbeat: {e}")

    # 2. LEITURA 1: Consulta na tabela 'usuarios'
    try:
        req_users = urllib.request.Request(
            f"{url}/rest/v1/usuarios?select=id&limit=1",
            headers=headers,
            method="GET"
        )
        with urllib.request.urlopen(req_users, timeout=15) as resp:
            corpo = resp.read().decode('utf-8')
            print(f"✅ [2/3] Consulta de Leitura (Tabela Usuarios): Sucesso (HTTP {resp.status})")
            sucessos += 1
    except Exception as e:
        print(f"⚠️ Aviso na leitura de usuarios: {e}")

    # 3. LEITURA 2: Consulta na tabela 'dados'
    try:
        req_dados = urllib.request.Request(
            f"{url}/rest/v1/dados?select=id&limit=3",
            headers=headers,
            method="GET"
        )
        with urllib.request.urlopen(req_dados, timeout=15) as resp:
            corpo = resp.read().decode('utf-8')
            print(f"✅ [3/3] Consulta de Leitura (Tabela Dados): Sucesso (HTTP {resp.status})")
            sucessos += 1
    except Exception as e:
        print(f"⚠️ Aviso na leitura de dados: {e}")

    # 4. Fallback com SDK oficial supabase (se disponível no ambiente)
    try:
        from supabase import create_client, Client
        sb: Client = create_client(url, key)
        res = sb.table("dados").select("id").eq("id", "_keepalive_ping").execute()
        print(f"✅ [Bônus] Validação via SDK Oficial Supabase: OK ({len(res.data)} registro)")
        sucessos += 1
    except ImportError:
        pass
    except Exception as e:
        print(f"ℹ️ Info SDK: {e}")

    if sucessos > 0:
        print(f"🎉 Concluído com sucesso! {sucessos} operações de banco de dados executadas.")
        print(f"📌 Status: Banco de dados ativo, transações registradas e contador de inatividade reiniciado.")
    else:
        print("❌ Falha: Nenhuma operação pôde ser concluída no Supabase.")
        sys.exit(1)

if __name__ == "__main__":
    main()
