import os
import sys
import subprocess
from typing import Optional
import platform

def log(msg: str) -> None:
    print(f"[*] {msg}")

def error_exit(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)

def run_command(args: list, cwd: Optional[str] = None) -> None:
    try:
        subprocess.check_call(args, cwd=cwd)
    except subprocess.CalledProcessError as e:
        error_exit(f"Command failed: {' '.join(args)} (Error: {e})")

def main() -> None:
    log("Setting up local environment for Amplify Federal Todo App...")
    
    # 1. Detect OS environment paths
    is_windows = platform.system() == "Windows"
    venv_dir = ".venv"
    
    if is_windows:
        python_bin = os.path.join(venv_dir, "Scripts", "python.exe")
        pip_bin = os.path.join(venv_dir, "Scripts", "pip.exe")
        uvicorn_bin = os.path.join(venv_dir, "Scripts", "uvicorn.exe")
    else:
        python_bin = os.path.join(venv_dir, "bin", "python")
        pip_bin = os.path.join(venv_dir, "bin", "pip")
        uvicorn_bin = os.path.join(venv_dir, "bin", "uvicorn")

    # 2. Initialize virtual environment if absent
    if not os.path.exists(venv_dir):
        log(f"Virtual environment not found. Initializing virtualenv in {venv_dir}...")
        # run base python environment creator
        run_command([sys.executable, "-m", "venv", venv_dir])
    else:
        log("Existing virtual environment detected.")

    # Double check binaries exist
    if not os.path.exists(python_bin):
        error_exit(f"Python interpreter not found at expected location: {python_bin}")

    # 3. Upgrade pip to prevent version conflicts
    log("Upgrading package manager (pip)...")
    run_command([python_bin, "-m", "pip", "install", "--upgrade", "pip"])

    # 4. Install dependencies listed in requirements.txt
    req_file = "requirements.txt"
    if not os.path.exists(req_file):
        error_exit(f"Requirements file not found at: {os.path.abspath(req_file)}")

    log(f"Installing pinned dependencies from {req_file}...")
    run_command([pip_bin, "install", "-r", req_file])

    # 5. Launch FastAPI application server using Uvicorn
    if not os.path.exists(uvicorn_bin):
        error_exit(f"Uvicorn server binary not found at: {uvicorn_bin}")

    log("Application initialized successfully! Starting server...")
    log("Access API docs: http://127.0.0.1:8000/docs")
    log("Access UI: http://127.0.0.1:8000")
    log("Press Ctrl+C to terminate.")
    
    # We pass control directly to the Uvicorn execution loop
    try:
        subprocess.run([uvicorn_bin, "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"])
    except KeyboardInterrupt:
        print("\n[*] Server shutdown gracefully.")

if __name__ == "__main__":
    main()
