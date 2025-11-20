from config import *
import time, os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Export functions untuk di-import oleh Streamlit
__all__ = [
    'AntamWarrior', 
    'wait_until_battle_time', 
    'belm_mapping',
    'traditional_antrean_mode', 
    'belanja_online_mode',
    'launch_attack_squad_with_captcha',
    'single_warrior_attack_with_captcha',
    'set_battle_time',
    'set_target_belm',
    'set_max_workers'
]

# ==========================================================
# KONFIGURASI PERANG - FLEXIBLE (BISA DIUBAH DARI APP.PY)
# ==========================================================
BATTLE_TIME = "06:59:58"  # Default, bisa di-override dari app.py
MAX_WORKERS = 3
TARGET_BELM = "BKS01"

def set_battle_time(new_time):
    """Update battle time dari app.py"""
    global BATTLE_TIME
    BATTLE_TIME = new_time
    print(f"🎯 Battle time updated to: {BATTLE_TIME}")

def set_target_belm(new_belm):
    """Update target BELM dari app.py"""
    global TARGET_BELM
    TARGET_BELM = new_belm
    print(f"🎯 Target BELM updated to: {TARGET_BELM}")

def set_max_workers(new_workers):
    """Update max workers dari app.py"""
    global MAX_WORKERS
    MAX_WORKERS = new_workers
    print(f"🎯 Max workers updated to: {MAX_WORKERS}")

