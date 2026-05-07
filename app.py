import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Monitor SP18 v5.7.2", page_icon="🏫")

if 'last_data' not in st.session_state:
    st.session_state.last_data = "FIRST_RUN" # Wymuszenie czytania przy starcie

st.title("🏫 Monitor SP18 v5.7.2")
target_name = st.text_input("Nauczyciel:", "Pielok-Opara")

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
            # Szukanie przycisku nauczycieli
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

# --- GŁÓWNA LOGIKA (URUCHAMIANA ZAWSZE) ---
with st.spinner('Pobieram dane na start...'):
    results = get_substitutions(target_name)
    current_data_str = str(results)
    speech_text = ""

    # 1. Sprawdzanie czy dane są nowe lub czy to pierwszy start
    if current_data_str != st.session_state.last_data:
        st.session_state.last_data = current_data_str
        
        if isinstance(results, list):
            if results:
                st.warning(f"🔔 Znaleziono zmiany dla: {target_name}")
                for p, i in results:
                    with st.expander(f"Lekcja {p}", expanded=True):
                        st.write(f"Opis: {i.replace('➔', '➡️')}")
                    speech_text += f"Lekcja {p}. " + i.replace(":", " klasa ", 1).replace("➔", " zamiana na ") + ". "
            else:
                st.success(f"✅ Brak zastępstw dla: {target_name}")
                speech_text = f"Dla nazwiska {target_name} brak nowych zastępstw."
        
        # 2. WYWOŁANIE GŁOSU (Zawsze przy zmianie/starcie)
        if speech_text:
            js_code = f"""
                <script>
                window.speechSynthesis.cancel();
                var msg = new SpeechSynthesisUtterance("{speech_text.replace('"', '').replace("'", "")}");
                msg.lang = 'pl-PL';
                msg.rate = 0.9;
                window.speechSynthesis.speak(msg);
                </script>
            """
            st.components.v1.html(js_code, height=0)
    else:
        # DANE IDENTYCZNE - TYLKO WYŚWIETLANIE (CISZA)
        if isinstance(results, list) and results:
            st.info("ℹ️ Plan bez zmian.")
            for p, i in results:
                with st.expander(f"Lekcja {p}", expanded=False):
                    st.write(i)
        else:
            st.success("✅ Nadal brak zastępstw. Czekam...")

# --- AUTOMATYCZNE ODŚWIEŻANIE (Co 2 minuty) ---
st.components.v1.html("""
    <script>
    setTimeout(function(){
        window.parent.location.reload();
    }, 120000);
    </script>
""", height=0)

if st.button("🔍 SPRAWDŹ TERAZ RĘCZNIE"):
    st.rerun()

st.divider()
st.caption(f"v5.7.2 Stable | Odświeżanie: 2 min | Ostatni skan: {time.strftime('%H:%M:%S')}")
