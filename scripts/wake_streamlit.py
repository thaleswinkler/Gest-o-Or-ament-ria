import sys
import time
from datetime import datetime

def log(msg: str):
    print(f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}] {msg}")

def main():
    url = (sys.argv[1] if len(sys.argv) > 1 else "https://gestaoorcamentaria.streamlit.app").strip()
    log(f"🚀 Iniciando verificação de Keep-Alive no Streamlit: {url}")
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("❌ Playwright não instalado. Instale com: pip install playwright && playwright install chromium")
        sys.exit(1)
        
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        log("🌐 Acessando a página do aplicativo...")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            log(f"⚠️ Aviso no carregamento inicial: {e}")
            
        # Aguarda alguns segundos para renderização do React/WebSocket
        page.wait_for_timeout(6000)
        
        # Procura pelo botão oficial de despertar do Streamlit Cloud
        # Frases comuns: "Yes, get this app back up!", "Get this app back up!", "Wake up"
        sleep_selectors = [
            'button:has-text("back up")',
            'button:has-text("get this app back up")',
            'button:has-text("wake", { timeout: 1000 })',
            'button:has-text("Yes")',
            '[data-testid="stAppSleeping"] button'
        ]
        
        acordou = False
        for sel in sleep_selectors:
            try:
                locator = page.locator(sel)
                if locator.count() > 0 and locator.first.is_visible():
                    texto_btn = locator.first.inner_text()
                    log(f"😴 App detectado em modo de suspensão! Botão encontrado: '{texto_btn}'")
                    log("👉 Clicando no botão para acordar a aplicação...")
                    locator.first.click()
                    acordou = True
                    break
            except Exception:
                continue
                
        if acordou:
            log("⏳ Aguardando 20 segundos enquanto o Streamlit inicializa o contêiner...")
            page.wait_for_timeout(20000)
        else:
            log("✅ O aplicativo já está acordado ou carregou a interface diretamente.")
            
        log(f"📄 Título atual da página: '{page.title()}'")
        browser.close()
        log("🎉 Rotina concluída com sucesso! Contêiner do Streamlit mantido aquecido.")

if __name__ == "__main__":
    main()