# ==========================================================
# MULTI-THREADING SYSTEM - JAM 7 BATTLE
# ==========================================================
class AntamWarrior:
    def __init__(self, warrior_id):
        self.warrior_id = warrior_id
        self.driver = None
        self.status = "READY"
        
    def create_warrior_driver(self):
        """Create optimized driver for battle"""
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-images")
        
        self.driver = uc.Chrome(options=options, headless=False)
        return self.driver
    
    def pre_warm_browser_with_captcha(self):
        """Pre-warm browser + handle reCAPTCHA sebelum battle"""
        try:
            print(f"🔥 Warrior {self.warrior_id}: Pre-warming browser dengan reCAPTCHA...")
            self.driver.get("https://antrean.logammulia.com/login")
            time.sleep(2)
            
            # Pre-fill login form
            username = self.wait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username.clear()
            username.send_keys(EMAIL)
            
            password = self.driver.find_element(By.ID, "password")
            password.clear() 
            password.send_keys(PASSWORD)
            
            # Handle reCAPTCHA dengan 2-strike strategy
            print(f"🛡️ Warrior {self.warrior_id}: Handling reCAPTCHA...")
            recaptcha_result = solve_recaptcha_antrean(self.driver, is_restart_session=False)
            
            if recaptcha_result == "RESTART_NEEDED":
                print(f"🔄 Warrior {self.warrior_id}: Restart needed, retrying...")
                return False
            elif not recaptcha_result:
                print(f"❌ Warrior {self.warrior_id}: reCAPTCHA failed")
                return False
            
            print(f"✅ Warrior {self.warrior_id}: Ready for battle! (reCAPTCHA solved)")
            self.status = "PREPARED"
            return True
            
        except Exception as e:
            print(f"❌ Warrior {self.warrior_id}: Pre-warm failed - {e}")
            return False
    
    def execute_attack_with_captcha(self):
        """Eksekusi serangan dengan reCAPTCHA handling"""
        try:
            print(f"⚡ Warrior {self.warrior_id}: ATTACKING!")
            
            # STEP 1: Langsung klik login (form udah diisi + reCAPTCHA solved)
            login_btn = self.wait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
            )
            self.driver.execute_script("arguments[0].click();", login_btn)
            
            # STEP 2: Tunggu login & pastikan berhasil
            time.sleep(3)
            
            # Cek jika login berhasil, tunggu sampai redirect selesai
            if "antrean" not in self.driver.current_url:
                # Jika belum redirect, tunggu element dashboard
                try:
                    self.wait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//a[contains(., 'Menu Antrean')]"))
                    )
                    print("✅ Login successful, accessing antrean menu...")
                except:
                    print("❌ Login mungkin gagal, cek browser")
                    return False
            
            # STEP 3: Akses menu antrean dulu
            try:
                antrean_btn = self.wait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Menu Antrean')]"))
                )
                self.driver.execute_script("arguments[0].click();", antrean_btn)
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ Tidak bisa akses menu antrean: {e}")
                # Langsung coba buka URL antrean
                self.driver.get("https://antrean.logammulia.com/antrean")
                time.sleep(2)
            
            # STEP 4: Tunggu sampai form antrean load sepenuhnya
            print("🔄 Menunggu form antrean load...")
            try:
                self.wait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "site"))
                )
            except:
                print("❌ Form antrean tidak load, refresh...")
                self.driver.refresh()
                time.sleep(2)
                self.wait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "site"))
                )
            
            # STEP 5: Pilih BELM dengan cara yang lebih reliable
            belm_value = belm_mapping[TARGET_BELM]
            print(f"🎯 Memilih BELM: {TARGET_BELM} -> {belm_value}")
            
            # Cara 1: Pake Selenium Select (lebih reliable)
            try:
                dropdown = self.wait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "site"))
                )
                select = Select(dropdown)
                select.select_by_value(belm_value)
                print("✅ BELM selected via Selenium")
            except Exception as e:
                print(f"❌ Gagal pilih BELM via Selenium: {e}")
                # Cara 2: Pake JavaScript fallback
                try:
                    self.driver.execute_script(f"""
                        var select = document.getElementById('site');
                        if (select) {{
                            select.value = '{belm_value}';
                            // Trigger change event
                            var event = new Event('change', {{ bubbles: true }});
                            select.dispatchEvent(event);
                        }}
                    """)
                    print("✅ BELM selected via JavaScript")
                except Exception as js_error:
                    print(f"❌ Gagal pilih BELM via JS: {js_error}")
                    return False
            
            time.sleep(1)
            
            # STEP 6: Klik tampilkan butik
            try:
                tampilkan_btn = self.wait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Tampilkan Butik')]"))
                )
                self.driver.execute_script("arguments[0].click();", tampilkan_btn)
                print("✅ Tombol Tampilkan Butik diklik")
                time.sleep(3)  # Tunggu loading
            except Exception as e:
                print(f"❌ Gagal klik tampilkan butik: {e}")
                return False
            
            # STEP 7: Pilih waktu kedatangan yang available
            print("⏰ Memilih waktu kedatangan...")
            try:
                # Tunggu dropdown waktu load
                self.wait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "wakda"))
                )
                
                # Cek option yang available
                available_times = self.driver.find_elements(By.XPATH, "//select[@id='wakda']/option[not(@disabled) and not(@value='')]")
                
                if len(available_times) > 0:
                    # Pake JavaScript untuk select
                    self.driver.execute_script("""
                        var select = document.getElementById('wakda');
                        var availableOptions = [];
                        for (var i = 0; i < select.options.length; i++) {
                            if (!select.options[i].disabled && select.options[i].value !== '') {
                                availableOptions.push(select.options[i]);
                            }
                        }
                        if (availableOptions.length > 0) {
                            select.value = availableOptions[0].value;
                            console.log('Selected time: ' + availableOptions[0].value);
                        }
                    """)
                    print(f"✅ Waktu dipilih, {len(available_times)} slot available")
                    time.sleep(1)
                else:
                    print("⚠️ Tidak ada waktu available, lanjut tanpa pilih waktu")
                    
            except Exception as e:
                print(f"⚠️ Gagal pilih waktu: {e}, lanjut tanpa waktu")
            
            # STEP 8: Ambil nomor antrian!
            print("🎫 Mencoba ambil nomor antrian...")
            try:
                # Tunggu tombol ambil antrian
                ambil_btn = self.wait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Ambil Antrean') and not(@disabled)]"))
                )
                
                # Scroll ke tombol biar kelihatan
                self.driver.execute_script("arguments[0].scrollIntoView(true);", ambil_btn)
                time.sleep(0.5)
                
                # Klik tombol
                self.driver.execute_script("arguments[0].click();", ambil_btn)
                print("✅ Tombol Ambil Antrean diklik!")
                
                # Tunggu hasil
                time.sleep(5)
                
                # Cek jika berhasil
                page_text = self.driver.page_source.lower()
                if "berhasil" in page_text or "sukses" in page_text or "nomor antrian" in page_text:
                    print(f"🎉 Warrior {self.warrior_id}: SUCCESS! Antrian berhasil diambil!")
                    self.status = "VICTORY"
                    return True
                else:
                    print(f"⚠️ Warrior {self.warrior_id}: Mungkin berhasil, cek browser untuk konfirmasi...")
                    self.status = "POSSIBLE_VICTORY"
                    return True
                
            except Exception as e:
                print(f"❌ Gagal ambil antrian: {e}")
                # Coba cara alternatif
                try:
                    # Cari tombol dengan JavaScript
                    buttons = self.driver.find_elements(By.XPATH, "//button[contains(., 'Ambil Antrean')]")
                    if buttons:
                        for btn in buttons:
                            if btn.is_enabled():
                                self.driver.execute_script("arguments[0].click();", btn)
                                print("✅ Tombol ditemukan via alternative method")
                                time.sleep(5)
                                return True
                except:
                    pass
                
                self.status = "FAILED"
                return False
            
        except Exception as e:
            print(f"💥 Warrior {self.warrior_id}: Failed - {e}")
            self.status = "FAILED"
            return False
    
    def wait(self, driver, timeout=10):
        return WebDriverWait(driver, timeout)

