import os
import logging
import time
import json
import requests
import sys
import uuid
import signal
import threading
import msvcrt  # For file locking (Windows)
import pystray
from pystray import MenuItem as item  # Tray Icon
from PIL import Image, ImageDraw
from datetime import datetime
from cryptography.fernet import Fernet
import tkinter as tk
from tkinter import simpledialog

# -----------------------------------------------------------------------------
# Logging setup
log_folder = "logs"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

log_filename = os.path.join(log_folder, f"authen_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

logging.basicConfig(
    filename=log_filename,
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Tkinter Password Prompt
def ask_password():
    # Create a hidden Tkinter root window
    root = tk.Tk()
    root.withdraw()
    # Ask for the password via a pop-up dialog
    password = simpledialog.askstring("Password", "Enter your password:", show='*')
    root.destroy()
    if not password:
        logging.error("No password provided. Exiting.")
        sys.exit(1)
    return password.encode()

# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Generate Encryption Key and Encrypt Password if Files Do Not Exist
def generate_key_and_password():
    logging.info("Encryption key or encrypted password not found. Generating new key and encrypting password.")
    try:
        key = Fernet.generate_key()
    except Exception as e:
        logging.error(f"Error generating encryption key: {e}")
        sys.exit(1)
    
    try:
        with open('encryption_key.key', 'wb') as key_file:
            key_file.write(key)
    except IOError as e:
        logging.error(f"Failed to write encryption key file: {e}")
        sys.exit(1)
    
    cipher = Fernet(key)
    
    try:
        password = ask_password()  # Use Tkinter pop-up to ask for the password
    except Exception as e:
        logging.error(f"Error obtaining password: {e}")
        sys.exit(1)
    
    try:
        encrypted_password = cipher.encrypt(password)
    except Exception as e:
        logging.error(f"Encryption failed: {e}")
        sys.exit(1)
    
    try:
        with open('encrypted_password.txt', 'wb') as encrypted_file:
            encrypted_file.write(encrypted_password)
    except IOError as e:
        logging.error(f"Failed to write encrypted password file: {e}")
        sys.exit(1)
    
    logging.info("Encryption complete. Encrypted password saved.")
    return key

# Check if encryption key and encrypted password files exist; if not, generate them.
if not os.path.exists('encryption_key.key') or not os.path.exists('encrypted_password.txt'):
    generate_key_and_password()
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# File Reading 
# Read configuration from config.json
def load_config(file_path):
    try:
        with open(file_path, 'r') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        logging.error(f"Configuration file is not a valid JSON: {file_path}")
        sys.exit(1)

# Read key encryption from encryption_key.key
def load_encryption_key(file_path):
    try:
        with open(file_path, 'rb') as key_file:
            return key_file.read()
    except FileNotFoundError:
        logging.error(f"Encryption key file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error loading encryption key: {e}")
        sys.exit(1)


# Read password from encrypted_password.txt
def load_encrypted_password(file_path):
    try:
        with open(file_path, 'rb') as encrypted_file:
            return encrypted_file.read()
    except FileNotFoundError:
        logging.error(f"Encrypted password file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error loading encrypted password: {e}")
        sys.exit(1)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Load configuration and credentials
config = load_config('config.json')
key = load_encryption_key('encryption_key.key')
encrypted_password = load_encrypted_password('encrypted_password.txt')

# Create decoding key
cipher = Fernet(key)

userName = config['username']
userPass = cipher.decrypt(encrypted_password).decode()
ipAddress = config['ipAddress']
server_url = config['server_url']
acip = config['acip']
server_url_heartbeat = config['server_url_heartbeat']
operationsystem = config['os']
connection_check_interval = config['time_repeat'] # Time interval between connection_check in seconds
heartbeat_interval = config['heartbeat_interval'] # Time interval between heartbeats in seconds
max_login_attempt = config['max_login_attempt']
session_duration = config['session_duration']  # 8 hours = 28800 seconds
umac = ''.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1])
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Session tracking 
login_time = None
login_attempts = 0
login_attempts_lock = threading.Lock()  # Lock for thread-safe access
agent = requests.session()

def increment_login_attempts():
    global login_attempts
    with login_attempts_lock:
        login_attempts += 1

def reset_login_attempts():
    global login_attempts
    with login_attempts_lock:
        login_attempts = 0

def get_login_attempts():
    with login_attempts_lock:
        return login_attempts
