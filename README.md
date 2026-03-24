# max-Droid – Android Management Framework

![Python Version](https://img.shields.io/badge/python-3.6+-blue.svg)
![Platform](https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20macos-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

**max-Droid** is a feature‑rich Android management framework that wraps ADB into a sleek, interactive terminal interface.  
It automates device connection, provides comprehensive device, app, file, system, screen, and Wi‑Fi management, and includes automatic ADB installation and wireless reconnection.

> ⚠️ **For Educational Purposes Only**  
> Use this tool only on devices you own or have explicit permission to manage. Misuse may violate laws and regulations.

---

## 📋 Features

- **Device Management** – List, connect, disconnect, view info, reboot, execute shell commands.
- **App Management** – Install/uninstall, list packages, get package info, clear data, force stop, start apps, backup, batch install.
- **File Operations** – Screenshots (single or multiple), upload/download, list files, create/delete folders, backup folders.
- **System Monitoring** – Battery, memory, CPU, storage, running processes, network, system properties, performance monitor.
- **Screen Sharing & Recording** – Real‑time screen mirroring with optional audio (device audio or microphone), custom arguments, multi‑device sharing, screen recording.
- **Wi‑Fi Management** – Switch from USB to wireless mode, scan local network for ADB‑enabled devices, toggle automatic wireless switching, monitor logcat, service status.
- **Dashboard** – Live view of connected devices with connection events.
- **Auto‑reconnect** – Remembers wireless devices and reconnects automatically.
- **Nickname System** – Give your devices friendly names.
- **Automatic ADB Setup** – Downloads and installs the latest platform‑tools if not found.
- **Modern Hacker Aesthetic** – Colorful output, pyfiglet banners, and a clean menu structure.

---

## 🚀 Installation

### Prerequisites
- **Python 3.6+**  
- **ADB** (optional – the tool can download it for you)  
- **Screen sharing** requires a compatible Android device (Android 5.0+); the tool will download the necessary helper if needed.

### Clone & Run
```bash
git clone https://github.com/07iamravi/max-Droid.git
cd max-Droid
python3 maxdroid.py
```

Here is the content of your documentation formatted in clean, consistent Markdown:

# MaxDroid Documentation

On first run, the script will check for **ADB**. If missing, it will offer to download it automatically (recommended). All files are stored in `~/.maxdroid/`.

## 💡 Usage

The tool starts with an interactive menu.

### Main Menu

```text
=== MAIN MENU ===
[1] Device Management
[2] App Management
[3] File Operations
[4] System Monitoring
[5] Screen Sharing
[6] WiFi Management
[7] Dashboard
[99] About
[00] Exit
```

Each sub‑menu contains numbered options. Just type the number and press **Enter**.

#### Example: Screen Sharing with Audio
1. Choose option **5** → **1** (Start screen sharing)
2. Select audio mode:
    * **1** – Screen only
    * **2** – Screen + device audio (Android 11+)
    * **3** – Screen + microphone (Android 11+)
3. The screen mirroring window appears – enjoy!

---

## ⚙️ Configuration

The tool creates two files in your home directory:
* `~/.maxdroid.conf` – Settings (auto wireless switching flag, port)
* `~/.maxdroid_devices.json` – Device nicknames

You can edit these manually or use the built‑in **Settings** option (*WiFi Management → Settings*).

---

## 🛠️ Advanced

### Manual ADB Installation
If auto‑download fails, you can install ADB manually:
* **Windows:** Download `platform-tools`, add to PATH.
* **Linux:** `sudo apt install adb` (or equivalent)
* **macOS:** `brew install android-platform-tools`

### Manual Screen‑sharing Helper Installation
The tool can download the required helper automatically. If you prefer to install it yourself, follow the instructions on the [official scrcpy website](https://github.com/Genymobile/scrcpy).

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or pull requests. Please keep the code clean, maintain the existing style, and update the README if needed.

## 📜 License

This project is licensed under the **MIT License** – see the `LICENSE` file for details.

---

## ⚠️ Disclaimer

This tool is intended for **educational and research purposes only**. The author does not condone any misuse and is not responsible for any damage caused by using this software. Always ensure you have permission before interacting with any device.

