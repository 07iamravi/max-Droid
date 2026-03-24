#!/usr/bin/env python3
"""
max-Droid – Android Management Framework
Author: 07iamravi (Rabi Kishan Rauniyar)
Description: **max-Droid** is a feature‑rich Android management framework that wraps ADB into a sleek, interactive terminal interface.  
It automates device connection, provides comprehensive device, app, file, system, screen, and Wi‑Fi management, and includes automatic ADB installation and wireless reconnection.
"""

import subprocess
import sys
import os
import time
import re
import configparser
import shutil
import urllib.request
import zipfile
import platform
import signal
from pathlib import Path
from colorama import init, Fore, Style, Back
import pyfiglet
import threading
import json
from queue import Queue
import socket

# Initialize colorama for cross‑platform colored output
init(autoreset=True)

# ----------------------------------------------------------------------
# Color definitions (matching x‑zone style)
# ----------------------------------------------------------------------
RED = Fore.RED
GREEN = Fore.GREEN
PINK = Fore.MAGENTA
BLUE = Fore.BLUE
MAGENTA = Fore.MAGENTA
CYAN = Fore.CYAN
WHITE = Fore.WHITE
BLACK = Fore.BLACK
YELLOW = Fore.YELLOW

# Background colors (for special messages)
REDBG = Back.RED
GREENBG = Back.GREEN
PINKBG = Back.MAGENTA
BLUEBG = Back.BLUE
MAGENTABG = Back.MAGENTA
CYANBG = Back.CYAN
WHITEBG = Back.WHITE
BLACKBG = Back.BLACK

RESET = Style.RESET_ALL

# ----------------------------------------------------------------------
# Configuration & Global Variables
# ----------------------------------------------------------------------
CONFIG_FILE = Path.home() / ".maxdroid.conf"
ADB_PATH = "adb"
SCRCPY_PATH = None
SCRCPY_DIR = None
DEFAULT_PORT = 5555
AUTO_TCPIP = True
TCPIP_PORT = DEFAULT_PORT
VERSION = "2.0"
DEVICE_DB = Path.home() / ".maxdroid_devices.json"
DEVICE_NAMES = {}
EVENT_QUEUE = Queue()
RUN_WATCHER = True

# ===================== DEVICE DB =====================
def load_devices_db():
    global DEVICE_NAMES
    if DEVICE_DB.exists():
        with open(DEVICE_DB, "r") as f:
            DEVICE_NAMES = json.load(f)

def save_devices_db():
    with open(DEVICE_DB, "w") as f:
        json.dump(DEVICE_NAMES, f, indent=2)

load_devices_db()

# ===================== NICKNAME SYSTEM =====================
def set_device_name(serial):
    name = input(f"{CYAN}Enter nickname: {RESET}").strip()
    if name:
        DEVICE_NAMES[serial] = name
        save_devices_db()
        print(f"{GREEN}Saved nickname.{RESET}")

def get_device_name(serial):
    return DEVICE_NAMES.get(serial, "Unknown")

# ===================== ASYNC ADB =====================
def run_adb_async(cmd, device=None):
    def worker():
        out = run_adb_command(cmd, device)
        EVENT_QUEUE.put(out)
    threading.Thread(target=worker, daemon=True).start()

# ===================== AUTO RECONNECT (improved) =====================
def wait_for_device_status(serial, expected_status='device', timeout=5):
    """Wait up to `timeout` seconds for the device to reach `expected_status`."""
    start = time.time()
    while time.time() - start < timeout:
        devices = list_devices()
        for s, status in devices:
            if s == serial and status == expected_status:
                return True
        time.sleep(0.5)
    return False

def auto_reconnect_saved():
    """Attempt to reconnect saved wireless devices. Returns list of successfully reconnected serials."""
    print(f"{CYAN}Checking saved devices...{RESET}")
    reconnected = []
    for serial in DEVICE_NAMES.keys():
        if ":" in serial:
            out = run_adb_command(f"connect {serial}")
            if "connected" in out.lower() or "already" in out.lower():
                if wait_for_device_status(serial, 'device', timeout=5):
                    print(f"{GREEN}Reconnected → {serial}{RESET}")
                    reconnected.append(serial)
                else:
                    print(f"{YELLOW}Device {serial} connected but not ready (status may be offline).{RESET}")
            else:
                print(f"{RED}Failed to connect to {serial}{RESET}")
    return reconnected

# ===================== DEVICE WATCHER =====================
def device_watcher():
    known = set()
    while RUN_WATCHER:
        devices = list_devices()
        current = set([d for d, s in devices if s == "device"])
        for d in current - known:
            EVENT_QUEUE.put(f"[+] Device connected: {d}")
        for d in known - current:
            EVENT_QUEUE.put(f"[-] Device disconnected: {d}")
        known = current
        time.sleep(3)

# ===================== DASHBOARD =====================
def dashboard():
    os.system("cls" if os.name == "nt" else "clear")
    print(CYAN + pyfiglet.figlet_format("max-Droid", font="small"))
    print(GREEN + "Live Device Dashboard\n")
    devices = list_devices()
    for serial, status in devices:
        name = get_device_name(serial)
        if ":" not in serial:
            ip = get_device_ip(serial)
        else:
            ip = serial
        print(f"{YELLOW}{name}{RESET} → {serial} ({status})")
        if ip:
            print(f"   IP: {ip}")
    print("\nEvents:")
    while not EVENT_QUEUE.empty():
        print(EVENT_QUEUE.get())

def load_config():
    global AUTO_TCPIP, TCPIP_PORT
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE)
        if "Settings" in config:
            AUTO_TCPIP = config.getboolean("Settings", "auto_tcpip", fallback=True)
            TCPIP_PORT = config.getint("Settings", "tcpip_port", fallback=DEFAULT_PORT)
    else:
        config["Settings"] = {
            "auto_tcpip": str(AUTO_TCPIP),
            "tcpip_port": str(TCPIP_PORT)
        }
        with open(CONFIG_FILE, "w") as f:
            config.write(f)

def save_config():
    config = configparser.ConfigParser()
    config["Settings"] = {
        "auto_tcpip": str(AUTO_TCPIP),
        "tcpip_port": str(TCPIP_PORT)
    }
    with open(CONFIG_FILE, "w") as f:
        config.write(f)

load_config()

# ----------------------------------------------------------------------
# Signal Handling (clean exit)
# ----------------------------------------------------------------------
def exit_on_signal(signum, frame):
    print(f"\n{RED}[{WHITE}!{RED}]{RED} Program Interrupted.{RESET}")
    sys.exit(0)

signal.signal(signal.SIGINT, exit_on_signal)
signal.signal(signal.SIGTERM, exit_on_signal)

