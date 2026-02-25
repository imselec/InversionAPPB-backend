import re
import subprocess
import sys
import time
from pathlib import Path

LOG_FILE = "backend_log.txt"


def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{timestamp} - {message}"
    print(entry)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def install_missing_module(module_name):
    log(f"Módulo faltante detectado: {module_name}. Instalando...")
    subprocess.call([sys.executable, "-m", "pip", "install", module_name])
    log(f"Módulo {module_name} instalado.")


def run_backend():
    while True:
        log("Iniciando uvicorn...")
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--reload",
                "--host",
                "127.0.0.1",
                "--port",
                "8080",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        for line in process.stdout:
            print(line, end="")
            if "ModuleNotFoundError" in line:
                match = re.search(r"No module named '(.+?)'", line)
                if match:
                    missing = match.group(1)
                    install_missing_module(missing)
                    process.kill()
                    break

        process.wait()
        log("Reiniciando backend...")
        time.sleep(2)


if __name__ == "__main__":
    run_backend()
