import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

# --- KONFIGURACJA ---
st.set_page_config(page_title="Monitor SP18 v5.6.1", page_icon="🏫")

# Inicjalizacja stabilnej pamięci
if 'last_data' not in st.session_state:
    st.session_state.last_data = ""

st.title("🏫 Monitor SP18 v5.6.1 - Safe Watch")

target_name = st.text_input("Nauczyciel:", "Pielok-Opara")
auto_mode = st.toggle("Tryb czuwania (auto-odświeżanie co 2 minuty)", value=False)

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
            time.sleep(3)
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

# --- GŁÓWNA LOGIKA ---
manual_check = st.button("🔍 SPRAWDŹ TERAZ")

# Mechanizm automatycznego wyzwalania (Refresh: 2 minuty)
if auto_mode:
    st.info("⏱️ Tryb czuwania aktywny. Następne sprawdzenie za 2 minuty.")
    # 120000 ms = 120 sekund = 2 minuty
    st.components.v1.html("""
        <script>
        setTimeout(function(){ 
            window.parent.location.reload(); 
        }, 120000);
        </script>
    """, height=0)

if manual_check or auto_mode:
    with st.spinner('Pobieram dane...'):
        results = get_substitutions(target_name)
        
        current_data_str = str(results)
        speech_text = ""

        if current_data_str != st.session_state.last_data:
            # ZAPISUJEMY ZMIANĘ
            st.session_state.last_data = current_data_str
            
            if isinstance(results, list):
                if results:
                    st.warning(f"🔔 ZMIANA W PLANIE dla: {target_name}")
                    for p, i in results:
                        with st.expander(f"Lekcja {p}", expanded=True):
                            st.write(f"Opis: {i.replace('➔', '➡️')}")
                        speech_text += f"Lekcja {p} " + i.replace(":", " klasa ", 1).replace("➔", " zamiana na ") + ". "
                else:
                    st.success(f"✅ Brak zastępstw dla: {target_name}")
                    speech_text = f"Dla nazwiska {target_name} brak nowych zastępstw."
            
            # Odpal mowę
            if speech_text:
                clean_speech = speech_text.replace('"', '').replace("'", "")
                st.components.v1.html(f"""
                    <script>
                    var msg = new SpeechSynthesisUtterance("{clean_speech}");
                    msg.lang = 'pl-PL'; msg.rate = 0.9;
                    window.speechSynthesis.speak(msg);
                    </script>
                """, height=0)
        else:
            # Dane identyczne - milczymy
            if isinstance(results, list) and results:
                st.info("ℹ️ Plan bez zmian (już odczytany).")
                for p, i in results:
                    with st.expander(f"Lekcja {p}", expanded=False):
                        st.write(i)
            else:
                st.success("✅ Nadal brak zastępstw. Cisza.")

st.divider()
st.caption(f"v5.6.1 Safe Watch | Co 2 min | {time.strftime('%H:%M:%S')}")
