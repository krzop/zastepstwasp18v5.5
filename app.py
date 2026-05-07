import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Monitor SP18 v5.5", page_icon="🏫", layout="centered")

# Inicjalizacja pamięci (aby nie czytać tego samego)
if 'last_results' not in st.session_state:
    st.session_state.last_results = None

st.title("🏫 Monitor SP18 v5.5 - Tryb Czuwania")

# --- INTERFEJS ---
target_name = st.text_input("Nauczyciel:", "Pielok-Opara")
auto_refresh = st.checkbox("Włącz tryb czuwania (auto-odświeżanie co 2 min)", value=True)
check_now = st.button("🔍 SPRAWDŹ TERAZ")

def get_substitutions(name):
    url = "https://sp18.chorzow.pl/substitution/"
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--blink-settings=imagesEnabled=false")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        try:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Informacje dla nauczycieli')]")))
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(4)
        except:
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

# --- LOGIKA ODŚWIEŻANIA I AUDIO ---
if check_now or (auto_refresh and 'trigger_auto' in st.query_params):
    with st.spinner('Czuwam... sprawdzam zmiany...'):
        results = get_substitutions(target_name)
        
        full_speech_text = ""
        should_speak = False
        
        # Sprawdzanie czy dane się zmieniły od ostatniego razu
        if results != st.session_state.last_results:
            should_speak = True
            st.session_state.last_results = results # Zapisz nowe dane w pamięci
            
            if isinstance(results, str):
                st.error(results)
                full_speech_text = "Błąd połączenia."
            elif results:
                st.warning(f"🔔 AKTUALIZACJA dla: **{target_name}**")
                for p, i in results:
                    with st.expander(f"Lekcja {p}", expanded=True):
                        st.write(f"**Opis:** {i.replace('➔', ' ➡️ ')}")
                    full_speech_text += f"Lekcja {p} " + i.replace(":", " klasa ", 1).replace("➔", " zamiana na ") + ". "
            else:
                st.success(f"✅ Brak zastępstw dla: **{target_name}**")
                full_speech_text = f"Dla nazwiska {target_name} brak zastępstw."
        else:
            # Dane są takie same
            if results:
                st.info("ℹ️ Plan bez zmian od ostatniego sprawdzenia.")
                for p, i in results:
                    with st.expander(f"Lekcja {p}", expanded=False):
                        st.write(f"**Opis:** {i.replace('➔', ' ➡️ ')}")
            else:
                st.success("✅ Nadal brak zastępstw.")

        # Wyzwalacz audio (tylko przy zmianie)
        if should_speak and full_speech_text:
            js_text = full_speech_text.replace('"', '').replace("'", "").replace("\n", " ")
            st.components.v1.html(f"""
                <script>
                var msg = new SpeechSynthesisUtterance("{js_text}");
                msg.lang = 'pl-PL'; msg.rate = 0.9;
                window.speechSynthesis.speak(msg);
                </script>
            """, height=0)

# --- SKRYPT AUTO-ODŚWIEŻANIA (JavaScript) ---
if auto_refresh:
    # 30000 ms = 2 minut
    st.components.v1.html("""
        <script>
        setTimeout(function(){
            window.parent.document.querySelector('button[kind="primary"]').click();
        }, 30000); 
        </script>
    """, height=0)
    st.caption("⏱️ Tryb czuwania aktywny: sprawdzanie co 2 minuty.")

st.divider()
st.caption(f"v5.5 Smart Watch | Ostatnie sprawdzenie: {time.strftime('%H:%M:%S')}")