# ==========================================================
# TIME SYNCHRONIZATION SYSTEM  
# ==========================================================
def get_precise_time():
    return time.strftime("%H:%M:%S")

def wait_until_battle_time():
    print("⏰ Menunggu waktu battle...")
    while True:
        current_time = get_precise_time()
        if current_time >= BATTLE_TIME:
            print("🎯 WAKTU BATTLE! SERANG!!!")
            return True
        time.sleep(0.1)

# ==========================================================
# BATTLE COMMAND CENTER - DENGAN RECAPTCHA
# ==========================================================
def launch_attack_squad_with_captcha():
    print(f"🪖 Meluncurkan {MAX_WORKERS} warriors dengan reCAPTCHA...")
    
    warriors = []
    for i in range(MAX_WORKERS):
        warrior = AntamWarrior(i + 1)
        if warrior.create_warrior_driver():
            if warrior.pre_warm_browser_with_captcha():
                warriors.append(warrior)
            else:
                warrior.driver.quit()
    
    print(f"✅ {len(warriors)} warriors ready for battle!")
    
    if not warriors:
        print("❌ No warriors ready! Exiting...")
        return
    
    wait_until_battle_time()
    
    with ThreadPoolExecutor(max_workers=len(warriors)) as executor:
        futures = [executor.submit(warrior.execute_attack_with_captcha) for warrior in warriors]
        results = [future.result() for future in as_completed(futures)]
    
    victories = sum(results)
    print(f"🏆 BATTLE RESULTS: {victories}/{len(warriors)} SUCCESS!")
    
    for warrior in warriors:
        try:
            input(f"Press Enter to close Warrior {warrior.warrior_id}...")
            warrior.driver.quit()
        except:
            pass

# ==========================================================
# SINGLE MODE DENGAN RECAPTCHA HANDLING (FIXED)
# ==========================================================
def single_warrior_attack_with_captcha():
    """Single warrior dengan reCAPTCHA handling lengkap"""
    print("👤 Single Warrior Mode dengan reCAPTCHA")
    
    warrior = AntamWarrior(0)
    warrior.create_warrior_driver()
    
    try:
        # Pre-warm dengan reCAPTCHA handling
        if warrior.pre_warm_browser_with_captcha():
            print("✅ Browser ready! Waiting for battle time...")
            wait_until_battle_time()
            warrior.execute_attack_with_captcha()
        else:
            print("❌ Failed to prepare browser")
            
    except Exception as e:
        print(f"💥 Error: {e}")
    
    finally:
        input("Press Enter to close browser...")
        warrior.driver.quit()

