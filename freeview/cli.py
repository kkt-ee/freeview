"""CLI entrypoints for freeview minimal tool."""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _script_path():
    # path to bundled streamlit app
    return Path(__file__).resolve().parent / "streamlit_app.py"


def _cert_dir() -> Path:
    """Return a per-user cert directory across platforms."""
    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "freeview" / "certs"
    xdg = os.getenv("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "freeview" / "certs"
    return Path.home() / ".local" / "share" / "freeview" / "certs"


def _confirm(prompt: str) -> bool:
    reply = input(f"{prompt} [y/N]: ").strip().lower()
    return reply in {"y", "yes"}


def _mkcert_install_hint() -> str:
    if os.name == "nt":
        return "Install mkcert in Administrator PowerShell: choco install mkcert -y"
    if sys.platform == "darwin":
        return "Install mkcert on macOS: brew install mkcert nss"
    return "Install mkcert (Linux) from your package manager or https://github.com/FiloSottile/mkcert"


def _ensure_local_certs(cert: Path, key: Path) -> int:
    """Create trusted localhost certs with explicit user consent."""
    if cert.exists() and key.exists():
        return 0

    print("HTTPS certs for localhost were not found.")
    print("freeview requires HTTPS and will not start without local certs.")

    mkcert_path = shutil.which("mkcert")
    if not mkcert_path:
        print(_mkcert_install_hint())
        print("Then run: freeview cert")
        return 2

    if not _confirm("Create and trust local localhost certificates now"):
        print("Cancelled by user. Run `freeview cert` when ready.")
        return 2

    cert.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.check_call([mkcert_path, "-install"])
        subprocess.check_call(
            [
                mkcert_path,
                "-ecdsa",
                "-cert-file",
                str(cert),
                "-key-file",
                str(key),
                "localhost",
                "127.0.0.1",
                "::1",
            ]
        )
    except subprocess.CalledProcessError as exc:
        print("mkcert failed:", exc)
        return 2

    if not (cert.exists() and key.exists()):
        print("Certificate creation did not produce expected files.")
        return 2

    return 0


def main():
    if sys.version_info < (3, 10):
        print("freeview requires Python 3.10 or newer.")
        sys.exit(2)

    parser = argparse.ArgumentParser(prog="freeview", description="FreeSurfer stats viewer utilities")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("stats2csv", help="Convert a FreeSurfer stats/ directory to CSVs")
    p.add_argument("--stats-dir", required=True, help="Path to stats directory")
    p.add_argument("--out-dir", required=True, help="Output directory for CSVs")

    s = sub.add_parser("serve", help="Start the Streamlit dashboard")
    s.add_argument("--host", default="localhost", help="Host to bind (default: localhost)")
    s.add_argument("--port", default=8501, type=int, help="Port to serve on (default: 8501)")

    c = sub.add_parser("cert", help="Create trusted localhost certificates (mkcert required)")

    args = parser.parse_args()
    if args.cmd == "stats2csv":
        # local import to avoid heavy deps at CLI import time
        from . import stats2csv

        stats2csv.convert_stats_dir(args.stats_dir, args.out_dir)
    elif args.cmd == "serve":
        script = _script_path()
        cert_dir = _cert_dir()
        cert = cert_dir / "localhost.pem"
        key = cert_dir / "localhost-key.pem"
        rc = _ensure_local_certs(cert, key)
        if rc != 0:
            sys.exit(rc)

        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(script),
            "--server.headless=true",
            "--server.address",
            args.host,
            "--server.port",
            str(args.port),
            f"--server.sslCertFile={str(cert)}",
            f"--server.sslKeyFile={str(key)}",
        ]
        # Launch Streamlit as a subprocess; this will block until terminated
        print("Starting Streamlit:", " ".join(cmd))
        subprocess.run(cmd, check=False)
    elif args.cmd == "cert":
        cert_dir = _cert_dir()
        cert = cert_dir / "localhost.pem"
        key = cert_dir / "localhost-key.pem"
        rc = _ensure_local_certs(cert, key)
        if rc == 0:
            print(f"Certificates ready: {cert}")
        sys.exit(rc)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
