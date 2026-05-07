import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# PRÓBA IMPORTU LICZNIKA (z zabezpieczeniem)
try:
    from streamlit_autorefresh import st_autorefresh
    refresh_available = True
except ImportError:
    refresh_available = False

# --- KONFIGURACJA ---
st.set_page_config(page_title="Monitor SP18 v5.7.1", page_icon="🏫")

# 1. Mechanizm odświeżania (2 minuty)
if refresh_available:
    count = st_autorefresh(interval=120000, key="monitor_counter")
else:
    st.error("⚠️ Brak biblioteki 'streamlit-autorefresh' w requirements.txt!")
    count = 0

# 2. Inicjalizacja pamięci
if 'last_data' not in st.session_state:
    st.session_state.last_data = ""

st.title("🏫 Monitor SP18 v5.7.1")
target_name = st.text_input("Nauczyciel:", "Pielok-Opara")
st.caption(f"🔄 Cykl odświeżania nr: {count} | Następny skan za ok. 2 min")

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
            # Kliknięcie przycisku na stronie szkoły
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

# --- LOGIKA WYKONANIA (Zawsze przy starcie i odświeżeniu) ---
with st.spinner('Pobieranie aktualnych danych...'):
    results = get_substitutions(target_name)
    current_data_str = str(results)
    speech_text = ""

    # Logika Audio: Mów tylko jeśli dane są nowe
    if current_data_str != st.session_state.last_data:
        st.session_state.last_data = current_data_str
        
        if isinstance(results, list):
            if results:
                st.warning(f"🔔 NOWE ZMIANY dla: {target_name}")
                for p, i in results:
                    with st.expander(f"Lekcja {p}", expanded=True):
                        st.write(f"Opis: {i.replace('➔', '➡️')}")
                    speech_text += f"Lekcja {p}. " + i.replace(":", " klasa ", 1).replace("➔", " zamiana na ") + ". "
            else:
                st.success(f"✅ Brak zastępstw dla: {target_name}")
                speech_text = "Brak nowych zastępstw."
        
        if speech_text:
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{speech_text.replace('"', '').replace("'", "")}");
                msg.lang = 'pl-PL'; msg.rate = 0.9;
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)
    else:
        # Dane identyczne - wyświetlamy po cichu
        if isinstance(results, list) and results:
            st.info("ℹ️ Plan bez zmian (już odczytany).")
            for p, i in results:
                with st.expander(f"Lekcja {p}", expanded=False):
                    st.write(i)
        else:
            st.success("✅ Nadal brak zastępstw. Czuwam...")

if st.button("🔍 WYMUŚ SPRAWDZENIE TERAZ"):
    st.rerun()

st.divider()
st.caption(f"v5.7.1 | Ostatnia aktualizacja: {time.strftime('%H:%M:%S')}")