# ==========================================================
# FUNGSI RECAPTCHA DENGAN 2-STRIKE STRATEGY (ORIGINAL LU)
# ==========================================================
def is_recaptcha_solved(driver):
    """Cek apakah reCAPTCHA sudah solved"""
    try:
        recaptcha_iframe = driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
        driver.switch_to.frame(recaptcha_iframe)
        
        checkbox = driver.find_element(By.ID, "recaptcha-anchor")
        is_checked = checkbox.get_attribute("aria-checked") == "true"
        
        checkmark = driver.find_element(By.CLASS_NAME, "recaptcha-checkbox-checkmark")
        checkmark_visible = "background-position: 0 -600px" not in checkmark.get_attribute("style")
        
        driver.switch_to.default_content()
        return is_checked and checkmark_visible
            
    except Exception as e:
        driver.switch_to.default_content()
        return False

def two_strike_recaptcha_strategy(driver):
    """2-strike strategy: 2x manual → restart → auto"""
    
    for attempt in range(1, 3):
        try:
            # Coba auto click dulu
            recaptcha_iframe = wait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'recaptcha')]"))
            )
            driver.switch_to.frame(recaptcha_iframe)
            
            checkbox = wait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
            )
            checkbox.click()
            
            driver.switch_to.default_content()
            time.sleep(4)
            
            if is_recaptcha_solved(driver):
                return True
            
            # Jika masih challenge, manual solve
            print(f"🖼️ Manual Solve {attempt}/2")
            print("1. Selesaikan gambar captcha di browser")
            print("2. Klik VERIFY setelah selesai") 
            print("3. Tekan ENTER di terminal")
            
            input("⏳ Selesaikan lalu tekan ENTER...")
            
            time.sleep(3)
            if is_recaptcha_solved(driver):
                time.sleep(3)
                return True
            else:
                print("⚠️ reCAPTCHA belum terverifikasi")
                
        except Exception as e:
            continue
    
    print("🔄 Restart browser untuk session trusted...")
    return "RESTART_NEEDED"

def quick_auto_check(driver):
    """Cepat cek apakah bisa auto setelah restart"""
    try:
        recaptcha_iframe = wait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'recaptcha')]"))
        )
        driver.switch_to.frame(recaptcha_iframe)
        
        checkbox = wait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
        )
        checkbox.click()
        
        driver.switch_to.default_content()
        time.sleep(5)
        return is_recaptcha_solved(driver)
            
    except Exception as e:
        return False

def solve_recaptcha_antrean(driver, is_restart_session=False):
    """Main reCAPTCHA solver dengan 2-strike strategy"""
    try:
        recaptcha_iframe = wait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//iframe[contains(@src, 'recaptcha')]"))
        )
        
        if is_restart_session:
            if quick_auto_check(driver):
                return True
        
        result = two_strike_recaptcha_strategy(driver)
        
        if result == "RESTART_NEEDED":
            return "RESTART_NEEDED"
        else:
            return result
            
    except Exception as e:
        return True

# ==========================================================
# UTILITIES (ORIGINAL LU)
# ==========================================================
def wait(driver, t=10):
    return WebDriverWait(driver, t)

def find(driver, by, value, timeout=10):
    return wait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def click(driver, by, value, timeout=10):
    el = wait(driver, timeout).until(
        EC.element_to_be_clickable((by, value))
    )
    el.click()
    return el

def ensure_dir(d):
    if not os.path.exists(d):
        os.makedirs(d)

def save_screenshot(driver, name):
    ensure_dir("screenshots")
    path = f"screenshots/{name}"
    driver.save_screenshot(path)

def create_driver():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return uc.Chrome(options=options, headless=False)

# ==========================================================
# BELM MAPPING (ORIGINAL LU)
# ==========================================================
belm_mapping = {
    "BKS01": "19",  # Bekasi
    "JKT01": "3",   # Graha Dipta
    "JKT02": "6",   # Gedung Antam  
    "JKT03": "8",   # Setiabudi One
    "BDG01": "1",   # Bandung
    "SMG01": "15",  # Semarang
    "YGY01": "9",   # Yogyakarta
    "SBY01": "13",  # Surabaya Darmo
    "SBY02": "14",  # Surabaya Pakuwon
    "DPS01": "5",   # Denpasar
    "BPN01": "4",   # Balikpapan
    "MKS01": "11",  # Makassar
    "MDN01": "10",  # Medan
    "PLB01": "12",  # Palembang
    "PKU01": "24",  # Pekanbaru
    "SRP01": "23",  # Serpong
    "BTR01": "16",  # Bintaro
    "BGR01": "17",  # Bogor
    "JKT05": "20",  # Djuanda
    "JKT06": "21"   # Puri Indah
}

