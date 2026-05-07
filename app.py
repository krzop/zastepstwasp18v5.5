import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Monitor SP18 v5.8.1", page_icon="🏫", layout="centered")

if 'last_data' not in st.session_state:
    st.session_state.last_data = "START"

st.title("🏫 Monitor SP18 v5.8.1")

# --- INTERFEJS ---
target_name = st.text_input("Nauczyciel:", "Pielok-Opara")

# WAŻNE: Przycisk, który odblokowuje Audio w przeglądarce
if st.button("🔊 AKTYWUJ GŁOS I SPRAWDŹ"):
    st.session_state.activated = True

def get_substitutions(name):
    url = "https://sp18.chorzow.pl/substitution/"
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        wait = WebDriverWait(driver, 15)
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Informacje dla nauczycieli')]")))
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(4)
        except: pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        sections = soup.find_all("div", class_="section print-nobreak")
        raw_entries = []
        for sec in sections:
            header = sec.find("div", class_="header")
            if header and name.lower() in header.get_text().lower():
                rows = sec.find_all("div", class_="row")
                for r in rows:
                    p = r.find("div", class_="period"); i = r.find("div", class_="info")
                    if p and i: raw_entries.append((p.get_text(strip=True), i.get_text(strip=True)))
        
        if raw_entries:
            raw_entries.sort(key=lambda x: (int(''.join(filter(str.isdigit, x[0]))), 0 if "(" in x[0] else 1))
        return raw_entries
    except Exception as e: return f"Błąd: {str(e)}"
    finally:
        if driver: driver.quit()

# --- LOGIKA ---
with st.spinner('Pobieranie danych...'):
    results = get_substitutions(target_name)
    current_data_str = str(results)
    full_speech_text = ""

    should_speak = False
    if current_data_str != st.session_state.last_data:
        should_speak = True
        st.session_state.last_data = current_data_str

    if isinstance(results, list):
        if results:
            st.warning(f"🔔 Zmiany dla: {target_name}")
            for p, i in results:
                with st.expander(f"Lekcja {p}", expanded=True):
                    st.write(f"Opis: {i.replace('➔', '➡️')}")
                if should_speak:
                    full_speech_text += f"Lekcja {p}. " + i.replace(":", " klasa ", 1).replace("➔", " zamiana na ") + ". "
        else:
            st.success(f"✅ Brak zastępstw dla: {target_name}")
            if should_speak:
                full_speech_text = f"Dla nazwiska {target_name} brak nowych zastępstw."

    # --- POPRAWIONY SKRYPT AUDIO ---
    if should_speak and full_speech_text:
        js_text = full_speech_text.replace('"', '').replace("'", "")
        st.components.v1.html(f"""
            <script>
            function speak() {{
                window.speechSynthesis.cancel();
                var msg = new SpeechSynthesisUtterance("{js_text}");
                msg.lang = 'pl-PL';
                msg.rate = 0.9;
                msg.volume = 1.0;
                window.speechSynthesis.speak(msg);
            }}
            // Próba natychmiastowa i opóźniona dla pewności
            speak();
            setTimeout(speak, 1000);
            </script>
        """, height=0)

# --- AUTO-REFRESH ---
st.components.v1.html("""
<script>
    setTimeout(function(){ window.parent.location.reload(); }, 120000);
</script>
""", height=0)

st.divider()
st.caption(f"v5.8.1 | Ostatni skan: {time.strftime('%H:%M:%S')}")
