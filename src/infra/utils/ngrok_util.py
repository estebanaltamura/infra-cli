"""
Module: ngrok_util
------------------
Encapsulates the logic to detect, launch, and automatically download ngrok.
Provides functions to:
    - Check if the local ngrok API is running.
    - Locate the ngrok executable (global or local).
    - Download and extract ngrok locally (if needed).
    - Launch ngrok on a specific port and wait for its API.
    - Return the public ngrok endpoint.
"""

import os
import sys
import time
import platform
import subprocess
import requests
import shutil
import urllib.request
import zipfile
from pathlib import Path


NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"
NGROK_DEFAULT_PORT = 8000
PROJECT_ROOT = Path(__file__).resolve().parents[2]
NGROK_BIN_DIR = PROJECT_ROOT / "bin" / "ngrok_bin"

def is_ngrok_running():
    """Returns True if ngrok's local API is available."""
    try:
        res = requests.get(NGROK_API_URL)
        res.raise_for_status()
        return True
    except Exception:
        return False

def get_download_url():
    system = platform.system()
    arch = platform.machine().lower()

    print(f"Detected platform: {system} ({arch})")

    if system == "Windows":
        if arch in ("amd64", "x86_64"):
            return "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
        elif arch in ("arm64", "aarch64"):
            return "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-arm64.zip"
        elif arch in ("x86", "i386", "i686"):
            return "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-386.zip"
        else:
            raise Exception(f"Unsupported Windows architecture: {arch}")

    elif system == "Darwin":
        if arch == "arm64":
            return "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-arm64.zip"
        elif arch in ("x86_64", "amd64"):
            return "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-darwin-amd64.zip"
        else:
            raise Exception(f"Unsupported macOS architecture: {arch}")

    elif system == "Linux":
        if arch in ("amd64", "x86_64"):
            return "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"
        elif arch in ("x86", "i386", "i686"):
            return "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-386.tgz"
        elif arch == "aarch64":
            return "https://bin.ngrok.com/ngrok-v3-stable-linux-arm64.zip"  
        else:
            raise Exception(f"Unsupported Linux architecture: {arch}")

    else:
        raise Exception(f"Unsupported operating system: {system} ({arch})")


def download_ngrok():
    """Downloads and extracts ngrok into NGROK_BIN_DIR and returns the path to the binary."""
    print("⏬ Downloading ngrok automatically...")
    os.makedirs(NGROK_BIN_DIR, exist_ok=True)
    url = get_download_url()
    zip_path = os.path.join(NGROK_BIN_DIR, "ngrok.zip")
    urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(NGROK_BIN_DIR)
    os.remove(zip_path)
    ngrok_exec = get_local_ngrok_path()
    if platform.system() != "Windows":
        os.chmod(ngrok_exec, 0o755)
    print("✅ Ngrok downloaded and ready at:", ngrok_exec)
    return ngrok_exec

def get_local_ngrok_path():
    """Returns the local path to the ngrok executable inside NGROK_BIN_DIR."""
    if platform.system() == "Windows":
        return os.path.join(NGROK_BIN_DIR, "ngrok.exe")
    else:
        return os.path.join(NGROK_BIN_DIR, "ngrok")

def resolve_ngrok_exec():
    """
    Attempts to use global ngrok executable; if not available or fails,
    uses local one; if also missing, downloads it.
    """
    ngrok_exec = shutil.which("ngrok")
    if ngrok_exec:
        try:
            subprocess.run([ngrok_exec, "version"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return ngrok_exec
        except Exception:
            print("⚠️ Global ngrok is present but not responding correctly.")
    local_ngrok = get_local_ngrok_path()
    if os.path.exists(local_ngrok):
        return local_ngrok
    return download_ngrok()

def start_ngrok(port=NGROK_DEFAULT_PORT, authtoken=None):
    """
    Launches ngrok on the specified port.
    If an authtoken is provided, it will be configured.
    Waits for the local ngrok API to be ready and returns the process.
    """
    ngrok_exec = resolve_ngrok_exec()

    # Kill any existing ngrok processes
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/F", "/IM", "ngrok.exe"], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL,
                          check=False)
        else:
            subprocess.run(["pkill", "ngrok"], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL,
                          check=False)
        print("Previous ngrok processes terminated.")
        time.sleep(2)
    except Exception as e:
        print(f"Warning while trying to terminate existing ngrok processes: {e}")

    # Apply authtoken if available
    if authtoken:
        try:
            subprocess.run([ngrok_exec, "authtoken", authtoken], check=True)
        except Exception as e:
            print(f"Error applying authtoken: {e}")
            print("Continuing without authtoken...")

    print(f"🚀 Launching ngrok on port {port}...")

    process = subprocess.Popen(
        [ngrok_exec, "http", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    timeout = 30
    for i in range(timeout):
        if is_ngrok_running():
            print(f"✅ Ngrok started successfully after {i+1} seconds.")
            return process

        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print(f"Ngrok exited prematurely with code: {process.returncode}")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            raise RuntimeError("Ngrok exited prematurely")

        time.sleep(1)
        print(f"Waiting for ngrok to start... {i+1}/{timeout} seconds")

    stdout, stderr = process.communicate(timeout=1)
    print(f"STDOUT: {stdout}")
    print(f"STDERR: {stderr}")
    process.terminate()
    raise RuntimeError("⏰ Timeout while waiting for ngrok to start.")

def get_ngrok_endpoint():
    """
    Returns the public ngrok endpoint (without protocol).
    If ngrok isn't running, it will be launched automatically.
    """
    if not is_ngrok_running():
        print("🔄 Ngrok is not running. It will be launched automatically...")
        authtoken = os.getenv("NGROK_AUTHTOKEN")
        port = int(os.getenv("NGROK_PORT", NGROK_DEFAULT_PORT))
        print(f"Using port {port} for ngrok")
        start_ngrok(port=port, authtoken=authtoken)
        time.sleep(5)

    try:
        res = requests.get(NGROK_API_URL)
        res.raise_for_status()
        data = res.json()       
        tunnels = data.get("tunnels", [])
        if not tunnels:
            port = int(os.getenv("NGROK_PORT", NGROK_DEFAULT_PORT))
            print(f"No active tunnels found. Make sure a service is listening on port {port}")
            raise ValueError("No active ngrok tunnels.")
        url = tunnels[0]["public_url"]
        return url.replace("https://", "").replace("http://", "")
    except Exception as e:
        raise RuntimeError(f"Error fetching ngrok endpoint: {e}")