# ==========================================================
# ENHANCED LOGIN DENGAN RESTART SUPPORT (ORIGINAL LU)
# ==========================================================
def login_antrean_with_restart(driver, max_restarts=2):
    """Login dengan support restart session"""
    
    restarts_count = 0
    
    while restarts_count <= max_restarts:
        if restarts_count > 0:
            print(f"🔄 Restart Session #{restarts_count}")
            driver.quit()
            time.sleep(2)
            driver = create_driver()
        
        try:
            driver.get("https://antrean.logammulia.com/login")
            time.sleep(3)
            
            # Isi credentials
            username_input = wait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            username_input.clear()
            username_input.send_keys(EMAIL)
            
            password_input = wait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "password"))
            )
            password_input.clear()
            password_input.send_keys(PASSWORD)
            
            time.sleep(2)
            
            # Handle reCAPTCHA
            is_restart_session = (restarts_count > 0)
            recaptcha_result = solve_recaptcha_antrean(driver, is_restart_session)
            
            if recaptcha_result == "RESTART_NEEDED":
                restarts_count += 1
                continue
            elif not recaptcha_result:
                return False
            
            # Klik login button
            login_btn = wait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' or contains(., 'Log in')]"))
            )
            driver.execute_script("arguments[0].click();", login_btn)
            
            # Tunggu proses login
            time.sleep(5)
            
            # Cek jika login berhasil
            if "dashboard" in driver.current_url or "antrean" in driver.current_url:
                print("✅ Login berhasil!")
                return True
            else:
                restarts_count += 1
                continue
                
        except Exception as e:
            restarts_count += 1
            continue
    
    return False

# ==========================================================
# SISTEM ANTREAN - FUNGSI UTAMA (ORIGINAL LU)
# ==========================================================
def akses_menu_antrean(driver):
    """Akses menu antrean dari dashboard"""
    try:
        antrean_btn = wait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Menu Antrean')]"))
        )
        driver.execute_script("arguments[0].click();", antrean_btn)
        time.sleep(3)
        return True
        
    except Exception as e:
        return False

def pilih_belm_antrean(driver, kode_wilayah="BKS01"):
    """Pilih BELM di sistem antrean"""
    
    if kode_wilayah not in belm_mapping:
        return False
        
    belm_value = belm_mapping[kode_wilayah]
    
    try:
        dropdown = wait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "site"))
        )
        
        select = Select(dropdown)
        select.select_by_value(belm_value)
        
        tampilkan_btn = wait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Tampilkan Butik')]"))
        )
        driver.execute_script("arguments[0].click();", tampilkan_btn)
        time.sleep(3)
        
        return True
        
    except Exception as e:
        return False

def pilih_waktu_kedatangan(driver):
    """Pilih waktu kedatangan yang tersedia"""
    try:
        waktu_dropdown = wait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "wakda"))
        )
        
        available_times = driver.find_elements(By.XPATH, "//select[@id='wakda']/option[not(@disabled) and not(@value='')]")
        
        if len(available_times) > 0:
            select = Select(waktu_dropdown)
            select.select_by_index(1)
            time.sleep(1)
            return True
        else:
            return False
            
    except Exception as e:
        return False

def ambil_nomor_antrean(driver):
    """Ambil nomor antrian jika tersedia"""
    try:
        nomor_btn = wait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Ambil Antrean') and not(@disabled)]"))
        )
        driver.execute_script("arguments[0].click();", nomor_btn)
        time.sleep(3)
        return True
        
    except:
        return False

