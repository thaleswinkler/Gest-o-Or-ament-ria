import os
import sys
import json
from datetime import datetime
from supabase import create_client, Client

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando backup do banco de dados...")
    
    url = os.environ.get("SUPABASE_URL") or "https://oxneqoegehufjksvupji.supabase.co"
    key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or "sb_publishable_norqoENXSTwzga1rD-vU2A_NDIH7KeX"
    
    if not url or not key:
        print("ERRO: SUPABASE_URL e/ou SUPABASE_KEY não configurados.")
        sys.exit(1)
        
    try:
        supabase: Client = create_client(url, key)
        
        # 1. Extração da tabela de Usuários (sem as senhas para segurança do backup)
        resp_usuarios = supabase.table("usuarios").select("id, nome, om, secao, perfil").execute()
        usuarios_data = resp_usuarios.data
        print(f"-> Tabela 'usuarios': {len(usuarios_data)} registros exportados.")
        
        # 2. Extração da tabela de Dados (NCs, itens, configurações de requisição)
        resp_dados = supabase.table("dados").select("*").execute()
        dados_data = resp_dados.data
        print(f"-> Tabela 'dados': {len(dados_data)} seções/registros exportados.")
        
        backup_conteudo = {
            "metadata": {
                "timestamp": timestamp,
                "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "versao_sistema": "1.0",
                "total_usuarios": len(usuarios_data),
                "total_secoes": len(dados_data)
            },
            "tabelas": {
                "usuarios": usuarios_data,
                "dados": dados_data
            }
        }
        
        # Cria o diretório de backups se não existir
        os.makedirs("backups", exist_ok=True)
        nome_arquivo = f"backups/backup_{timestamp}.json"
        
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            json.dump(backup_conteudo, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Backup concluído e gravado em '{nome_arquivo}' com sucesso!")
        
        # Mantém apenas os últimos 10 backups para não inchar o repositório
        arquivos = sorted([os.path.join("backups", f) for f in os.listdir("backups") if f.endswith(".json")])
        if len(arquivos) > 10:
            para_remover = arquivos[:-10]
            for arq in para_remover:
                try:
                    os.remove(arq)
                    print(f"Rotatividade: Backup antigo '{arq}' removido para economizar espaço.")
                except Exception as err:
                    print(f"Aviso ao remover {arq}: {err}")
                    
    except Exception as e:
        print(f"ERRO durante o backup do Supabase: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
