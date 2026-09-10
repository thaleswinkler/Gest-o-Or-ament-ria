import os
import sys
import json
from datetime import datetime
from supabase import create_client, Client

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando backup do banco de dados...")
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("ERRO: SUPABASE_URL e/ou SUPABASE_KEY não configurados.")
        sys.exit(1)
        
    try:
        supabase: Client = create_client(url, key)
        
        # 1. Usuários (sem as senhas para proteger os militares)
        resp_usuarios = supabase.table("usuarios").select("id, nome, om, secao, perfil").execute()
        usuarios_data = resp_usuarios.data
        print(f"-> Tabela 'usuarios': {len(usuarios_data)} registros exportados.")
        
        # 2. Dados das NCs, Itens e Timbre
        resp_dados = supabase.table("dados").select("*").execute()
        dados_data = resp_dados.data
        print(f"-> Tabela 'dados': {len(dados_data)} seções exportadas.")
        
        backup_conteudo = {
            "metadata": {
                "timestamp": timestamp,
                "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "total_usuarios": len(usuarios_data),
                "total_secoes": len(dados_data)
            },
            "tabelas": {
                "usuarios": usuarios_data,
                "dados": dados_data
            }
        }
        
        os.makedirs("backups", exist_ok=True)
        nome_arquivo = f"backups/backup_{timestamp}.json"
        
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            json.dump(backup_conteudo, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Backup concluído em '{nome_arquivo}'!")
        
        # Mantém apenas os últimos 10 backups para não lotar o repositório
        arquivos = sorted([os.path.join("backups", f) for f in os.listdir("backups") if f.endswith(".json")])
        if len(arquivos) > 10:
            for arq in arquivos[:-10]:
                os.remove(arq)
                print(f"Backup antigo '{arq}' removido da rotação.")
                
    except Exception as e:
        print(f"ERRO durante o backup: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
