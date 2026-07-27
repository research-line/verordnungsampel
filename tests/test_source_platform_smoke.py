"""Kleine, reproduzierbare Source-Smokes für die unterstützten Desktop-Plattformen.

Die Tests sind bewusst kein Installer-, Tray- oder Produktivnachweis. Sie prüfen
die portable Source-Basis: CLI mit isoliertem Datenordner, GUI-Import ohne
Anzeigeserver und einen lokalen Web-Start mit einem echten HTTP-Readback.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from urllib.request import urlopen

import pytest
from werkzeug.serving import make_server


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"


def test_cli_check_source_smoke_uses_isolated_user_data(tmp_path):
    """Die CLI muss aus Source ohne lokale Nutzerdaten laufen."""
    env = os.environ.copy()
    env["APPDATA"] = str(tmp_path / "appdata")
    env["HOME"] = str(tmp_path / "home")
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "verordnungsampel.cli.main",
            "check",
            "--icd",
            "I10",
            "--atc",
            "C09AA02",
            "--no-log",
            "--json",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["icd"] == "I10"
    assert payload["atc"] == "C09AA02"
    assert payload["gesamt"] == "gruen"
    assert (tmp_path / "appdata" / "VerordnungsAmpel" / "regelwerk.db").exists()


def test_gui_modules_import_without_starting_a_tray():
    """Der GUI-Pfad muss ohne native Tray- oder Display-Interaktion importieren."""
    pytest.importorskip("PySide6")

    gui_app = importlib.import_module("verordnungsampel.gui.app")
    main_window = importlib.import_module("verordnungsampel.gui.main_window")

    assert gui_app._find_window_icon()
    assert Path(gui_app._find_window_icon()).is_file()
    assert main_window.MainWindow.__name__ == "MainWindow"


def test_web_source_smoke_starts_local_server_and_reads_health(tmp_path):
    """Der lokale Web-Prototyp muss auf Loopback starten und /health liefern."""
    from verordnungsampel.web import create_app

    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "web-smoke.db"),
        }
    )
    server = make_server("127.0.0.1", 0, app)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with urlopen(
            f"http://127.0.0.1:{server.server_port}/health", timeout=5
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["service"] == "verordnungsampel-web"
        assert payload["status"] == "ok"
        assert payload["version"]
    finally:
        server.shutdown()
        worker.join(timeout=5)
