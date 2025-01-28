
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
from pystray import MenuItem as item # Stray Icon
from PIL import Image, ImageDraw
from datetime import datetime, timedelta
from cryptography.fernet import Fernet # Key Encryption

# Key Encryption -----------------------------------------------------------------------------
# Read configuration from config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Read key encryption from encryption_key.key
with open('encryption_key.key', 'rb') as key_file:
    key = key_file.read()
# Create decoding key
cipher = Fernet(key)

# Read password from encrypted_password.txt
with open('encrypted_password.txt', 'rb') as encrypted_file:
    encrypted_password = encrypted_file.read()
#----------------------------------------------------------------------------------------------


# Load IP address and URLs from config.json ---------------------------------------------------
userName = config['username']
userPass = cipher.decrypt(encrypted_password).decode()
ipAddress = config['ipAddress']
server_url = config['server_url']
acip = config['acip']
server_url_heartbeat = config['server_url_heartbeat']
time_repeat = config['time_repeat']  # Time interval between heartbeats in seconds
max_login_attempt = config['max_login_attempt']
session_duration = config['session_duration']  # 8 hours = 28800 seconds
umac = ''.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1])
#----------------------------------------------------------------------------------------------


# Logging setup -------------------------------------------------------------------------------
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
#----------------------------------------------------------------------------------------------


# Session tracking variables ------------------------------------------------------------------
login_time = None
login_attempts = 0
agent = requests.session()
#----------------------------------------------------------------------------------------------


# Function to monitor network connection ------------------------------------------------------
def check_connection():
    # Ping an external URL to check internet connectivity
    try:
        content = requests.get('http://detectportal.firefox.com/success.txt', timeout=5)
    except requests.exceptions.RequestException:
        return False, False
    if content.text == 'success\n':
        return True, True
    
    return True, False
#----------------------------------------------------------------------------------------------


# Request to login ----------------------------------------------------------------------------
def login():
    global login_time, login_attempts
    logging.info(f"Attempting login with username -> {userName}")
    try:
        url = server_url
        connection, internet = check_connection()

         # Send login request
        content = agent.post(url, params={'userName': userName,
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

    except requests.exceptions.RequestException:
        logging.warning(f'Connection lost... ')
        login_attempts += 1
        return  # Exit the function early on connection failure
    
    time.sleep(4)  
    connection, internet = check_connection()
    if connection and internet:
        logging.info(f"Login successful at {datetime.now()}: {data}")
        login_time = datetime.now()  # Record login time
        login_attempts = 0  # Reset login attempts
    else:
        logging.warning(f"Login failed: {data}")
        login_attempts += 1
#----------------------------------------------------------------------------------------------


# Function to send a heartbeat request to keep the session alive ------------------------------
def heartbeat():
    global login_attempts
    try:
        content = agent.post(server_url_heartbeat, params={
            'username': userName,
            'os': "Windows 10 Home 64-bit",
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
#----------------------------------------------------------------------------------------------    


# main authen loop ----------------------------------------------------------------------------
def start_authentication():
    global login_attempts
    login_attempts = 0
    login()
    while True:
        connection, internet = check_connection()
        # Check if the internet is connected
        if connection and internet :
            heartbeat()  # Send heartbeat
            time.sleep(time_repeat)
        else:
            if login_attempts > max_login_attempt:
                logging.warning("Max login attempts exceeded")
                time.sleep(60)
                logging.warning("Start trying again...")
                login_attempts = 0
            logging.info(f"Internet lost, attempting to login... {login_attempts}")
            login()    # Immediately log in if the connection or internet are lost
            time.sleep(5)           
#----------------------------------------------------------------------------------------------


# Lock file location (Windows) ----------------------------------------------------------------
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
#----------------------------------------------------------------------------------------------


# Signal handler for performing cleanup tasks and graceful shutdown ---------------------------
def signal_handler(signal, frame):
    release_lock()
    logging.info('Goodbye!')
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)

acquire_lock()
#----------------------------------------------------------------------------------------------


# System Tray Functions -----------------------------------------------------------------------
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
    release_lock()
    icon.stop()

def run_authen():
    logging.info("Starting authentication loop")
    start_authentication()
#----------------------------------------------------------------------------------------------


# Start authentication in a separate thread ---------------------------------------------------
authen_thread = threading.Thread(target=run_authen)
authen_thread.daemon = True
authen_thread.start()
#----------------------------------------------------------------------------------------------


# System tray icon setup ----------------------------------------------------------------------
def run_system_tray():
    icon = pystray.Icon("Authen Script")
    icon.icon = create_image()
    icon.menu = pystray.Menu(
        item('Open Logs', open_log_file),
        item('Quit', on_quit)
    )
    icon.title = "Auto Authentication Service"
    icon.run()

run_system_tray()
#----------------------------------------------------------------------------------------------
