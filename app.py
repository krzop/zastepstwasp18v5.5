import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from streamlit_autorefresh import st_autorefresh

# --- KONFIGURACJA ---
st.set_page_config(page_title="Monitor SP18 v5.7", page_icon="🏫")

# 1. Licznik odświeżania (2 minuty = 120 000 ms)
# Ten komponent zmusi Streamlit do przeładowania strony co 2 minuty
count = st_autorefresh(interval=120000, key="fscounter")

# 2. Inicjalizacja pamięci
if 'last_data' not in st.session_state:
    st.session_state.last_data = ""

st.title("🏫 Monitor SP18 v5.7 - Smart Refresh")

target_name = st.text_input("Nauczyciel:", "Pielok-Opara")
st.caption(f"Status: Czuwanie aktywne. Odświeżenie nr: {count}")

def get_substitutions(name):
    url = "https://sp18.chorzow.pl/substitution/"
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(25)
        driver.get(url)
        wait = WebDriverWait(driver, 15)
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Informacje dla nauczycieli')]")))
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(4)
        except:
            pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        sections = soup.find_all("div", class_="section print-nobreak")
        entries = []
        for sec in sections:
            header = sec.find("div", class_="header")
            if header and name.lower() in header.get_text().lower():
                rows = sec.find_all("div", class_="row")
                for r in rows:
                    p = r.find("div", class_="period")
                    i = r.find("div", class_="info")
                    if p and i:
                        entries.append((p.get_text(strip=True), i.get_text(strip=True)))
        
        if entries:
            entries.sort(key=lambda x: (int(''.join(filter(str.isdigit, x[0]))), 0 if "(" in x[0] else 1))
        return entries
    except Exception as e:
        return f"Błąd: {str(e)}"
    finally:
        if driver:
            driver.quit()

# --- LOGIKA WYKONANIA ---
with st.spinner('Sprawdzam stronę szkoły...'):
    results = get_substitutions(target_name)
    current_data_str = str(results)
    speech_text = ""

    # Sprawdzamy czy dane różnią się od zapamiętanych
    if current_data_str != st.session_state.last_data:
        st.session_state.last_data = current_data_str
        
        if isinstance(results, list):
            if results:
                st.warning(f"🔔 AKTUALIZACJA: {target_name}")
                for p, i in results:
                    with st.expander(f"Lekcja {p}", expanded=True):
                        st.write(f"Opis: {i.replace('➔', '➡️')}")
                    speech_text += f"Lekcja {p}. " + i.replace(":", " klasa ", 1).replace("➔", " zamiana na ") + ". "
            else:
                st.success(f"✅ Brak zastępstw dla: {target_name}")
                speech_text = "Brak nowych zastępstw."
        
        # Mówimy tylko przy starcie lub gdy dane się zmieniły
        if speech_text:
            js_speech = f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{speech_text.replace('"', '').replace("'", "")}");
                msg.lang = 'pl-PL'; msg.rate = 0.9;
                window.speechSynthesis.speak(msg);
                </script>
            """
            st.components.v1.html(js_speech, height=0)
    else:
        # Brak zmian - wyświetlamy po cichu
        if isinstance(results, list) and results:
            st.info("ℹ️ Plan bez zmian.")
            for p, i in results:
                with st.expander(f"Lekcja {p}", expanded=False):
                    st.write(i)
        else:
            st.success("✅ Brak zastępstw. Czekam na zmiany...")

st.divider()
st.caption(f"v5.7 | Ostatni skan: {time.strftime('%H:%M:%S')}")