def sistem_antrean_lengkap(driver, kode_wilayah="BKS01"):
    """Full process sistem antrean dengan restart support"""
    try:
        # Step 1: Login dengan restart support
        if not login_antrean_with_restart(driver):
            return False
            
        # Step 2: Akses menu antrean
        if not akses_menu_antrean(driver):
            return False
            
        # Step 3: Pilih BELM
        if not pilih_belm_antrean(driver, kode_wilayah):
            return False
            
        # Step 4: Pilih waktu kedatangan
        if not pilih_waktu_kedatangan(driver):
            print("⏰ Lanjut tanpa waktu kedatangan")
            
        # Step 5: Ambil nomor antrian
        if ambil_nomor_antrean(driver):
            print("🎉 Nomor antrian berhasil diambil!")
        else:
            print("❌ Tidak bisa ambil nomor antrian")
            
        return True
        
    except Exception as e:
        return False

# ==========================================================
# FUNGSI UNTUK MODE BELANJA ONLINE (ORIGINAL LU)
# ==========================================================
pilih_wilayah_by_value = {
    "JKT01": "BELM - Pengiriman Ekspedisi, Pulogadung Jakarta, Jakarta",
    "JKT02": "BELM - Graha Dipta (Pengambilan Di Butik) Pulo Gadung, Jakarta",
    "JKT03": "BELM - Gedung Antam (pengambilan Di Butik), Jakarta",
    "JKT04": "BELM - Setiabudi One (pengambilan Di Butik), Jakarta",
    "BDG01": "BELM - Bandung, Bandung",
    "SMG01": "BELM - Semarang, Semarang",
    "YGY01": "BELM - Yogyakarta, Yogyakarta",
    "SBY01": "BELM - Surabaya Darmo, Surabaya",
    "SBY02": "BELM - Surabaya Pakuwon, Surabaya",
    "DPS01": "BELM - Denpasar Bali, Bali",
    "BPN01": "BELM - Balikpapan, Balikpapan",
    "MKS01": "BELM - Makassar, Makassar",
    "MDN01": "BELM - Medan, Medan",
    "PLB01": "BELM - Palembang, Palembang",
    "PKU01": "BELM - Pekanbaru, Pekanbaru",
    "SRP01": "BELM - Serpong (pengambilan Di Butik), Tangerang",
    "BTR01": "BELM - Bintaro, Tangerang Selatan",
    "BGR01": "BELM - Bogor, Bogor",
    "BKS01": "BELM - Bekasi, Bekasi",
    "JKT05": "BELM - Juanda, Jakarta",
    "JKT06": "BELM - Puri Indah, Jakarta"
}

def pilih_wilayah(driver, kode):
    if kode not in pilih_wilayah_by_value:
        return False

    teks_lokasi = pilih_wilayah_by_value[kode]

    select_box = click(driver, By.ID, "select2-location-container", timeout=10)
    time.sleep(0.5)

    search_box = find(driver, By.CSS_SELECTOR, "input.select2-search__field", timeout=10)
    search_box.clear()
    search_box.send_keys(teks_lokasi)
    time.sleep(1)

    opsi = click(
        driver,
        By.XPATH,
        f"//li[contains(@class,'select2-results__option') and contains(., '{teks_lokasi}')]",
        timeout=10
    )

    click(driver, By.ID, "change-location-button", timeout=10)
    return True

def handle_popup_tujuan_transaksi(driver):
    """Handle popup konfirmasi tujuan transaksi"""
    try:
        wait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(., 'Konfirmasi Tujuan Transaksi')]"))
        )
        
        confirm_btn = wait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "change-destination-transaction-button"))
        )
        driver.execute_script("arguments[0].click();", confirm_btn)
        time.sleep(3)
        return True
        
    except Exception as e:
        return True
    
def tambah_produk_ke_keranjang(driver, product_name="Logam Mulia ANTAM 1 gr", quantity=1):
    """Pilih produk dan tambah ke keranjang"""
    try:
        product_element = wait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), '{product_name}')]"))
        )
        driver.execute_script("arguments[0].click();", product_element)
        time.sleep(2)
        
        qty_input = wait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//input[@type='number' and contains(@name, 'qty')]"))
        )
        
        driver.execute_script("arguments[0].value = '';", qty_input)
        qty_input.send_keys(str(quantity))
        time.sleep(1)
        
        tambah_btn = wait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "add-cart-button-gold"))
        )
        driver.execute_script("arguments[0].click();", tambah_btn)
        time.sleep(3)
        
        return True
        
    except Exception as e:
        return False

