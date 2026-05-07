import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# --- KONFIGURACJA ---
st.set_page_config(page_title="Monitor SP18 v5.7.3", page_icon="🏫")

# Pamięć sesji
if 'last_data' not in st.session_state:
    st.session_state.last_data = "START"

st.title("🏫 Monitor SP18 v5.7.3")
target_name = st.text_input("Nauczyciel:", "Pielok-Opara")

def get_substitutions(name):
    url = "https://sp18.chorzow.pl/substitution/"
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080") # Dodane dla stabilności klikania
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        driver.get(url)
        
        # Czekamy na załadowanie strony
        time.sleep(2) 
        
        # KLUCZOWY MOMENT: Próba kliknięcia przycisku
        try:
            wait = WebDriverWait(driver, 15)
            # Szukamy przycisku po tekście wewnątrz linku
            btn = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Informacje dla nauczycieli")))
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(5) # Dajemy 5 sekund na przeładowanie tabeli (ważne!)
        except Exception as e:
            # Jeśli nie znajdzie przycisku, spróbujemy pobrać to co jest (może już widoczne)
            pass

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        sections = soup.find_all("div", class_="section print-nobreak")
        
        raw_entries = []
        target_lower = name.lower()
        
        for sec in sections:
            header = sec.find("div", class_="header")
            if header and target_lower in header.get_text().lower():
                rows = sec.find_all("div", class_="row")
                for r in rows:
                    p = r.find("div", class_="period")
                    i = r.find("div", class_="info")
                    if p and i:
                        raw_entries.append((p.get_text(strip=True), i.get_text(strip=True)))
        
        if raw_entries:
            raw_entries.sort(key=lambda x: (int(''.join(filter(str.isdigit, x[0]))), 0 if "(" in x[0] else 1))
        
        return raw_entries
    except Exception as e:
        return f"Błąd: {str(e)}"
    finally:
        if driver:
            driver.quit()

# --- LOGIKA WYKONANIA ---
with st.spinner('Pobieram dane (silnik v5.4)...'):
    results = get_substitutions(target_name)
    current_data_str = str(results)
    speech_text = ""

    # Zawsze wyświetlaj to, co pobrano
    if isinstance(results, list):
        if results:
            st.warning(f"🔔 Znaleziono zmiany dla: {target_name}")
            for p, i in results:
                with st.expander(f"Lekcja {p}", expanded=True):
                    st.write(f"**Opis:** {i.replace('➔', ' ➡️ ')}")
                if current_data_str != st.session_state.last_data:
                    speech_text += f"Lekcja {p}. " + i.replace(":", " klasa ", 1).replace("➔", " zamiana na ") + ". "
        else:
            st.success(f"✅ Brak zastępstw dla: {target_name}")
            if current_data_str != st.session_state.last_data:
                speech_text = f"Dla nazwiska {target_name} brak nowych zastępstw."

    # Obsługa mowy (tylko gdy dane są nowe)
    if speech_text:
        st.session_state.last_data = current_data_str
        js_code = f"""
            <script>
            window.speechSynthesis.cancel();
            var msg = new SpeechSynthesisUtterance("{speech_text.replace('"', '').replace("'", "")}");
            msg.lang = 'pl-PL'; msg.rate = 0.9;
            window.speechSynthesis.speak(msg);
            </script>
        """
        st.components.v1.html(js_code, height=0)

# --- AUTO-ODŚWIEŻANIE (2 MINUTY) ---
st.components.v1.html("""
    <script>
    setTimeout(function(){ window.parent.location.reload(); }, 120000);
    </script>
""", height=0)

st.divider()
st.caption(f"v5.7.3 Stable Engine | {time.strftime('%H:%M:%S')}")
