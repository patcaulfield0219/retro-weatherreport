import importlib.util
import os
import socket
import sys
from urllib.request import urlopen


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS = [
    "assets/audio/wiiUmiimaker.mp3",
    "assets/audio/terminal_open.mp3",
    "assets/fonts/Belgrad.ttf",
    "assets/ads/plasma_cutter.png",
    "assets/logos/halcyon_logo.webp",
]
PACKAGES = ["requests", "pygame", "PIL"]


def ok(label):
    print(f"[OK] {label}")


def warn(label):
    print(f"[WARN] {label}")


def fail(label):
    print(f"[FAIL] {label}")


def check_python():
    version = sys.version_info
    if version >= (3, 10):
        ok(f"Python {version.major}.{version.minor}.{version.micro}")
    else:
        fail("Python 3.10 or newer is recommended.")


def check_packages():
    for package in PACKAGES:
        if importlib.util.find_spec(package):
            ok(f"Python package available: {package}")
        else:
            fail(f"Missing package: {package}. Run: pip install -r requirements.txt")


def check_assets():
    for rel_path in ASSETS:
        path = os.path.join(BASE_DIR, rel_path)
        if os.path.exists(path):
            ok(f"Asset found: {rel_path}")
        else:
            fail(f"Missing asset: {rel_path}")


def check_url(name, url, timeout=5):
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status < 400:
                ok(f"{name} reachable")
            else:
                warn(f"{name} returned HTTP {response.status}")
    except Exception as exc:
        warn(f"{name} unavailable: {exc}")


def check_ollama():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        sock.connect(("127.0.0.1", 11434))
        ok("Ollama server reachable on localhost:11434")
    except Exception:
        warn("Ollama is offline. The app still runs with local fallback summaries.")
    finally:
        sock.close()


def main():
    print("Arcadia 5000 setup check")
    print("=" * 32)
    check_python()
    check_packages()
    check_assets()
    check_url("Open-Meteo", "https://api.open-meteo.com/v1/forecast?latitude=25&longitude=121&current=temperature_2m")
    check_ollama()
    print("=" * 32)
    print("Run the app with: python3 main.py")


if __name__ == "__main__":
    main()
