import streamlit as st
import time
import threading
from datetime import datetime, timedelta
import sys
import os

# Add current directory to path untuk import bot
sys.path.append(os.path.dirname(__file__))

# Set page config
st.set_page_config(
    page_title="🤖 ANTAM BOT",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #FFD700;
        text-align: center;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        font-weight: bold;
    }
    .status-ready {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .status-running {
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    .status-success {
        background-color: #d1ecf1;
        color: #0c5460;
        border: 1px solid #bee5eb;
    }
    .status-error {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    .warrior-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        color: white;
    }
    .stButton button {
        width: 100%;
    }
    .credentials-info {
        background-color: #e8f4fd;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #2196F3;
        margin: 1rem 0;
    }
    .time-info {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class AntamBotUI:
    def __init__(self):
        self.is_running = False
        self.bot_thread = None
        self.logs = []
        self.warriors_status = {}
        self.current_warrior = None
        self.stop_requested = False
        self.ambil_antrean_btn = None
        
    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        # Keep only last 50 logs
        if len(self.logs) > 50:
            self.logs.pop(0)
        print(f"LOG: {log_entry}")
            
    def stop_bot(self):
        """Stop bot dan cleanup resources"""
        self.stop_requested = True
        self.is_running = False
        
        if self.current_warrior and hasattr(self.current_warrior, 'driver'):
            try:
                self.add_log("🔄 Closing browser...")
                self.current_warrior.driver.quit()
                self.add_log("✅ Browser closed successfully")
            except Exception as e:
                self.add_log(f"⚠️ Error closing browser: {e}")
        
        self.current_warrior = None
        self.ambil_antrean_btn = None
        self.stop_requested = False

    def wait_for_battle_time(self, battle_time_str):
        """Tunggu sampe waktu battle dengan countdown"""
        try:
            # Parse battle time
            battle_time = datetime.strptime(battle_time_str, "%H:%M:%S").time()
            
            while True:
                if self.stop_requested:
                    return False
                
                now = datetime.now()
                target_datetime = datetime.combine(now.date(), battle_time)
                
                # Jika sudah lewat hari ini, tunggu besok
                if now > target_datetime:
                    target_datetime = target_datetime + timedelta(days=1)
                
                time_diff = (target_datetime - now).total_seconds()
                
                # Jika sudah kurang dari 3 detik, siap-siap attack
                if time_diff <= 3:
                    self.add_log("🎯 WAKTU BATTLE! SERANG!!!")
                    return True
                
                # Update countdown setiap 10 detik
                if int(time_diff) % 10 == 0:
                    hours = int(time_diff // 3600)
                    minutes = int((time_diff % 3600) // 60)
                    seconds = int(time_diff % 60)
                    if hours > 0:
                        self.add_log(f"⏳ Countdown: {hours:02d}:{minutes:02d}:{seconds:02d}")
                    else:
                        self.add_log(f"⏳ Countdown: {minutes:02d}:{seconds:02d}")
                
                time.sleep(1)
                
        except Exception as e:
            self.add_log(f"💥 Error in countdown: {e}")
            return False

    def setup_antrean_form(self, belm_target):
        """Setup form antrean sampe siap, tombol dicari nanti pas battle time"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait, Select
            from selenium.webdriver.support import expected_conditions as EC
            
            # Import belm_mapping dari main.py
            from main import belm_mapping
            
            driver = self.current_warrior.driver
            
            # STEP 1: Akses menu antrean dulu
            self.add_log("🔍 Accessing Menu Antrean...")
            try:
                antrean_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Menu Antrean')]"))
                )
                driver.execute_script("arguments[0].click();", antrean_btn)
                self.add_log("✅ Menu Antrean clicked!")
                time.sleep(2)
            except Exception as e:
                self.add_log(f"⚠️ Cannot find Menu Antrean: {e}, trying direct access...")
                driver.get("https://antrean.logammulia.com/antrean")
                time.sleep(2)
            
            # STEP 2: Tunggu form antrean load
            self.add_log("🔄 Loading antrean form...")
            site_dropdown = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "site"))
            )
            self.add_log("✅ Antrean form loaded")
            
            # STEP 3: Pilih BELM
            belm_code = belm_target.split(" - ")[0]
            belm_value = belm_mapping.get(belm_code)
            
            if not belm_value:
                self.add_log(f"❌ BELM code {belm_code} not found in mapping")
                return False
                
            self.add_log(f"🎯 Selecting BELM: {belm_code} -> {belm_value}")
            
            select = Select(site_dropdown)
            select.select_by_value(belm_value)
            time.sleep(1)
            
            # STEP 4: Klik tampilkan butik
            self.add_log("🔄 Clicking 'Tampilkan Butik'...")
            tampilkan_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Tampilkan Butik')]"))
            )
            driver.execute_script("arguments[0].click();", tampilkan_btn)
            self.add_log("✅ Tombol Tampilkan Butik diklik")
            time.sleep(3)
            
            # STEP 5: Pilih waktu kedatangan yang available
            self.add_log("⏰ Memilih waktu kedatangan...")
            try:
                waktu_dropdown = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "wakda"))
                )
                
                # Cek option yang available
                available_times = driver.find_elements(By.XPATH, "//select[@id='wakda']/option[not(@disabled) and not(@value='')]")
                
                if len(available_times) > 0:
                    # Pake JavaScript untuk select waktu pertama yang available
                    driver.execute_script("""
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
                    self.add_log(f"✅ Waktu dipilih, {len(available_times)} slot available")
                    time.sleep(1)
                else:
                    self.add_log("⚠️ Tidak ada waktu available, lanjut tanpa pilih waktu")
                    
            except Exception as e:
                self.add_log(f"⚠️ Gagal pilih waktu: {e}, lanjut tanpa waktu")
            
            # STEP 6: FORM SUDAH SIAP! Tombol akan dicari nanti pas battle time
            self.add_log("✅ Form antrean siap! Tombol Ambil Antrean akan dicari saat battle time...")
            return True
            
        except Exception as e:
            self.add_log(f"❌ Gagal setup form antrean: {str(e)}")
            return False

    def execute_final_attack(self):
        """CARI & KLIK tombol Ambil Antrean saat battle time"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            driver = self.current_warrior.driver
            
            self.add_log("🎯 MENCARI tombol Ambil Antrean...")
            
            # Tunggu dan cari tombol Ambil Antrean yang ENABLED
            ambil_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Ambil Antrean') and not(@disabled)]"))
            )
            
            self.add_log("✅ Tombol Ambil Antrean DITEMUKAN! MENGKLIK...")
            
            # Scroll ke tombol biar kelihatan
            driver.execute_script("arguments[0].scrollIntoView(true);", ambil_btn)
            time.sleep(0.5)
            
            # KLIK TOMBOL!
            driver.execute_script("arguments[0].click();", ambil_btn)
            self.add_log("🎉 Tombol Ambil Antrean diklik!")
            
            # Tunggu hasil
            time.sleep(5)
            
            # Cek jika berhasil
            page_text = driver.page_source.lower()
            success_indicators = ["berhasil", "sukses", "nomor antrian", "antrian berhasil", "terima kasih"]
            
            for indicator in success_indicators:
                if indicator in page_text:
                    self.add_log("🎉 SUCCESS! Antrian berhasil diambil!")
                    return True
            
            # Cek jika ada error
            error_indicators = ["gagal", "error", "tidak tersedia", "sudah penuh"]
            for indicator in error_indicators:
                if indicator in page_text:
                    self.add_log(f"❌ Antrian {indicator}")
                    return False
            
            self.add_log("⚠️ Status tidak jelas, cek browser untuk konfirmasi...")
            return True
            
        except Exception as e:
            self.add_log(f"❌ Gagal cari/klik Ambil Antrean: {str(e)}")
            
            # Coba cara alternatif
            try:
                self.add_log("🔄 Mencoba cara alternatif...")
                buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Ambil Antrean')]")
                for btn in buttons:
                    if btn.is_enabled():
                        driver.execute_script("arguments[0].click();", btn)
                        self.add_log("✅ Tombol diklik via alternatif!")
                        time.sleep(5)
                        return True
            except:
                pass
            
            return False

    def run_single_warrior(self, belm_target, battle_time_str):
        """Run single warrior mode - PREPARE SEMUA SEBELUM BATTLE TIME"""
        try:
            from main import AntamWarrior, set_battle_time
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Set battle time dari UI
            set_battle_time(battle_time_str)
            self.add_log(f"🎯 Battle time set to: {battle_time_str}")
            
            # Load credentials dari config.py
            # Load credentials dari config.py atau environment variables
            try:
                import os
                # Coba dari environment variables dulu
                email = os.environ.get('EMAIL')
                password = os.environ.get('PASSWORD')
                
                if not email or not password:
                    # Fallback ke config.py
                    from config import EMAIL, PASSWORD
                    email = EMAIL
                    password = PASSWORD
                    self.add_log("✅ Credentials loaded from config.py")
                else:
                    self.add_log("✅ Credentials loaded from environment variables")
                    
            except Exception as e:
                self.add_log(f"❌ Failed to load credentials: {e}")
                return
            
            self.add_log("🔄 Initializing Single Warrior...")
            
            # Setup warrior
            self.current_warrior = AntamWarrior(0)
            if self.current_warrior.create_warrior_driver():
                self.add_log("✅ Browser created successfully")
                
                # Step 1: Buka login page
                self.current_warrior.driver.get("https://antrean.logammulia.com/login")
                time.sleep(2)
                
                # Step 2: Isi credentials dari config.py
                username = WebDriverWait(self.current_warrior.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
                username.clear()
                username.send_keys(email)
                
                password_elem = self.current_warrior.driver.find_element(By.ID, "password")
                password_elem.clear()
                password_elem.send_keys(password)
                
                self.add_log("✅ Credentials filled")
                
                # Step 3: Auto-detect reCAPTCHA status
                self.add_log("🛡️ Waiting for reCAPTCHA to be solved...")
                self.add_log("👤 Please manually solve the reCAPTCHA in the browser")
                
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
                
                # Tunggu maksimal 10 menit buat user solve reCAPTCHA
                max_wait_time = 600  # 10 menit
                start_time = time.time()
                recaptcha_solved = False
                last_status_time = start_time
                
                while time.time() - start_time < max_wait_time and not recaptcha_solved:
                    if self.stop_requested:
                        self.add_log("⏹️ Bot stopped by user")
                        return
                        
                    recaptcha_solved = is_recaptcha_solved(self.current_warrior.driver)
                    
                    if recaptcha_solved:
                        self.add_log("✅ reCAPTCHA SOLVED! Auto-clicking login...")
                        
                        # Langsung klik login button
                        login_btn = WebDriverWait(self.current_warrior.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
                        )
                        self.current_warrior.driver.execute_script("arguments[0].click();", login_btn)
                        self.add_log("✅ Login button clicked! Waiting for login...")
                        break
                    else:
                        # Kasih status update setiap 15 detik
                        current_time = time.time()
                        if current_time - last_status_time >= 15:
                            elapsed = int(current_time - start_time)
                            minutes = elapsed // 60
                            seconds = elapsed % 60
                            self.add_log(f"⏳ Waiting for reCAPTCHA... ({minutes:02d}:{seconds:02d} elapsed)")
                            last_status_time = current_time
                        time.sleep(1)
                
                if not recaptcha_solved:
                    self.add_log("❌ reCAPTCHA not solved within 10 minutes")
                    return
                    
                # Step 4: Tunggu login berhasil
                self.add_log("🔄 Waiting for login to complete...")
                time.sleep(5)
                
                # Step 5: Setup form antrean SAMPAI SIAP (tapi belum cari tombol)
                self.add_log("🔧 Setting up antrean form...")
                if self.setup_antrean_form(belm_target):
                    self.add_log("✅ Antrean form ready! Waiting for battle time...")
                    self.warriors_status = {"Warrior 0": "Ready - Waiting Battle Time"}
                else:
                    self.add_log("❌ Failed to setup antrean form")
                    return
                
                # Step 6: Tunggu sampe waktu battle
                self.add_log(f"⏰ Waiting for battle time ({battle_time_str})...")
                if not self.wait_for_battle_time(battle_time_str):
                    self.add_log("⏹️ Bot stopped while waiting for battle time")
                    return
                
                # Step 7: KLIK Ambil Antrean!
                self.add_log("⚡ EXECUTING FINAL ATTACK!")
                self.warriors_status = {"Warrior 0": "Attacking"}
                
                success = self.execute_final_attack()
                
                if success:
                    self.add_log("🎉 ANTRIAN BERHASIL DAPAT!")
                    self.warriors_status = {"Warrior 0": "Success"}
                else:
                    self.add_log("❌ Gagal mengambil antrian")
                    self.warriors_status = {"Warrior 0": "Failed"}
                    
            else:
                self.add_log("❌ Failed to create browser")
                self.warriors_status = {"Warrior 0": "Failed"}
                
        except Exception as e:
            self.add_log(f"💥 Error: {str(e)}")
            self.warriors_status = {"Warrior 0": "Error"}
        finally:
            self.is_running = False
            
    def run_traditional_mode(self, belm_target, battle_time_str):
        """Run traditional mode"""
        try:
            from main import traditional_antrean_mode, set_battle_time
            
            # Set battle time
            set_battle_time(battle_time_str)
            
            self.add_log("🎫 Running Traditional Antrean Mode...")
            self.warriors_status = {"Traditional": "Running"}
            
            # Jalankan traditional mode
            traditional_antrean_mode()
            
            self.add_log("✅ Traditional mode completed")
            self.warriors_status = {"Traditional": "Success"}
            
        except Exception as e:
            self.add_log(f"💥 Error: {str(e)}")
            self.warriors_status = {"Traditional": "Failed"}
        finally:
            self.is_running = False
            
    def run_belanja_online(self, belm_target, battle_time_str):
        """Run belanja online mode"""
        try:
            from main import belanja_online_mode, set_battle_time
            
            # Set battle time
            set_battle_time(battle_time_str)
            
            self.add_log("🛒 Running Belanja Online Mode...")
            self.warriors_status = {"Belanja Online": "Running"}
            
            # Jalankan belanja online mode
            belanja_online_mode()
            
            self.add_log("✅ Belanja online completed")
            self.warriors_status = {"Belanja Online": "Success"}
            
        except Exception as e:
            self.add_log(f"💥 Error: {str(e)}")
            self.warriors_status = {"Belanja Online": "Failed"}
        finally:
            self.is_running = False

    def run_multi_thread(self, belm_target, battle_time_str):
        """Run multi-thread mode"""
        try:
            from main import launch_attack_squad_with_captcha, set_battle_time
            
            # Set battle time
            set_battle_time(battle_time_str)
            
            self.add_log("🪖 Launching Multi-Thread Attack Squad...")
            self.warriors_status = {
                "Warrior 1": "Preparing",
                "Warrior 2": "Preparing", 
                "Warrior 3": "Preparing"
            }
            
            # Jalankan multi-thread attack
            launch_attack_squad_with_captcha()
            
            self.add_log("✅ Multi-thread attack completed")
            self.warriors_status = {f"Warrior {i+1}": "Success" for i in range(3)}
            
        except Exception as e:
            self.add_log(f"💥 Error: {str(e)}")
            self.warriors_status = {f"Warrior {i+1}": "Failed" for i in range(3)}
        finally:
            self.is_running = False

def main():
    # Initialize session state untuk persist data across reruns
    if 'bot_ui' not in st.session_state:
        st.session_state.bot_ui = AntamBotUI()
    
    bot_ui = st.session_state.bot_ui
    
    # Header
    st.markdown('<h1 class="main-header">🤖 ANTAM BOT - Ultimate Battle Edition</h1>', unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Credentials INFO (otomatis dari config.py)
        st.subheader("🔐 Credentials")
        try:
            from config import EMAIL, PASSWORD
            st.markdown(f"""
            <div class="credentials-info">
                <strong>📧 Email:</strong> {EMAIL}<br>
                <strong>🔑 Password:</strong> {'*' * len(PASSWORD)}<br>
                <strong>Status:</strong> ✅ Loaded from config.py
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"❌ Gagal load credentials dari config.py: {e}")
            st.stop()
        
        # Mode selection
        mode = st.selectbox(
            "Battle Mode",
            ["Single Warrior", "Multi-Thread Attack", "Traditional", "Belanja Online"],
            index=0
        )
        
        # BELM selection
        belm_options = {
            "BKS01 - Bekasi": "BKS01",
            "JKT01 - Graha Dipta": "JKT01", 
            "JKT02 - Gedung Antam": "JKT02",
            "JKT03 - Setiabudi One": "JKT03",
            "BDG01 - Bandung": "BDG01",
            "SBY01 - Surabaya Darmo": "SBY01",
            "DPS01 - Denpasar": "DPS01"
        }
        
        belm_target = st.selectbox(
            "Target BELM",
            list(belm_options.keys()),
            index=0
        )
        
        # Timing configuration
        st.subheader("⏰ Battle Timing")
        battle_time = st.time_input(
            "Attack Time",
            value=datetime.strptime("06:59:58", "%H:%M:%S").time()  # Default 2 detik lebih awal
        )
        battle_time_str = battle_time.strftime("%H:%M:%S")
        
        st.markdown(f"""
        <div class="time-info">
            <strong>Battle Time:</strong> {battle_time_str}<br>
            <strong>Countdown:</strong> Akan dimulai saat bot running
        </div>
        """, unsafe_allow_html=True)
        
        # Control buttons
        col1, col2 = st.columns(2)
        with col1:
            start_disabled = bot_ui.is_running
            if st.button("🚀 Start Bot", type="primary", use_container_width=True, disabled=start_disabled):
                if not bot_ui.is_running:
                    bot_ui.is_running = True
                    bot_ui.warriors_status = {}
                    bot_ui.logs = []  # Clear previous logs
                    
                    # Start bot in separate thread berdasarkan mode
                    if mode == "Single Warrior":
                        bot_thread = threading.Thread(
                            target=bot_ui.run_single_warrior, 
                            args=(belm_target, battle_time_str)
                        )
                    elif mode == "Multi-Thread Attack":
                        bot_thread = threading.Thread(
                            target=bot_ui.run_multi_thread,
                            args=(belm_target, battle_time_str)
                        )
                    elif mode == "Traditional":
                        bot_thread = threading.Thread(
                            target=bot_ui.run_traditional_mode,
                            args=(belm_target, battle_time_str)
                        )
                    else:  # Belanja Online
                        bot_thread = threading.Thread(
                            target=bot_ui.run_belanja_online,
                            args=(belm_target, battle_time_str)
                        )
                    
                    bot_thread.daemon = True
                    bot_thread.start()
                    bot_ui.add_log(f"🚀 Starting {mode} mode for {belm_target} at {battle_time_str}")
                    
        with col2:
            if st.button("🛑 Stop Bot", use_container_width=True):
                bot_ui.stop_bot()
                bot_ui.add_log("⏹️ Bot stopping...")

    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Status dashboard
        st.header("📊 Battle Dashboard")
        
        # Current status
        status_text = "🟢 RUNNING" if bot_ui.is_running else "🔴 STOPPED"
        status_color = "status-running" if bot_ui.is_running else "status-ready"
        st.markdown(f'<div class="status-box {status_color}">Status: {status_text}</div>', unsafe_allow_html=True)
        
        # Mode info
        st.metric("Current Mode", mode)
        st.metric("Target BELM", belm_target)
        
        # Warriors status
        if bot_ui.warriors_status:
            st.subheader("🪖 Warriors Status")
            for warrior, status in bot_ui.warriors_status.items():
                status_emoji = "🟢" if status == "Success" else "🟡" if status in ["Running", "Ready", "Attacking", "Preparing", "Ready - Waiting Battle Time"] else "🔴"
                st.markdown(f'<div class="warrior-card">{status_emoji} {warrior}: {status}</div>', unsafe_allow_html=True)
        
        # Real-time logs
        st.subheader("📝 Battle Logs")
        
        # Create a container for logs
        log_container = st.container()
        
        with log_container:
            # Tampilkan logs terbaru
            if bot_ui.logs:
                log_text = "\n".join(bot_ui.logs)
                st.code(log_text, language="bash")
            else:
                st.info("No logs yet. Start the bot to see logs here.")
        
    with col2:
        # Statistics
        st.header("📈 Statistics")
        
        # Battle info
        st.metric("Target BELM", belm_target.split(" - ")[0])
        st.metric("Battle Mode", mode)
        st.metric("Attack Time", battle_time_str)
        
        # Quick actions
        st.header("🎯 Quick Actions")
        
        if st.button("🔍 Test Connection", use_container_width=True):
            bot_ui.add_log("Testing connection to antrean.logammulia.com...")
            
        if st.button("🔄 Clear Logs", use_container_width=True):
            bot_ui.logs = []
            bot_ui.add_log("Logs cleared")

        # Battle countdown
        if bot_ui.is_running:
            now = datetime.now()
            target_time = datetime.combine(now.date(), battle_time)
            time_diff = (target_time - now).total_seconds()
            
            if time_diff > 0:
                st.subheader("⏳ Countdown")
                minutes, seconds = divmod(int(time_diff), 60)
                hours, minutes = divmod(minutes, 60)
                st.metric("Time Remaining", f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            else:
                st.metric("Status", "⚡ ATTACKING!")

        # System info
        st.header("🖥️ System Info")
        st.metric("Python Version", sys.version.split()[0])
        st.metric("Log Entries", len(bot_ui.logs))
        st.metric("Active Threads", threading.active_count())

    # Auto-refresh mechanism
    if bot_ui.is_running:
        # Auto refresh setiap 3 detik ketika bot running
        time.sleep(3)
        st.rerun()
    else:
        # Refresh setiap 5 detik ketika idle untuk update status stop
        time.sleep(5)
        st.rerun()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        🚀 ANTAM BOT - Built for Speed | ⚡ Ultimate Battle Edition
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
