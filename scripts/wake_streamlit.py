import sys
import time
from datetime import datetime

def log(msg: str):
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}] {msg}")

def main():
    url = (sys.argv[1] if len(sys.argv) > 1 else "https://gestaoorcamentaria.streamlit.app").strip()
    log(f"🚀 Iniciando verificação de Keep-Alive no Streamlit: {url}")
    
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    log("🌐 Abrindo navegador Chrome Headless nativo...")
    driver = webdriver.Chrome(options=options)
    
    try:
        log("🔗 Navegando para o Streamlit...")
        driver.get(url)
        time.sleep(6)
        
        # Procura botões de acordar o Streamlit
        botoes = driver.find_elements(By.TAG_NAME, "button")
        acordou = False
        for btn in botoes:
            try:
                texto = btn.text.strip().lower()
                if any(palavra in texto for palavra in ["back up", "wake", "acordar", "yes, get this app back up"]):
                    log(f"😴 App em modo de suspensão detectado! Botão encontrado: '{btn.text}'")
                    log("👉 Clicando no botão para acordar o Streamlit...")
                    btn.click()
                    acordou = True
                    break
            except Exception:
                continue
                
        if acordou:
            log("⏳ Aguardando 15s para inicialização do contêiner...")
            time.sleep(15)
        else:
            log("✅ O aplicativo já está acordado ou carregou a interface diretamente.")
            
        log(f"📄 Título atual da página: '{driver.title}'")
        log("🎉 Rotina concluída com sucesso! Contêiner mantido ativo.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