# ----------------------------------------------------------------------
# Utility Functions (ADB helpers, etc.)
# ----------------------------------------------------------------------
def print_banner():
    banner = pyfiglet.figlet_format("max-Droid", font="slant")
    print(CYAN + banner)
    print(YELLOW + "Android Management Framework")
    print(f"{GREEN}[{WHITE}-{GREEN}] {CYAN}github.com/07iamravi{RESET}")
    print(f"{GREEN}[{WHITE}-{GREEN}] {YELLOW}Advanced Android Control Suite{RESET}\n")
    print(f"\n{REDBG}{WHITE} ⚠️  FOR EDUCATIONAL PURPOSES ONLY  ⚠️ {RESET}")
    print(f"{YELLOW}Authorized use only. Misuse may violate laws and regulations.")
    print(f"{MAGENTA}>> Stay ethical, stay curious <<{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")

def banner_small():
    small = pyfiglet.figlet_format("max-Droid", font="small")
    print(CYAN + small + RESET)

def reset_color():
    print(RESET, end="")

def run_adb_command(cmd, device=None):
    full_cmd = [ADB_PATH]
    if device:
        full_cmd.extend(["-s", device])
    full_cmd.extend(cmd.split())
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"{RED}Error: {e.stderr.strip()}{RESET}"
    except FileNotFoundError:
        return f"{RED}ADB not found at {ADB_PATH}. Please check your installation.{RESET}"

def list_devices():
    """Returns a list of tuples (serial, status) from 'adb devices'."""
    out = run_adb_command("devices")
    devices = []
    for line in out.splitlines():
        if line and not line.startswith("List of devices attached"):
            parts = line.split()
            if len(parts) >= 2:
                serial, status = parts[0], parts[1]
                devices.append((serial, status))
    return devices

def device_list():
    devices = list_devices()
    if not devices:
        print(f"{YELLOW}No devices attached.{RESET}")
        return
    for serial, status in devices:
        name = get_device_name(serial)
        label = f"{name} ({serial})" if name != "Unknown" else serial
        if ":" not in serial and status == "device":
            ip = get_device_ip(serial)
            print(f"{GREEN}{label}{RESET} → {status} | IP: {ip}")
        else:
            print(f"{GREEN}{label}{RESET} → {status}")

def get_device_ip(serial):
    ip_output = run_adb_command("shell ip -f inet addr show wlan0", serial)
    if "Error" in ip_output:
        ip_output = run_adb_command("shell ip -f inet addr", serial)
    for line in ip_output.splitlines():
        if "inet " in line and "127.0.0.1" not in line:
            parts = line.strip().split()
            for part in parts:
                if part.startswith("inet"):
                    ip = parts[parts.index(part) + 1].split('/')[0]
                    return ip
    return None

def select_device():
    devices = list_devices()
    if not devices:
        print(f"{RED}No devices connected.{RESET}")
        return None
    if len(devices) == 1:
        serial, status = devices[0]
        if status == "device":
            print(f"{GREEN}Using device: {serial}{RESET}")
            return serial
        else:
            print(f"{RED}Device {serial} is {status}. Please check.{RESET}")
            return None
    else:
        print(f"{YELLOW}Multiple devices found:{RESET}")
        for i, (serial, status) in enumerate(devices, 1):
            print(f"{i}. {serial} ({status})")
        choice = input(f"{CYAN}Select device number: {RESET}").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(devices):
                serial, status = devices[idx]
                if status == "device":
                    return serial
                else:
                    print(f"{RED}Device {serial} is {status}.{RESET}")
                    return None
            else:
                print(f"{RED}Invalid selection.{RESET}")
                return None
        except ValueError:
            print(f"{RED}Invalid input.{RESET}")
            return None

def wait_for_adb():
    run_adb_command("start-server")

# ----------------------------------------------------------------------
# ADB Installation & Auto‑Setup
# ----------------------------------------------------------------------
def is_adb_available():
    adb_path = shutil.which("adb")
    if adb_path:
        return adb_path
    home = Path.home()
    common_paths = [
        home / "Android/Sdk/platform-tools/adb",
        home / "AppData/Local/Android/Sdk/platform-tools/adb.exe",
        home / ".maxdroid/platform-tools/adb",
        home / ".maxdroid/platform-tools/adb.exe",
    ]
    for path in common_paths:
        if path.exists():
            return str(path)
    return None

