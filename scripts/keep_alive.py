import os
import sys
from datetime import datetime
from supabase import create_client, Client

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando rotina Keep-Alive no Supabase...")
    
    url = os.environ.get("SUPABASE_URL") or "https://oxneqoegehufjksvupji.supabase.co"
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or "sb_publishable_norqoENXSTwzga1rD-vU2A_NDIH7KeX"
    
    if not url or not key:
        print("ERRO: As variáveis de ambiente SUPABASE_URL e/ou SUPABASE_KEY não foram configuradas.")
        sys.exit(1)
        
    try:
        supabase: Client = create_client(url, key)
        
        # Executa uma consulta leve e rápida para movimentar a API e resetar o contador de inatividade de 7 dias
        resposta = supabase.table("usuarios").select("id").limit(1).execute()
        
        print("Sucesso! Conexão realizada com o banco de dados Supabase.")
        print(f"Registros verificados com sucesso: {len(resposta.data)}")
        print(f"Status: Banco de dados ativo e contador de inatividade reiniciado com sucesso.")
        
    except Exception as e:
        print(f"ERRO ao conectar com o Supabase: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
