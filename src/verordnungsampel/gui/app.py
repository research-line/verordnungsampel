"""QApplication + QSystemTrayIcon + Main-Window-Lifecycle.

Entry-Point für die GUI. Startet eine :class:`QApplication`, legt das
Systray-Icon an, verbindet Show/Hide/Quit und übernimmt die Kontrolle
über das Schließ-Verhalten: "X" am Fenster minimiert in den Tray,
echtes Beenden nur über Tray-Menü oder Datei -> Beenden.

Importiert PySide6 erst innerhalb der Funktionen, damit das Modul
selbst ohne installiertes PySide6 importierbar bleibt (für Tests).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from verordnungsampel import i18n
from verordnungsampel.gui import strings_de as S


ICONS_DIR = Path(__file__).resolve().parent / "icons"


def _find_icon(name: str) -> str:
    """Pfad zu einem mitgelieferten Icon-Asset."""
    path = ICONS_DIR / name
    return str(path)


def _find_window_icon() -> str:
    """Bevorzugt Windows-ICO fuer App/Fenster, faellt sonst auf SVG zurueck."""
    ico_path = ICONS_DIR / "ampel.ico"
    if ico_path.exists():
        return str(ico_path)
    return _find_icon("ampel.svg")


def _require_pyside6():
    """Importiert PySide6 oder wirft einen benutzerfreundlichen Fehler."""
    try:
        import PySide6  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment-abhängig
        raise SystemExit(
            "Die GUI benötigt PySide6. Installation:\n"
            "    pip install 'PySide6>=6.6.0'\n"
            f"Originalfehler: {exc}"
        )


class TrayController:
    """Verwaltet Tray-Icon + Hauptfenster.

    Diese Klasse wird erst konstruiert, wenn PySide6 bereits importiert ist
    (im ``run_gui``). Sie hält Referenzen auf QApplication, QSystemTrayIcon,
    QMenu und das Hauptfenster und wechselt bei Bedarf das Tray-Icon
    (grau -> grün/gelb/rot), wenn ein Check-Ergebnis vorliegt.
    """

    def __init__(self, app, main_window) -> None:
        from PySide6.QtGui import QIcon, QAction
        from PySide6.QtWidgets import QMenu, QSystemTrayIcon

        self.app = app
        self.main_window = main_window

        self.icons = {
            "grey": QIcon(_find_icon("tray_grey.svg")),
            "green": QIcon(_find_icon("tray_green.svg")),
            "yellow": QIcon(_find_icon("tray_yellow.svg")),
            "red": QIcon(_find_icon("tray_red.svg")),
        }

        self.tray = QSystemTrayIcon(self.icons["grey"], parent=app)
        self.tray.setToolTip(S.TRAY_TOOLTIP)

        self.menu = QMenu()
        self.action_show = QAction(S.TRAY_SHOW, self.menu)
        self.action_show.triggered.connect(self.toggle_window)
        self.menu.addAction(self.action_show)

        self.menu.addSeparator()

        self.action_quit = QAction(S.TRAY_QUIT, self.menu)
        self.action_quit.triggered.connect(self.request_quit)
        self.menu.addAction(self.action_quit)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)
        self.tray.show()

        # Main-Window über Tray-Controller beenden lassen
        self.main_window.quit_requested.connect(self.request_quit)
        self.main_window.ampel_changed.connect(self.set_ampel_icon)

    # --------------------------------------------------------------
    # Tray-Actions
    # --------------------------------------------------------------

    def _on_activated(self, reason) -> None:
        from PySide6.QtWidgets import QSystemTrayIcon

        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_window()

    def toggle_window(self) -> None:
        """Fenster zeigen/verbergen."""
        if self.main_window.isVisible() and not self.main_window.isMinimized():
            self.main_window.hide()
            self.action_show.setText(S.TRAY_SHOW)
        else:
            self.main_window.showNormal()
            self.main_window.raise_()
            self.main_window.activateWindow()
            self.action_show.setText(S.TRAY_HIDE)

    def request_quit(self) -> None:
        """Echtes Beenden der Anwendung (Tray-Menü oder File -> Quit)."""
        self.main_window.allow_close = True
        self.tray.hide()
        self.app.quit()

    # --------------------------------------------------------------
    # Icon-Feedback
    # --------------------------------------------------------------

    def _update_tray_tooltip(self, key: str) -> None:
        """Spiegelt den kompakten Tray-Status in einen lesbaren Tooltip."""
        state_text = {
            "green": S.AMPEL_GRUEN,
            "yellow": S.AMPEL_GELB,
            "red": S.AMPEL_ROT,
        }.get(key)
        if state_text:
            self.tray.setToolTip(i18n.t("TRAY_TOOLTIP_STATUS", state=state_text))
        else:
            self.tray.setToolTip(S.TRAY_TOOLTIP)

    def set_ampel_icon(self, farbe: str) -> None:
        """Setzt das Tray-Icon nach Ampelfarbe.

        Args:
            farbe: ``"gruen"``, ``"gelb"``, ``"rot"`` oder ``""``/``None``.
        """
        key = {
            "gruen": "green",
            "gelb": "yellow",
            "rot": "red",
        }.get((farbe or "").lower(), "grey")
        self.tray.setIcon(self.icons[key])
        self._update_tray_tooltip(key)


def run_gui(argv: Optional[list] = None) -> int:
    """Startet die GUI und blockiert bis zum Quit.

    Returns:
        Exit-Code von ``QApplication.exec``.
    """
    _require_pyside6()

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

    from verordnungsampel.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication(argv or sys.argv)
    app.setApplicationName(S.APP_TITLE)
    app.setQuitOnLastWindowClosed(False)  # Tray darf App am Leben halten
    app.setWindowIcon(QIcon(_find_window_icon()))

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            S.APP_TITLE,
            "Kein Systray auf diesem System verfügbar. "
            "Die App würde dann nicht wie vorgesehen laufen.",
        )
        return 1

    # Erststart-Acknowledgement (Haftungsgutachten 10.2) - muss VOR
    # MainWindow angezeigt werden.
    from verordnungsampel.audit.compliance_log import ComplianceLog
    from verordnungsampel.db.connection import open_database
    from verordnungsampel.gui.disclaimer_dialog import ensure_disclaimer_accepted

    conn, _ = open_database()
    log = ComplianceLog()
    try:
        accepted = ensure_disclaimer_accepted(conn, log)
    finally:
        log.close()
        conn.close()
    if not accepted:
        return 0

    window = MainWindow()
    controller = TrayController(app, window)  # noqa: F841 - lebt am app
    window.show()

    return app.exec()


__all__ = ["run_gui", "TrayController"]