def checkout_dari_keranjang(driver):
    """Checkout setelah produk ditambahkan ke keranjang"""
    try:
        checkout_selectors = [
            "//a[contains(., 'Checkout')]",
            "//button[contains(., 'Checkout')]",
            "//a[contains(@href, 'checkout')]",
            "//a[contains(., 'Lanjut ke Pembayaran')]"
        ]
        
        for selector in checkout_selectors:
            try:
                checkout_btn = wait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                driver.execute_script("arguments[0].click();", checkout_btn)
                time.sleep(3)
                return True
            except:
                continue
        
        return False
        
    except Exception as e:
        return False

def klik_beli_emas(driver):
    btn = wait(driver, 20).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='purchase/gold']"))
    )
    btn.click()
    
    time.sleep(3)
    handle_popup_tujuan_transaksi(driver)

def login_belanja_online(driver):
    """Login untuk mode belanja online"""
    driver.get(LOGIN_URL)
    time.sleep(WAIT_MED)

    email = find(driver, By.XPATH, "//input[@type='email' or contains(@name,'email')]", timeout=10)
    email.clear()
    email.send_keys(EMAIL)

    password = find(driver, By.XPATH, "//input[@type='password']", timeout=10)
    password.clear()
    password.send_keys(PASSWORD)

    try:
        click(driver,
              By.XPATH,
              "//button[contains(translate(.,'MASUK','masuk'),'masuk') or contains(.,'Login')]",
              timeout=5)
    except:
        password.send_keys(Keys.ENTER)

    time.sleep(WAIT_LONG)

# ==========================================================
# MODE TRADITIONAL & BELANJA ONLINE (ORIGINAL)
# ==========================================================
def traditional_antrean_mode():
    """Mode antrean traditional dengan semua fitur original"""
    print("🎫 MODE SISTEM ANTREAN TRADITIONAL")
    driver = create_driver()
    try:
        sistem_antrean_lengkap(driver, DEFAULT_WILAYAH)
    finally:
        input("Press Enter to close browser...")
        driver.quit()

def belanja_online_mode():
    """Mode belanja online original"""
    print("🛒 MODE BELANJA ONLINE")
    driver = create_driver()
    try:
        login_belanja_online(driver)
        time.sleep(2)
        pilih_wilayah(driver, DEFAULT_WILAYAH)
        klik_beli_emas(driver)
        tambah_produk_ke_keranjang(driver, "Logam Mulia ANTAM 1 gr", 1)
        checkout_dari_keranjang(driver)
        print("🎉 PROSES BELI EMAS SELESAI!")
    finally:
        input("Press Enter to close browser...")
        driver.quit()

# ==========================================================
# MAIN BATTLE CONTROL - UPDATED
# ==========================================================
def main():
    print("""
    🎯 ANTAM BOT - ULTIMATE BATTLE EDITION 🎯
    ========================================
    """)
    
    print("PILIH STRATEGI PERANG:")
    print("1. ⚡ LIGHTNING ATTACK (Multi-thread Jam 7 + reCAPTCHA)")
    print("2. 🤺 SINGLE WARRIOR (Fast Jam 7 + reCAPTCHA)") 
    print("3. 🎫 TRADITIONAL ANTREAN (Full feature)")
    print("4. 🛒 BELANJA ONLINE (Original)")
    
    choice = input("Pilih mode (1/2/3/4): ")
    
    if choice == "1":
        print("🚀 Launching Multi-Thread Attack Squad dengan reCAPTCHA...")
        launch_attack_squad_with_captcha()
    elif choice == "2":
        print("👤 Launching Single Warrior dengan reCAPTCHA...")
        single_warrior_attack_with_captcha()
    elif choice == "3":
        traditional_antrean_mode()
    elif choice == "4":
        belanja_online_mode()
    else:
        print("Default: Single Warrior dengan reCAPTCHA")
        single_warrior_attack_with_captcha()

if __name__ == "__main__":
    main()