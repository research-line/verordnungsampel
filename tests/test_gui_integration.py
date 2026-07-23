"""Integrationstests fuer das PySide6-Frontend.

Ziel ist es, die GUI-Struktur zu pruefen, ohne dass ein echter User-
Klick gerendert werden muss. Die Engine-Kopplung wird direkt getestet
(Check-Tab ruft ``evaluate`` auf). Fehlendes PySide6 oder Systray fuehrt
zum ``skip`` des kompletten Moduls.
"""

from __future__ import annotations

import os
import sys

import pytest

pytest.importorskip("PySide6")

# Headless-Windows/Linux: offscreen Platform (auch ohne Monitor lauffaehig).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QSystemTrayIcon  # noqa: E402

from verordnungsampel.audit.compliance_log import ComplianceLog  # noqa: E402
from verordnungsampel.db.connection import open_database  # noqa: E402
from verordnungsampel.db.seed import load_seed_data  # noqa: E402
from verordnungsampel.engine.evaluator import Ampel, evaluate  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    """Einmalige QApplication fuer alle GUI-Tests."""
    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    # NICHT app.quit() — pytest-qt / Folgetests koennten sie brauchen.


@pytest.fixture(autouse=True)
def isolated_data_dirs(tmp_path, monkeypatch):
    """Isoliert user_data_dir() pro Test (Regelwerk- und Compliance-DB)."""
    from verordnungsampel.utils import paths as path_utils
    from verordnungsampel.db import connection as conn_mod
    from verordnungsampel.audit import compliance_log as log_mod

    monkeypatch.setattr(path_utils, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(conn_mod, "user_data_dir", lambda: tmp_path)
    monkeypatch.setattr(log_mod, "user_data_dir", lambda: tmp_path)

    # DB initialisieren und seeden, damit Check-Tests echte Ergebnisse haben.
    conn, _ = open_database()
    load_seed_data(conn)
    conn.close()
    yield


# ---------------------------------------------------------------------------
# 1. QApplication erzeugbar
# ---------------------------------------------------------------------------


def test_qapplication_vorhanden(qapp):
    assert qapp is not None
    assert QApplication.instance() is qapp


# ---------------------------------------------------------------------------
# 2. Tray-Icon wird erzeugt
# ---------------------------------------------------------------------------


def test_tray_controller_und_icon(qapp):
    from verordnungsampel.gui.app import TrayController
    from verordnungsampel.gui.main_window import MainWindow
    from verordnungsampel.gui import strings_de as S

    # Auf manchen Headless-Systemen meldet Qt kein Systray. In dem Fall nur
    # die Icon-Pfade pruefen, keinen echten Tray bauen.
    if not QSystemTrayIcon.isSystemTrayAvailable():
        from verordnungsampel.gui.app import ICONS_DIR

        assert (ICONS_DIR / "tray_grey.svg").exists()
        assert (ICONS_DIR / "tray_green.svg").exists()
        assert (ICONS_DIR / "tray_yellow.svg").exists()
        assert (ICONS_DIR / "tray_red.svg").exists()
        return

    window = MainWindow()
    controller = TrayController(qapp, window)
    try:
        assert controller.tray is not None
        assert controller.tray.toolTip() == S.TRAY_TOOLTIP
        # Setzt auf eine der vier Farben, kein Fehler erwartet
        controller.set_ampel_icon("gelb")
        assert S.AMPEL_GELB in controller.tray.toolTip()
        controller.set_ampel_icon("")  # fallback grey
        assert controller.tray.toolTip() == S.TRAY_TOOLTIP
    finally:
        controller.tray.hide()
        window.deleteLater()


# ---------------------------------------------------------------------------
# 3. MainWindow Tabs vorhanden
# ---------------------------------------------------------------------------


def test_main_window_hat_alle_tabs(qapp):
    from verordnungsampel.gui.main_window import MainWindow

    window = MainWindow()
    try:
        tab_texts = [window.tabs.tabText(i) for i in range(window.tabs.count())]
        # 6 Tabs: Check, Begruenden, Workflow, Log, Reminder, Regelwerke
        assert window.tabs.count() == 6
        assert "Check" in tab_texts
        assert any(t.startswith("Begr") for t in tab_texts)  # Begruenden (ae/Umlaut)
        assert "Workflow" in tab_texts
        assert any("Log" in t for t in tab_texts)
        assert "Reminder" in tab_texts
        assert "Regelwerke" in tab_texts
    finally:
        window.deleteLater()


# ---------------------------------------------------------------------------
# 4. Check-Tab gibt GRUEN fuer I10+C09AA02 zurueck (via Engine, nicht Click)
# ---------------------------------------------------------------------------


def test_check_tab_gruen_via_engine(qapp):
    """Der Check-Tab muss korrekt auf die Engine zugreifen (I10+C09AA02 = GRUEN)."""
    # Engine direkt (wie sie aus dem Tab heraus aufgerufen wird)
    conn, _ = open_database()
    try:
        erg = evaluate("I10", "C09AA02", alter=None, conn=conn)
    finally:
        conn.close()
    assert erg.gesamt is Ampel.GRUEN

    # Der Tab soll das Signal emittieren und das Ergebnis anzeigen.
    from verordnungsampel.gui.tabs.check_tab import CheckTab

    tab = CheckTab()
    try:
        received = []
        tab.result_ready.connect(received.append)

        tab.icd_edit.setText("I10")
        tab.atc_edit.setText("C09AA02")
        tab.no_log_chk.setChecked(True)  # Log sauber halten
        tab.on_check()

        assert len(received) == 1
        assert received[0].gesamt is Ampel.GRUEN
        # Ampel-Label zeigt GRUEN
        assert "GR" in tab.ampel_label.text().upper()
    finally:
        tab.deleteLater()


# ---------------------------------------------------------------------------
# 5. Close-Event minimiert, quit_requested beendet
# ---------------------------------------------------------------------------


def test_close_minimiert_und_quit_beendet(qapp):
    """closeEvent ohne ``allow_close`` darf das Fenster NICHT wirklich schliessen.

    ``quit_requested`` (aus dem Tray oder Datei -> Beenden) setzt das Flag
    und fuehrt danach zum echten Schliessen.
    """
    from PySide6.QtGui import QCloseEvent

    from verordnungsampel.gui.main_window import MainWindow

    window = MainWindow()
    try:
        # Signal-Emission bei quit_requested abonnieren
        signals_received = []
        window.quit_requested.connect(lambda: signals_received.append("quit"))

        # 1) closeEvent ohne Erlaubnis -> ignoriert
        window.show()
        assert window.isVisible()

        event = QCloseEvent()
        window.closeEvent(event)
        assert not event.isAccepted()
        # Fenster wird versteckt, nicht zerstoert
        assert window.isHidden() or not window.isVisible()

        # 2) quit_requested emittieren
        window.quit_requested.emit()
        assert signals_received == ["quit"]

        # 3) Nach allow_close = True wird closeEvent akzeptiert
        window.allow_close = True
        event2 = QCloseEvent()
        window.closeEvent(event2)
        assert event2.isAccepted()
    finally:
        window.deleteLater()


# ---------------------------------------------------------------------------
# 6 (Bonus). Justify-Tab deaktiviert sich bei GRUEN, aktiviert bei GELB/ROT
# ---------------------------------------------------------------------------


def test_justify_tab_state_wechselt_mit_ergebnis(qapp):
    from verordnungsampel.gui.main_window import MainWindow

    window = MainWindow()
    try:
        conn, _ = open_database()
        try:
            gruen = evaluate("I10", "C09AA02", conn=conn)
            # Aus dem Seed: F41 + N05BA01 mit Alter 72 -> ROT (PRISCUS)
            rot = evaluate("F41", "N05BA01", alter=72, conn=conn)
        finally:
            conn.close()

        window._on_result_ready(gruen)
        idx_j = window.tabs.indexOf(window.justify_tab)
        assert not window.tabs.isTabEnabled(idx_j)

        window._on_result_ready(rot)
        assert window.tabs.isTabEnabled(idx_j)
    finally:
        window.deleteLater()


# ---------------------------------------------------------------------------
# 7 (Bonus). Workflow-Tab Context-Builder
# ---------------------------------------------------------------------------


def test_workflow_tab_context_liest_praxisdaten(qapp):
    from verordnungsampel.gui.tabs.workflow_tab import WorkflowTab

    tab = WorkflowTab()
    try:
        tab.praxis_edit.setText("Praxis Dr. Mustermann")
        tab.arzt_edit.setText("Dr. med. Mustermann")
        tab.kk_edit.setText("AOK Nordost")
        tab.patient_edit.setText("P-0001")
        ctx = tab._context()
        assert ctx.praxis_name == "Praxis Dr. Mustermann"
        assert ctx.arzt_name == "Dr. med. Mustermann"
        assert ctx.kk_name == "AOK Nordost"
        assert ctx.patient_kennung == "P-0001"
    finally:
        tab.deleteLater()