def download_and_extract_platform_tools():
    system = platform.system().lower()
    if system == "windows":
        url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
        adb_name = "adb.exe"
    elif system == "linux":
        url = "https://dl.google.com/android/repository/platform-tools-latest-linux.zip"
        adb_name = "adb"
    elif system == "darwin":
        url = "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip"
        adb_name = "adb"
    else:
        print(f"{RED}Unsupported OS: {system}. Please install ADB manually.{RESET}")
        return None

    dest_dir = Path.home() / ".maxdroid/platform-tools"
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "platform-tools.zip"

    print(f"{CYAN}Downloading platform-tools from Google...{RESET}")
    try:
        urllib.request.urlretrieve(url, zip_path)
    except Exception as e:
        print(f"{RED}Download failed: {e}{RESET}")
        return None

    print(f"{CYAN}Extracting...{RESET}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        zip_path.unlink()
        extracted_dir = dest_dir / "platform-tools"
        if extracted_dir.exists():
            for item in extracted_dir.iterdir():
                shutil.move(str(item), str(dest_dir / item.name))
            extracted_dir.rmdir()
        adb_path = dest_dir / adb_name
        if adb_path.exists():
            adb_path.chmod(0o755)
            return str(adb_path)
        else:
            print(f"{RED}Extraction completed but adb not found.{RESET}")
            return None
    except Exception as e:
        print(f"{RED}Extraction failed: {e}{RESET}")
        return None

def ensure_adb():
    global ADB_PATH
    adb = is_adb_available()
    if adb:
        ADB_PATH = adb
        # Silent – no print
        return True

    print(f"{YELLOW}\nADB is not installed or not in PATH.{RESET}")
    print("Without ADB, max-Droid cannot communicate with your device.")
    print("\nOptions:")
    print("1. Automatically download and set up ADB (recommended)")
    print("2. Show manual installation instructions and exit")
    print("3. Exit")
    choice = input(f"{CYAN}Choose option: {RESET}").strip()

    if choice == "1":
        print(f"{CYAN}Attempting to download ADB...{RESET}")
        adb_path = download_and_extract_platform_tools()
        if adb_path:
            ADB_PATH = adb_path
            print(f"{GREEN}ADB successfully set up at: {ADB_PATH}{RESET}")
            return True
        else:
            print(f"{RED}Automatic setup failed. Please install ADB manually.{RESET}")
            show_adb_installation_help()
            return False
    elif choice == "2":
        show_adb_installation_help()
        return False
    else:
        return False

def show_adb_installation_help():
    system = platform.system().lower()
    print(f"{YELLOW}\n=== Manual ADB Installation ==={RESET}")
    if system == "windows":
        print("1. Download the Android SDK Platform-Tools from:")
        print("   https://developer.android.com/studio/releases/platform-tools")
        print("2. Extract the zip and place the folder in a permanent location.")
        print("3. Add the folder containing 'adb.exe' to your system PATH.")
        print("4. Restart your terminal and run this script again.")
    elif system == "linux":
        print("You can install ADB using your package manager:")
        print("  - Debian/Ubuntu: sudo apt install adb")
        print("  - Fedora: sudo dnf install android-tools")
        print("  - Arch: sudo pacman -S android-tools")
        print("After installation, make sure 'adb' is in your PATH.")
    elif system == "darwin":
        print("You can install ADB using Homebrew:")
        print("  brew install android-platform-tools")
        print("If you don't have Homebrew, install it from https://brew.sh/")
    else:
        print("Please download the Android SDK Platform-Tools from:")
        print("https://developer.android.com/studio/releases/platform-tools")
        print("and ensure 'adb' is in your PATH.")
    print("\nAfter installing, run this script again.")

# ----------------------------------------------------------------------
# scrcpy Installation Check & Auto‑Setup
# ----------------------------------------------------------------------
def is_scrcpy_available():
    scrcpy_path = shutil.which("scrcpy")
    if scrcpy_path:
        return scrcpy_path, None
    home = Path.home()
    base_dir = home / ".maxdroid/scrcpy"
    if base_dir.exists():
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file == "scrcpy" or file == "scrcpy.exe":
                    return str(Path(root) / file), str(Path(root))
    return None, None

def download_and_setup_scrcpy():
    system = platform.system().lower()
    if system == "windows":
        url = "https://github.com/Genymobile/scrcpy/releases/download/v2.7/scrcpy-win64-v2.7.zip"
        dest_dir = Path.home() / ".maxdroid/scrcpy"
    elif system == "linux":
        url = "https://github.com/Genymobile/scrcpy/releases/download/v2.7/scrcpy-linux-x86_64-v2.7.tar.gz"
        dest_dir = Path.home() / ".maxdroid/scrcpy"
    elif system == "darwin":
        url = "https://github.com/Genymobile/scrcpy/releases/download/v2.7/scrcpy-macos-v2.7.tar.gz"
        dest_dir = Path.home() / ".maxdroid/scrcpy"
    else:
        print(f"{RED}Unsupported OS: {system}. Please install scrcpy manually.{RESET}")
        return None, None

    dest_dir.mkdir(parents=True, exist_ok=True)
    archive_path = dest_dir / ("scrcpy.zip" if url.endswith(".zip") else "scrcpy.tar.gz")

    print(f"{CYAN}Downloading scrcpy from GitHub...{RESET}")
    try:
        urllib.request.urlretrieve(url, archive_path)
    except Exception as e:
        print(f"{RED}Download failed: {e}{RESET}")
        return None, None

    print(f"{CYAN}Extracting...{RESET}")
    try:
        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)
        else:
            import tarfile
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                tar_ref.extractall(dest_dir)
        archive_path.unlink()

        exe_path = None
        exe_dir = None
        for root, dirs, files in os.walk(dest_dir):
            for file in files:
                if file == "scrcpy" or file == "scrcpy.exe":
                    exe_path = Path(root) / file
                    exe_dir = Path(root)
                    break
            if exe_path:
                break
        if exe_path:
            exe_path.chmod(0o755)
            return str(exe_path), str(exe_dir)
        else:
            print(f"{RED}Could not find scrcpy executable after extraction.{RESET}")
            return None, None
    except Exception as e:
        print(f"{RED}Extraction failed: {e}{RESET}")
        return None, None

def ensure_scrcpy():
    global SCRCPY_PATH, SCRCPY_DIR
    scrcpy_path, scrcpy_dir = is_scrcpy_available()
    if scrcpy_path:
        SCRCPY_PATH = scrcpy_path
        SCRCPY_DIR = scrcpy_dir
        # Silent – no print
        return True

    print(f"{YELLOW}\nscrcpy is not installed or not in PATH.{RESET}")
    print("Without scrcpy, screen sharing functions will not work.")
    print("\nOptions:")
    print("1. Automatically download and set up scrcpy (recommended)")
    print("2. Show manual installation instructions and continue without scrcpy")
    print("3. Exit")
    choice = input(f"{CYAN}Choose option: {RESET}").strip()

    if choice == "1":
        print(f"{CYAN}Attempting to download scrcpy...{RESET}")
        scrcpy_path, scrcpy_dir = download_and_setup_scrcpy()
        if scrcpy_path:
            SCRCPY_PATH = scrcpy_path
            SCRCPY_DIR = scrcpy_dir
            print(f"{GREEN}scrcpy successfully set up at: {SCRCPY_PATH}{RESET}")
            return True
        else:
            print(f"{RED}Automatic setup failed. Please install scrcpy manually.{RESET}")
            show_scrcpy_installation_help()
            return False
    elif choice == "2":
        show_scrcpy_installation_help()
        return False
    else:
        sys.exit(0)

def show_scrcpy_installation_help():
    system = platform.system().lower()
    print(f"{YELLOW}\n=== Manual scrcpy Installation ==={RESET}")
    print("scrcpy is available at: https://github.com/Genymobile/scrcpy")
    if system == "windows":
        print("1. Download the latest Windows release from the GitHub page.")
        print("2. Extract the zip to a folder, e.g., C:\\scrcpy.")
        print("3. Add that folder to your system PATH, or run scrcpy from that folder.")
    elif system == "linux":
        print("You can install scrcpy using your package manager:")
        print("  - Debian/Ubuntu: sudo apt install scrcpy")
        print("  - Fedora: sudo dnf install scrcpy")
        print("  - Arch: sudo pacman -S scrcpy")
        print("Or download the prebuilt binary from GitHub.")
    elif system == "darwin":
        print("You can install scrcpy using Homebrew:")
        print("  brew install scrcpy")
        print("If you don't have Homebrew, install it from https://brew.sh/")
    else:
        print("Please download scrcpy from https://github.com/Genymobile/scrcpy/releases")
    print("\nAfter installing, restart the script to use screen sharing.")

