#!/usr/bin/env python
"""
Bengaluru Road Safety AI - Unified Terminal Launcher
Runs Django REST Backend and React Vite Frontend concurrently.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Ensure UTF-8 output encoding if supported by terminal
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent

def main():
    print("=" * 65)
    print("  [+] Bengaluru Road Safety AI - Full Stack Launcher")
    print("  Frameworks: Django REST Backend + React (Vite) Frontend")
    print("=" * 65)

    backend_dir = PROJECT_ROOT / "backend"
    frontend_dir = PROJECT_ROOT / "frontend"

    if not backend_dir.exists():
        print(f"[X] Error: Backend directory not found at {backend_dir}")
        sys.exit(1)
    if not frontend_dir.exists():
        print(f"[X] Error: Frontend directory not found at {frontend_dir}")
        sys.exit(1)

    processes = []

    try:
        # 1. Launch Django REST Backend
        print("\n[*] [1/2] Starting Django REST Backend on http://localhost:8000/...")
        backend_cmd = [sys.executable, "manage.py", "runserver", "8000"]
        backend_proc = subprocess.Popen(
            backend_cmd,
            cwd=str(backend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("Django Backend", backend_proc))
        time.sleep(2)

        # 2. Launch React Frontend
        print("[*] [2/2] Starting React Vite Frontend on http://localhost:5173/...")
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        frontend_proc = subprocess.Popen(
            [npm_cmd, "run", "dev"],
            cwd=str(frontend_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append(("React Frontend", frontend_proc))

        print("\n" + "=" * 65)
        print("  [SUCCESS] Bengaluru Road Safety AI application is RUNNING!")
        print("  --> React Dashboard: http://localhost:5173/")
        print("  --> Django REST API:  http://localhost:8000/api/")
        print("  Press Ctrl+C in terminal to stop all servers cleanly.")
        print("=" * 65 + "\n")

        # Monitor processes
        while True:
            for name, proc in processes:
                poll = proc.poll()
                if poll is not None:
                    print(f"[!] Process '{name}' exited with code {poll}")
                    out, _ = proc.communicate()
                    if out:
                        print(out)
                    raise KeyboardInterrupt
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[*] Shutting down servers gracefully...")
        for name, proc in processes:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
        print("[OK] All processes stopped.")

if __name__ == "__main__":
    main()
