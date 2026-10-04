"""Start both loopback services, shut them down together on Ctrl-C or child failure."""

import argparse
import os
import signal
import subprocess
import sys
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args()
    env = {**os.environ, "PRIOR_SOURCE": "mock", "PRIOR_FIXTURE": str(args.fixture).lower()}
    # Keep demo data away from the user's real inbox database.
    env["PRIOR_DATABASE_PATH"] = "data/fixture.sqlite3" if args.fixture else "data/demo.sqlite3"
    processes: list[subprocess.Popen] = []
    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                    "--no-access-log",
                ],
                env=env,
                start_new_session=os.name != "nt",
            )
        )
        processes.append(
            subprocess.Popen(
                ["npm", "--prefix", "frontend", "run", "dev"],
                env=env,
                start_new_session=os.name != "nt",
            )
        )
        print("PriorInbox: http://127.0.0.1:5173 · Ctrl-C stops both services", flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(0.5)
        raise SystemExit(next((p.returncode for p in processes if p.returncode), 1))
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                if os.name == "nt":
                    process.terminate()
                else:
                    os.killpg(process.pid, signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()


if __name__ == "__main__":
    main()