#------------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Function to monitor network connection 
def check_connection():
    # Ping an external URL to check internet connectivity
    try:
        content = requests.get('http://detectportal.firefox.com/success.txt', timeout=5)
    except requests.exceptions.RequestException:
        return False, False
    if content.text == 'success\n':
        return True, True
    
    return True, False
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Login Function
def login():
    global login_time
    logging.info(f"Attempting login with username -> {userName}")
    try:
        url = server_url
        connection, internet = check_connection()

         # Send login request
        content = agent.post(url, params={
            'userName': userName,
            'userPass': userPass,
            'uaddress': ipAddress,
            'umac': umac,
            'agreed': 1,
            'acip': acip,
            'authType': 1
            })
        
        content_dict = json.loads(content.text)
        data = content_dict['data']

        if content.status_code != 200:
            logging.warning('Error! Something went wrong (maybe wrong username and/or password?)...')
            return False

    except requests.exceptions.RequestException:
        logging.warning(f'Connection lost... ')
        return False
    
    time.sleep(5)  
    connection, internet = check_connection()
    if connection and internet:
        logging.info(f"Login successful at {datetime.now()}: {data}")
        login_time = datetime.now()  # Record login time
        reset_login_attempts()  # Reset login attempts
        return True
    else:
        logging.warning(f"Login failed: {data}")
        increment_login_attempts()
        return False
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Force Re-login
def force_relogin(icon, item):
    logging.info("Force re-login initiated from system tray")
    def relogin_loop():
        while True:
            if login():
                logging.info("Force re-login successful")
                break
            else:
                logging.warning("Force re-login attempt failed, retrying in 5 seconds...")
                time.sleep(5)
    threading.Thread(target=relogin_loop, daemon=True).start()

# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Heartbeat
stop_threads = threading.Event()

def heartbeat():
    try:
        content = agent.post(server_url_heartbeat, params={
            'username': userName,
            'os': operationsystem,
            'speed': 1.29,
            'newauth': 1
        })
    except requests.exceptions.RequestException:
        logging.warning('Connection lost during heartbeat...')
        return False, False
    if  content.status_code == 200:
        logging.info('Heartbeat OK...')
        return True, True
    else:
        logging.warning('Heartbeat failed, checking if session expired...')
        return True, False
    
def heartbeat_loop(heartbeat_interval):
    while not stop_threads.is_set():
        heartbeat()
        time.sleep(heartbeat_interval)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Main Authentication Loop
def start_authentication():
    login_success = login()
    heartbeat_thread = threading.Thread(target=heartbeat_loop, args=(heartbeat_interval,), daemon=True)
    heartbeat_thread.start()
    while not stop_threads.is_set():
        connection, internet = check_connection()
        # Check if the internet is connected
        if connection and internet :
            time.sleep(connection_check_interval)
        else:
            if not login_success:  # Only increment on repeated failures
                increment_login_attempts()

            if get_login_attempts() > max_login_attempt:
                logging.warning("Max login attempts exceeded. Retrying after a delay (30s)...")
                time.sleep(30)
                reset_login_attempts()

            logging.info(f"Internet lost, Retrying login (attempt {get_login_attempts()})")
            login_success = login()  # Retry login immediately
            time.sleep(5)      
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Lock File for Single Instance (Windows)
lock_file = "authen_script.lock"

def acquire_lock():
    global lock
    lock = open(lock_file, "w")
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        logging.info("Lock acquired, starting the script")
    except IOError:
        logging.error("Another instance of the script is already running.")
        sys.exit(0)

def release_lock():
    global lock
    try:
        if lock:
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            lock.close()
            lock = None
            os.remove(lock_file)
            logging.info("Lock released and file closed successfully.")
        else:
            logging.warning("Lock file is already closed or not initialized.")
    except Exception as e:
        logging.error(f"Failed to release lock: {e}")
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Signal handler for performing cleanup tasks and graceful shutdown 
def signal_handler(signal, frame):
    stop_threads.set()  # Signal threads to stop
    release_lock()
    logging.info('Goodbye!')
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# System Tray Functions
def create_image():
    image = Image.new('RGB', (64, 64), "black")
    d = ImageDraw.Draw(image)
    d.rectangle((0, 32, 64, 64), fill="white")
    return image

def open_log_file(icon, item):
    try:
        # Get the list of log files in the log_folder
        log_files = [f for f in os.listdir(log_folder) if f.startswith("authen_log_") and f.endswith(".txt")]
        
        if not log_files:
            logging.error("No log files found.")
            return

        # Sort the log files by modification time to get the latest one
        log_files.sort(key=lambda f: os.path.getmtime(os.path.join(log_folder, f)), reverse=True)
        latest_log_file = os.path.join(log_folder, log_files[0])

        # Open the latest log file based on the operating system
        if sys.platform.startswith('win32'):
            os.startfile(latest_log_file)
        else:
            logging.error("Unsupported OS. Cannot open log file.")

    except Exception as e:
        logging.error(f"Failed to open log file: {e}")

def on_quit(icon, item):
    logging.info("Exiting the system tray icon")
    stop_threads.set()  # Signal threads to stop
    release_lock()
    icon.stop()

def run_authen():
    logging.info("Starting authentication loop")
    start_authentication()

# Start authentication in a separate thread
authen_thread = threading.Thread(target=run_authen)
authen_thread.daemon = True
authen_thread.start()

# System tray icon setup
def run_system_tray():
    icon = pystray.Icon("Authen Script")
    icon.icon = create_image()
    icon.menu = pystray.Menu(
        item('Force Re-login',force_relogin),
        item('Open Logs', open_log_file),
        item('Quit', on_quit)
    )
    icon.title = "Auto Authentication Service"
    icon.run()

try:
    acquire_lock()
    run_system_tray()
except Exception as e:
    logging.error(f"Critical error: {e}")
    release_lock()
    sys.exit(1)
# -----------------------------------------------------------------------------
