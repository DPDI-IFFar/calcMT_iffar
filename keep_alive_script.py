from playwright.sync_api import sync_playwright
import time


def run():
    with sync_playwright() as p:
        # Abre o navegador (modo headless para rodar no GitHub)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Acessando o app...")
        page.goto("https://iffarcalcmatriculatotal.streamlit.app/")

        # Espera o app carregar (Streamlit demora uns segundos)
        page.wait_for_timeout(15000)

        page.screenshot(path="screenshot.png")
        print("App acessado com sucesso!")

        browser.close()


if __name__ == "__main__":
    run()