# ----------------------------------------------------------------------
# Connection & Auto TCP/IP (silent mode)
# ----------------------------------------------------------------------
def wait_for_authorized_device(timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        devices = list_devices()
        for serial, status in devices:
            if status == "device":
                return serial
        unauthorized = [serial for serial, status in devices if status == "unauthorized"]
        if unauthorized:
            print(f"{YELLOW}\nDevice {unauthorized[0]} is UNAUTHORIZED.{RESET}")
            print("Please look at your device screen and accept the RSA fingerprint prompt.")
            print("Check 'Always allow from this computer' and tap OK.\n")
        else:
            print(f"{CYAN}\rWaiting for device... (make sure USB debugging is ON){RESET}", end="")
        time.sleep(2)
    return None

def auto_tcpip(usb_device=None):
    if not usb_device:
        devices = list_devices()
        for serial, status in devices:
            if status == "device" and ":" not in serial:
                usb_device = serial
                break
    if not usb_device:
        return None

    ip = get_device_ip(usb_device)
    if not ip:
        ip = input(f"{CYAN}Please enter device IP: {RESET}").strip()
        if not ip:
            return None

    print(f"{CYAN}Switching {usb_device} to TCP/IP mode...{RESET}")
    res = run_adb_command(f"tcpip {TCPIP_PORT}", usb_device)
    if "Error" in res:
        print(res)
        return None
    time.sleep(3)

    print(f"{CYAN}Connecting to {ip}:{TCPIP_PORT}...{RESET}")
    connect_out = run_adb_command(f"connect {ip}:{TCPIP_PORT}")
    if "connected" in connect_out.lower():
        print(f"{GREEN}Successfully connected to {ip}:{TCPIP_PORT}{RESET}")
        return f"{ip}:{TCPIP_PORT}"
    else:
        print(f"{RED}Connection failed: {connect_out}{RESET}")
        return None

def connect_device_interactive():
    """Minimal connection guide – returns a device serial."""
    run_adb_command("kill-server")
    time.sleep(1)
    run_adb_command("start-server")
    time.sleep(1)

    devices = list_devices()
    if devices:
        unauthorized = [serial for serial, status in devices if status == "unauthorized"]
        if unauthorized:
            print(f"{YELLOW}Device {unauthorized[0]} is UNAUTHORIZED.{RESET}")
            print("Accept the RSA prompt on your device.")
            input("After accepting, press Enter...")
            auth_serial = wait_for_authorized_device(timeout=30)
            if auth_serial:
                return auth_serial
            else:
                print(f"{RED}Device still unauthorized. Exiting.{RESET}")
                sys.exit(1)
        return select_device()

    print(f"{YELLOW}\nNo Android device detected.{RESET}")
    print("How would you like to connect?")
    print("1. Connect via USB cable (recommended for first time)")
    print("2. Connect wirelessly (long range)")
    print("3. Exit")
    choice = input(f"{CYAN}Choose option: {RESET}").strip()

    if choice == "1":
        print(f"{CYAN}\n=== USB Connection Guide ==={RESET}")
        print("1. Enable Developer options (tap Build number 7 times).")
        print("2. Enable USB debugging in Developer options.")
        print("3. Connect your device via USB.")
        print("4. Accept the RSA fingerprint when prompted.\n")
        input("After completing these steps, press Enter to continue...")

        print(f"{CYAN}Looking for a device...{RESET}")
        timeout = 30
        start = time.time()
        device_appeared = False
        while time.time() - start < timeout:
            devices = list_devices()
            if devices:
                device_appeared = True
                break
            time.sleep(2)
            print(".", end="", flush=True)
        if not device_appeared:
            print(f"{RED}\nNo device detected after 30 seconds.{RESET}")
            return None
        print(f"{GREEN}\nDevice detected!{RESET}")

        print(f"{CYAN}Waiting for authorization...{RESET}")
        auth_serial = wait_for_authorized_device(timeout=60)
        if not auth_serial:
            print(f"{RED}Authorization timeout.{RESET}")
            return None

        if AUTO_TCPIP:
            print(f"{CYAN}Switching to wireless mode...{RESET}")
            wireless = auto_tcpip(usb_device=auth_serial)
            if wireless:
                return wireless
            else:
                print(f"{YELLOW}Falling back to USB mode.{RESET}")
                return auth_serial
        else:
            return auth_serial

    elif choice == "2":
        print(f"{CYAN}\n=== Wireless Connection ==={RESET}")
        ip = input(f"{CYAN}Enter device IP: {RESET}").strip()
        if not ip:
            return None
        port = input(f"{CYAN}Enter port (default {TCPIP_PORT}): {RESET}").strip()
        if not port:
            port = TCPIP_PORT
        else:
            port = int(port)
        out = run_adb_command(f"connect {ip}:{port}")
        if "connected" in out.lower():
            print(f"{GREEN}{out}{RESET}")
            return f"{ip}:{port}"
        else:
            print(f"{RED}{out}{RESET}")
            return None
    else:
        sys.exit(0)

# ----------------------------------------------------------------------
# Device Management Functions 
# ----------------------------------------------------------------------
def device_list():
    devices = list_devices()
    if not devices:
        print(f"{YELLOW}No devices attached.{RESET}")
    else:
        print(f"{GREEN}Connected devices:{RESET}")
        for serial, status in devices:
            print(f"  {serial}  ({status})")

def device_connect_wifi():
    ip = input(f"{CYAN}Enter device IP: {RESET}").strip()
    port = input(f"{CYAN}Enter port (default {TCPIP_PORT}): {RESET}").strip()
    if not port:
        port = TCPIP_PORT
    else:
        port = int(port)
    out = run_adb_command(f"connect {ip}:{port}")
    print(out)

def device_restart_adb():
    run_adb_command("kill-server")
    time.sleep(1)
    run_adb_command("start-server")
    print(f"{GREEN}ADB server restarted.{RESET}")

def device_info(device):
    info = {}
    props = ["ro.product.manufacturer", "ro.product.model", "ro.build.version.release", "ro.build.version.sdk"]
    for prop in props:
        val = run_adb_command(f"shell getprop {prop}", device)
        info[prop.split('.')[-1]] = val
    print(f"{GREEN}Device Information:{RESET}")
    print(f"  Manufacturer: {info.get('manufacturer', 'N/A')}")
    print(f"  Model: {info.get('model', 'N/A')}")
    print(f"  Android Version: {info.get('release', 'N/A')} (API {info.get('sdk', 'N/A')})")

def device_shell(device):
    cmd = input(f"{CYAN}Enter shell command: {RESET}").strip()
    if cmd:
        out = run_adb_command(f"shell {cmd}", device)
        print(out)

def device_reboot(device):
    confirm = input(f"{RED}Reboot device? (y/n): {RESET}").strip().lower()
    if confirm == 'y':
        out = run_adb_command("reboot", device)
        print(out)

def device_disconnect(device):
    if ":" in device:
        ip_part = device.split(':')[0]
        out = run_adb_command(f"disconnect {ip_part}")
        print(out)
    else:
        print(f"{YELLOW}USB device cannot be disconnected via ADB; unplug physically.{RESET}")

# ----------------------------------------------------------------------
# App Management Functions
# ----------------------------------------------------------------------
def app_install(device):
    path = input(f"{CYAN}Enter APK path: {RESET}").strip()
    if not os.path.exists(path):
        print(f"{RED}File not found.{RESET}")
        return
    out = run_adb_command(f"install {path}", device)
    print(out)

def app_uninstall(device):
    package = input(f"{CYAN}Enter package name: {RESET}").strip()
    if package:
        out = run_adb_command(f"uninstall {package}", device)
        print(out)

def app_list_packages(device):
    filter_str = input(f"{CYAN}Filter (e.g., 'google'): {RESET}").strip()
    cmd = "shell pm list packages"
    if filter_str:
        cmd += f" | grep {filter_str}"
    out = run_adb_command(cmd, device)
    for line in out.splitlines():
        print(line.replace("package:", ""))

def app_package_info(device):
    package = input(f"{CYAN}Enter package name: {RESET}").strip()
    if package:
        out = run_adb_command(f"shell dumpsys package {package}", device)
        lines = out.splitlines()
        for line in lines[:30]:
            print(line)
        if len(lines) > 30:
            print("... (output truncated)")

def app_clear_data(device):
    package = input(f"{CYAN}Enter package name: {RESET}").strip()
    if package:
        confirm = input(f"{RED}Clear data for {package}? (y/n): {RESET}").strip().lower()
        if confirm == 'y':
            out = run_adb_command(f"shell pm clear {package}", device)
            print(out)

def app_force_stop(device):
    package = input(f"{CYAN}Enter package name: {RESET}").strip()
    if package:
        out = run_adb_command(f"shell am force-stop {package}", device)
        print(out)

def app_start(device):
    package = input(f"{CYAN}Enter package name: {RESET}").strip()
    if package:
        out = run_adb_command(f"shell cmd package resolve-activity --brief {package} | tail -n 1", device)
        activity = out.strip()
        if activity and not "Error" in activity:
            run_adb_command(f"shell am start -n {activity}", device)
            print(f"{GREEN}Started {activity}{RESET}")
        else:
            print(f"{RED}Could not determine launch activity.{RESET}")

def app_backup(device):
    package = input(f"{CYAN}Enter package name: {RESET}").strip()
    if package:
        outfile = input(f"{CYAN}Output file name (default: backup.ab): {RESET}").strip()
        if not outfile:
            outfile = "backup.ab"
        cmd = f"backup -f {outfile} -apk -shared -all -system {package}"
        out = run_adb_command(cmd, device)
        print(out)

def app_batch_install(device):
    folder = input(f"{CYAN}Enter folder containing APK files: {RESET}").strip()
    if not os.path.isdir(folder):
        print(f"{RED}Folder not found.{RESET}")
        return
    apks = [f for f in os.listdir(folder) if f.endswith('.apk')]
    if not apks:
        print(f"{YELLOW}No APK files found.{RESET}")
        return
    print(f"{YELLOW}Found {len(apks)} APKs. Installing...{RESET}")
    for apk in apks:
        path = os.path.join(folder, apk)
        print(f"Installing {apk}...")
        out = run_adb_command(f"install {path}", device)
        print(out)

# ----------------------------------------------------------------------
# File Operations
# ----------------------------------------------------------------------
def file_take_screenshot(device):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    local_file = f"screenshot_{timestamp}.png"
    remote_path = "/sdcard/screen.png"
    run_adb_command(f"shell screencap {remote_path}", device)
    run_adb_command(f"pull {remote_path} {local_file}", device)
    run_adb_command(f"shell rm {remote_path}", device)
    print(f"{GREEN}Screenshot saved as {local_file}{RESET}")

def file_multiple_screenshot(device):
    count = input(f"{CYAN}Number of screenshots: {RESET}").strip()
    try:
        count = int(count)
    except:
        print(f"{RED}Invalid number.{RESET}")
        return
    delay = input(f"{CYAN}Delay between shots (seconds): {RESET}").strip()
    try:
        delay = float(delay)
    except:
        delay = 2.0
    for i in range(count):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        local_file = f"screenshot_{timestamp}_{i+1}.png"
        remote_path = f"/sdcard/screen_{i+1}.png"
        run_adb_command(f"shell screencap {remote_path}", device)
        run_adb_command(f"pull {remote_path} {local_file}", device)
        run_adb_command(f"shell rm {remote_path}", device)
        print(f"Saved {local_file}")
        if i < count-1:
            time.sleep(delay)

def file_upload(device):
    local = input(f"{CYAN}Local file path: {RESET}").strip()
    remote = input(f"{CYAN}Remote destination (e.g., /sdcard/): {RESET}").strip()
    if not remote:
        remote = "/sdcard/"
    if not os.path.exists(local):
        print(f"{RED}File not found.{RESET}")
        return
    out = run_adb_command(f"push {local} {remote}", device)
    print(out)

def file_download(device):
    remote = input(f"{CYAN}Remote file path: {RESET}").strip()
    local = input(f"{CYAN}Local destination: {RESET}").strip()
    if not local:
        local = "."
    out = run_adb_command(f"pull {remote} {local}", device)
    print(out)

def file_list(device):
    path = input(f"{CYAN}Directory path (default /sdcard): {RESET}").strip()
    if not path:
        path = "/sdcard"
    out = run_adb_command(f"shell ls -la {path}", device)
    print(out)

def file_create_folder(device):
    path = input(f"{CYAN}Full path of new folder: {RESET}").strip()
    if path:
        out = run_adb_command(f"shell mkdir {path}", device)
        print(out)

def file_delete(device):
    path = input(f"{CYAN}File or folder to delete: {RESET}").strip()
    if path:
        confirm = input(f"{RED}Delete {path}? (y/n): {RESET}").strip().lower()
        if confirm == 'y':
            out = run_adb_command(f"shell rm -rf {path}", device)
            print(out)

def file_backup_folder(device):
    remote_folder = input(f"{CYAN}Remote folder path: {RESET}").strip()
    local_dest = input(f"{CYAN}Local destination folder: {RESET}").strip()
    if not local_dest:
        local_dest = "."
    if not remote_folder:
        print(f"{RED}No remote folder specified.{RESET}")
        return
    out = run_adb_command(f"pull {remote_folder} {local_dest}", device)
    print(out)

# ----------------------------------------------------------------------
# System Monitoring
# ----------------------------------------------------------------------
def sys_battery(device):
    out = run_adb_command("shell dumpsys battery", device)
    print(out)

def sys_memory(device):
    out = run_adb_command("shell dumpsys meminfo", device)
    for line in out.splitlines():
        if "Total RAM" in line or "Free RAM" in line or "Used RAM" in line:
            print(line)

def sys_cpu(device):
    out = run_adb_command("shell top -n 1 -d 1", device)
    print(out[:1000])

def sys_storage(device):
    out = run_adb_command("shell df -h", device)
    print(out)

def sys_processes(device):
    out = run_adb_command("shell ps", device)
    print(out)

def sys_network(device):
    out = run_adb_command("shell netstat", device)
    print(out)

def sys_properties(device):
    out = run_adb_command("shell getprop", device)
    print(out)

def sys_apps_with_size(device):
    out = run_adb_command("shell pm list packages -f", device)
    for line in out.splitlines():
        if "package:" in line:
            pkg = line.split('=')[-1]
            print(pkg)

def sys_monitor_performance(device):
    print(f"{YELLOW}Monitoring CPU/memory (Ctrl+C to stop){RESET}")
    try:
        while True:
            subprocess.call([ADB_PATH, "-s", device, "shell", "top", "-n", "1", "-d", "1"])
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

# ----------------------------------------------------------------------
# Screen Sharing & Recording (with audio option)
# ----------------------------------------------------------------------
def launch_scrcpy(device, extra_args=None):
    if not ensure_scrcpy():
        return False

    
    try:
        test_cmd = [SCRCPY_PATH, "--version"]
        subprocess.run(test_cmd, capture_output=True, check=True, timeout=5)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"{RED}scrcpy is not working properly: {e}{RESET}")
        return False

    cmd = [SCRCPY_PATH, "-s", device]
    if extra_args:
        cmd.extend(extra_args.split())

    env = os.environ.copy()
    adb_dir = os.path.dirname(ADB_PATH)
    if adb_dir:
        env["PATH"] = adb_dir + os.pathsep + env.get("PATH", "")
    cwd = SCRCPY_DIR if SCRCPY_DIR else None

    try:
        # Launch with output suppressed to keep the terminal clean
        subprocess.Popen(cmd, env=env, cwd=cwd,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{GREEN}Starting screen sharing...{RESET}")
        return True
    except Exception as e:
        print(f"{RED}Failed to launch scrcpy: {e}{RESET}")
        return False

def screen_start(device):
    print(f"{CYAN}Audio options:{RESET}")
    print("1. Screen only (no audio)")
    print("2. Screen with device audio (Android 11+)")
    print("3. Screen with microphone input (Android 11+)")
    choice = input(f"{CYAN}Choose option: {RESET}").strip()

    extra_args = ""
    if choice == "2":
        sdk_out = run_adb_command("shell getprop ro.build.version.sdk", device)
        try:
            sdk = int(sdk_out.strip())
            if sdk >= 30:
                extra_args = "--audio-source=playback"
                print(f"{GREEN}Using audio playback.{RESET}")
            else:
                print(f"{YELLOW}Audio not supported (API {sdk} < 30).{RESET}")
        except:
            print(f"{YELLOW}Could not determine Android version.{RESET}")
    elif choice == "3":
        sdk_out = run_adb_command("shell getprop ro.build.version.sdk", device)
        try:
            sdk = int(sdk_out.strip())
            if sdk >= 30:
                extra_args = "--audio-source=mic"
                print(f"{GREEN}Using microphone input.{RESET}")
            else:
                print(f"{YELLOW}Audio not supported (API {sdk} < 30).{RESET}")
        except:
            print(f"{YELLOW}Could not determine Android version.{RESET}")
    else:
        print("No audio will be captured.")

    if launch_scrcpy(device, extra_args):
        
        pass
    else:
        print(f"{RED}Failed to launch scrcpy.{RESET}")

def screen_custom(device):
    extra_args = input(f"{CYAN}Extra scrcpy arguments: {RESET}").strip()
    if launch_scrcpy(device, extra_args):
        # Silent
        pass
    else:
        print(f"{RED}Failed to launch scrcpy.{RESET}")

def screen_stop(device):
    if sys.platform.startswith('linux') or sys.platform == 'darwin':
        subprocess.run(["pkill", "scrcpy"])
        print(f"{GREEN}Attempted to kill scrcpy.{RESET}")
    else:
        print(f"{YELLOW}On Windows, close scrcpy window manually.{RESET}")

def screen_show_active_sessions(device):
    out = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if "scrcpy" in line:
            print(line)

def screen_multi_device():
    if not ensure_scrcpy():
        return
    devices = list_devices()
    for serial, status in devices:
        if status == "device":
            print(f"Starting scrcpy for {serial}")
            launch_scrcpy(serial)

def screen_check_scrcpy():
    if ensure_scrcpy():
        # Now print the path since it's explicitly requested
        print(f"{GREEN}scrcpy is installed at: {SCRCPY_PATH}{RESET}")
    else:
        print(f"{RED}scrcpy is not installed or not working.{RESET}")

def screen_record(device):
    output_file = input(f"{CYAN}Output file name (default: record.mp4): {RESET}").strip()
    if not output_file:
        output_file = "record.mp4"
    duration = input(f"{CYAN}Recording duration in seconds (default 30): {RESET}").strip()
    if not duration:
        duration = "30"
    remote_path = "/sdcard/screen_record.mp4"
    cmd = f"shell screenrecord --time-limit {duration} {remote_path}"
    print(f"{YELLOW}Recording for {duration} seconds...{RESET}")
    run_adb_command(cmd, device)
    run_adb_command(f"pull {remote_path} {output_file}", device)
    run_adb_command(f"shell rm {remote_path}", device)
    print(f"{GREEN}Recording saved as {output_file}{RESET}")

def screen_sync_folder(device):
    remote_folder = input(f"{CYAN}Remote folder to sync: {RESET}").strip()
    local_folder = input(f"{CYAN}Local folder to sync to: {RESET}").strip()
    if remote_folder and local_folder:
        out = run_adb_command(f"pull {remote_folder} {local_folder}", device)
        print(out)

# ----------------------------------------------------------------------
# WiFi Management
# ----------------------------------------------------------------------
def wifi_manual_transfer():
    ip = input(f"{CYAN}Enter device IP: {RESET}").strip()
    port = input(f"{CYAN}Enter port (default {TCPIP_PORT}): {RESET}").strip()
    if not port:
        port = TCPIP_PORT
    else:
        port = int(port)
    out = run_adb_command(f"connect {ip}:{port}")
    print(out)

def wifi_transfer_all():
    devices = list_devices()
    for serial, status in devices:
        if status == "device" and ":" in serial:
            continue
        if status == "device":
            ip = get_device_ip(serial)
            if ip:
                print(f"Connecting {serial} at {ip}:{TCPIP_PORT}")
                run_adb_command(f"tcpip {TCPIP_PORT}", serial)
                time.sleep(2)
                run_adb_command(f"connect {ip}:{TCPIP_PORT}")
            else:
                print(f"{RED}Could not get IP for {serial}{RESET}")

def wifi_quick_setup():
    auto_tcpip()

def wifi_status():
    devices = list_devices()
    for serial, status in devices:
        print(f"{serial} : {status}")

def wifi_disconnect():
    ip = input(f"{CYAN}Enter device IP to disconnect (or 'all'): {RESET}").strip()
    if ip == 'all':
        devices = list_devices()
        for serial, status in devices:
            if ":" in serial:
                ip_part = serial.split(':')[0]
                run_adb_command(f"disconnect {ip_part}")
                print(f"Disconnected {serial}")
    else:
        out = run_adb_command(f"disconnect {ip}")
        print(out)

def wifi_toggle_auto():
    global AUTO_TCPIP
    AUTO_TCPIP = not AUTO_TCPIP
    save_config()
    print(f"{GREEN}Auto TCP/IP is now {'ON' if AUTO_TCPIP else 'OFF'}{RESET}")

def wifi_monitor_logcat(device):
    print(f"{YELLOW}Monitoring logcat (Ctrl+C to stop){RESET}")
    try:
        subprocess.run([ADB_PATH, "-s", device, "logcat"])
    except KeyboardInterrupt:
        print("\nLogcat stopped.")

def wifi_service_status():
    services = ["adb", "scrcpy"]
    for svc in services:
        if svc == "adb":
            out = run_adb_command("devices")
            if "List of devices attached" in out:
                print("ADB: running")
            else:
                print("ADB: not responding")
        elif svc == "scrcpy":
            if is_scrcpy_available()[0]:
                print("scrcpy: installed")
            else:
                print("scrcpy: not found")

def wifi_settings():
    global AUTO_TCPIP, TCPIP_PORT
    print(f"{YELLOW}=== Settings ==={RESET}")
    print(f"1. Auto TCP/IP: {'ON' if AUTO_TCPIP else 'OFF'}")
    print(f"2. TCP/IP Port: {TCPIP_PORT}")
    print("3. Save and exit")
    choice = input(f"{CYAN}Select option: {RESET}").strip()
    if choice == "1":
        AUTO_TCPIP = not AUTO_TCPIP
        save_config()
        print(f"{GREEN}Auto TCP/IP set to {'ON' if AUTO_TCPIP else 'OFF'}{RESET}")
    elif choice == "2":
        new_port = input(f"{CYAN}Enter new port (current {TCPIP_PORT}): {RESET}").strip()
        if new_port.isdigit():
            TCPIP_PORT = int(new_port)
            save_config()
            print(f"{GREEN}TCP/IP port set to {TCPIP_PORT}{RESET}")
        else:
            print(f"{RED}Invalid port.{RESET}")
    elif choice == "3":
        return
    else:
        print(f"{RED}Invalid choice.{RESET}")

# ----------------------------------------------------------------------
# Network scan for ADB devices on port 5555
# ----------------------------------------------------------------------
def scan_network_for_adb():
    """Scan local network for devices with ADB listening on port 5555."""
    print(f"{CYAN}Scanning local network for ADB devices on port {TCPIP_PORT}...{RESET}")

    # Get local IP and subnet
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '192.168.1.1'
    finally:
        s.close()

    # Try common private subnets if local_ip looks like a private IP
    parts = local_ip.split('.')
    if len(parts) == 4 and parts[0] in ('10', '172', '192'):
        if parts[0] == '192' and parts[1] == '168':
            base = f"{parts[0]}.{parts[1]}.{parts[2]}"
        elif parts[0] == '10':
            base = f"{parts[0]}.{parts[1]}.{parts[2]}"
        elif parts[0] == '172' and 16 <= int(parts[1]) <= 31:
            base = f"{parts[0]}.{parts[1]}.{parts[2]}"
        else:
            base = f"{parts[0]}.{parts[1]}.{parts[2]}"
    else:
        base = '192.168.1'

    found = []
    print(f"Probing {base}.1-254:{TCPIP_PORT} (this may take a while)...")
    for i in range(1, 255):
        ip = f"{base}.{i}"
        try:
            with socket.create_connection((ip, TCPIP_PORT), timeout=0.5):
                out = run_adb_command(f"connect {ip}:{TCPIP_PORT}")
                if "connected" in out.lower() or "already" in out.lower():
                    print(f"{GREEN}Found device at {ip}:{TCPIP_PORT}{RESET}")
                    found.append(f"{ip}:{TCPIP_PORT}")
                else:
                    print(f"{YELLOW}Port open but ADB not responding at {ip}{RESET}")
        except:
            pass
    return found

# ----------------------------------------------------------------------
# Menu Handlers
# ----------------------------------------------------------------------
def device_management_menu(device):
    while True:
        print(f"{YELLOW}\n--- Device Management ---{RESET}")
        print("1. List devices")
        print("2. Connect WiFi")
        print("3. Restart ADB")
        print("4. Device info")
        print("5. Execute shell command")
        print("6. Reboot device")
        print("7. Disconnect device")
        print("0. Back")
        choice = input(f"{CYAN}Option: {RESET}").strip()
        if choice == "0":
            break
        elif choice == "1":
            device_list()
        elif choice == "2":
            device_connect_wifi()
        elif choice == "3":
            device_restart_adb()
        elif choice == "4":
            device_info(device)
        elif choice == "5":
            device_shell(device)
        elif choice == "6":
            device_reboot(device)
        elif choice == "7":
            device_disconnect(device)
        else:
            print(f"{RED}Invalid option.{RESET}")

def app_management_menu(device):
    while True:
        print(f"{YELLOW}\n--- App Management ---{RESET}")
        print("1. Install APK")
        print("2. Uninstall app")
        print("3. List packages")
        print("4. Package info")
        print("5. Clear app data")
        print("6. Force stop app")
        print("7. Start app")
        print("8. Backup app")
        print("9. Batch install")
        print("0. Back")
        choice = input(f"{CYAN}Option: {RESET}").strip()
        if choice == "0":
            break
        elif choice == "1":
            app_install(device)
        elif choice == "2":
            app_uninstall(device)
        elif choice == "3":
            app_list_packages(device)
        elif choice == "4":
            app_package_info(device)
        elif choice == "5":
            app_clear_data(device)
        elif choice == "6":
            app_force_stop(device)
        elif choice == "7":
            app_start(device)
        elif choice == "8":
            app_backup(device)
        elif choice == "9":
            app_batch_install(device)
        else:
            print(f"{RED}Invalid option.{RESET}")

def file_operations_menu(device):
    while True:
        print(f"{YELLOW}\n--- File Operations ---{RESET}")
        print("1. Take screenshot")
        print("2. Multiple screenshot")
        print("3. Upload file")
        print("4. Download file")
        print("5. List files")
        print("6. Create folder")
        print("7. Delete file/folder")
        print("8. Backup folder")
        print("0. Back")
        choice = input(f"{CYAN}Option: {RESET}").strip()
        if choice == "0":
            break
        elif choice == "1":
            file_take_screenshot(device)
        elif choice == "2":
            file_multiple_screenshot(device)
        elif choice == "3":
            file_upload(device)
        elif choice == "4":
            file_download(device)
        elif choice == "5":
            file_list(device)
        elif choice == "6":
            file_create_folder(device)
        elif choice == "7":
            file_delete(device)
        elif choice == "8":
            file_backup_folder(device)
        else:
            print(f"{RED}Invalid option.{RESET}")

def system_monitoring_menu(device):
    while True:
        print(f"{YELLOW}\n--- System Monitoring ---{RESET}")
        print("1. Battery info")
        print("2. Memory info")
        print("3. CPU info")
        print("4. Storage info")
        print("5. Running processes")
        print("6. Network info")
        print("7. System properties")
        print("8. Apps with size")
        print("9. Monitor performance")
        print("0. Back")
        choice = input(f"{CYAN}Option: {RESET}").strip()
        if choice == "0":
            break
        elif choice == "1":
            sys_battery(device)
        elif choice == "2":
            sys_memory(device)
        elif choice == "3":
            sys_cpu(device)
        elif choice == "4":
            sys_storage(device)
        elif choice == "5":
            sys_processes(device)
        elif choice == "6":
            sys_network(device)
        elif choice == "7":
            sys_properties(device)
        elif choice == "8":
            sys_apps_with_size(device)
        elif choice == "9":
            sys_monitor_performance(device)
        else:
            print(f"{RED}Invalid option.{RESET}")

def screen_sharing_menu(device):
    while True:
        print(f"{YELLOW}\n--- Screen Sharing & Recording ---{RESET}")
        print("1. Start screen sharing (default)")
        print("2. Custom screen sharing")
        print("3. Stop screen sharing")
        print("4. Show active sessions")
        print("5. Multi-device sharing")
        print("6. Check scrcpy")
        print("7. Record screen")
        print("8. Sync folder")
        print("0. Back")
        choice = input(f"{CYAN}Option: {RESET}").strip()
        if choice == "0":
            break
        elif choice == "1":
            screen_start(device)
        elif choice == "2":
            screen_custom(device)
        elif choice == "3":
            screen_stop(device)
        elif choice == "4":
            screen_show_active_sessions(device)
        elif choice == "5":
            screen_multi_device()
        elif choice == "6":
            screen_check_scrcpy()
        elif choice == "7":
            screen_record(device)
        elif choice == "8":
            screen_sync_folder(device)
        else:
            print(f"{RED}Invalid option.{RESET}")

def wifi_management_menu(device):
    while True:
        print(f"{YELLOW}\n--- WiFi Management ---{RESET}")
        print("1. Manual WiFi transfer")
        print("2. Transfer all devices")
        print("3. Quick WiFi setup")
        print("4. Scan network for ADB devices (port 5555)")
        print("5. WiFi status")
        print("6. Disconnect WiFi")
        print("7. Toggle auto-transfer")
        print("8. Monitor logcat")
        print("9. Service status")
        print("10. Settings")
        print("0. Back")
        choice = input(f"{CYAN}Option: {RESET}").strip()
        if choice == "0":
            break
        elif choice == "1":
            wifi_manual_transfer()
        elif choice == "2":
            wifi_transfer_all()
        elif choice == "3":
            wifi_quick_setup()
        elif choice == "4":
            found = scan_network_for_adb()
            if found:
                print(f"{GREEN}Found devices:{RESET}")
                for d in found:
                    print(f"  {d}")
            else:
                print(f"{YELLOW}No ADB devices found on port {TCPIP_PORT}.{RESET}")
        elif choice == "5":
            wifi_status()
        elif choice == "6":
            wifi_disconnect()
        elif choice == "7":
            wifi_toggle_auto()
        elif choice == "8":
            wifi_monitor_logcat(device)
        elif choice == "9":
            wifi_service_status()
        elif choice == "10":
            wifi_settings()
        else:
            print(f"{RED}Invalid option.{RESET}")

# ----------------------------------------------------------------------
# About & Exit
# ----------------------------------------------------------------------
def about():
    banner_small()
    print(f"{GREEN}Author   {RED}:  {PINK}Rabi kishan Rauniyar {RED}[ {PINK}max-Droid {RED}]{RESET}")
    print(f"{GREEN}Github   {RED}:  {CYAN}https://github.com/07iamravi{RESET}")
    print(f"{GREEN}Version  {RED}:  {PINK}{VERSION}{RESET}")
    print()
    print(f"{WHITE}{REDBG}Warning:{RESETBG}")
    print(f"{CYAN}  This tool is made for educational purposes only!{RESET}")
    print(f"{CYAN}  Author will not be responsible for any misuse.{RESET}\n")
    print(f"{GREEN}Special thanks to:{RESET}")
    print(f"{PINK}  MAXXX (ofc ME).{RESET}\n")
    input(f"{CYAN}Press Enter to return to main menu...{RESET}")

def exit_message():
    global RUN_WATCHER
    RUN_WATCHER = False
    print(f"\n{GREENBG}{BLACK} Thank you for using max-Droid. Stay ethical! {RESET}\n")
    sys.exit(0)

# ----------------------------------------------------------------------
# Main Menu
# ----------------------------------------------------------------------
def main_menu(device):
    while True:
        print(f"{YELLOW}\n=== MAIN MENU ==={RESET}")
        print(f"{RED}[{WHITE}1{RED}]{PINK} Device Management")
        print(f"{RED}[{WHITE}2{RED}]{PINK} App Management")
        print(f"{RED}[{WHITE}3{RED}]{PINK} File Operations")
        print(f"{RED}[{WHITE}4{RED}]{PINK} System Monitoring")
        print(f"{RED}[{WHITE}5{RED}]{PINK} Screen Sharing")
        print(f"{RED}[{WHITE}6{RED}]{PINK} WiFi Management")
        print(f"{RED}[{WHITE}7{RED}]{PINK} Dashboard")
        print(f"{RED}[{WHITE}99{RED}]{PINK} About")
        print(f"{RED}[{WHITE}00{RED}]{PINK} Exit")
        choice = input(f"{CYAN}Choose an option: {RESET}").strip()
        if choice in ("0", "00"):
            exit_message()
        elif choice == "99":
            about()
        elif choice == "1":
            device_management_menu(device)
        elif choice == "2":
            app_management_menu(device)
        elif choice == "3":
            file_operations_menu(device)
        elif choice == "4":
            system_monitoring_menu(device)
        elif choice == "5":
            screen_sharing_menu(device)
        elif choice == "6":
            wifi_management_menu(device)
        elif choice == "7":
            dashboard()
            input(f"{CYAN}Press Enter to return to main menu...{RESET}")
        else:
            print(f"{RED}Invalid option.{RESET}")

# ----------------------------------------------------------------------
def main():
    print_banner()

    if not ensure_adb():
        sys.exit(1)

    # AUTO RECONNECT – returns list of successfully reconnected devices
    reconnected = auto_reconnect_saved()

    # If we have any successfully reconnected devices, use the first one
    if reconnected:
        device = reconnected[0]
        print(f"{GREEN}Using device: {device}{RESET}")
    else:
        # No saved device worked, go interactive
        device = connect_device_interactive()

    if not device:
        print(f"{RED}No device available. Exiting.{RESET}")
        sys.exit(1)

    # ASK FOR NICKNAME (FIRST TIME)
    if device not in DEVICE_NAMES:
        print(f"{CYAN}New device detected.{RESET}")
        set_device_name(device)

    # START WATCHER (detects device changes)
    threading.Thread(target=device_watcher, daemon=True).start()

    # Go to main menu
    main_menu(device)

if __name__ == "__main__":
    main()
