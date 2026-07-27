# Source-Plattform-Smokes

Dieser Prüfpfad erfüllt den lokalen Teil von `TW-VA-05`: Er schützt die
plattformneutrale Source-Basis auf Windows, macOS und Linux. Er ist weder ein
Installer-, Store- noch ein Medizinproduktnachweis.

## Matrix

Der GitHub-Workflow `verordnungsampel-tests.yml` läuft mit Python 3.11 auf
`windows-latest`, `macos-latest` und `ubuntu-latest`. Jede Zelle installiert
`.[dev,gui,web]`, kompiliert `src` und `tests` und führt die gesamte Pytest-Suite
unter `QT_QPA_PLATFORM=offscreen` aus.

Die gezielten Source-Smokes in `tests/test_source_platform_smoke.py` prüfen:

- CLI: Ein `check` mit eigener temporärer Datenablage, UTF-8-JSON und ohne
  Compliance-Log-Eintrag.
- GUI: Import der PySide6-Module und der mitgelieferten Fenster-Assets, ohne
  einen Tray oder ein sichtbares Fenster zu starten.
- Web: Start eines temporären Loopback-Servers und HTTP-Readback von `/health`.

## Lokal ausführen

```bash
python -m pip install -e ".[dev,gui,web]"
python -m pytest -q tests/test_source_platform_smoke.py
```

Der Web-Smoke bindet ausschließlich an `127.0.0.1`. Die CLI verwendet im Test
einen temporären Nutzerordner; es werden keine realen Patienten- oder
Praxisdaten benötigt oder erzeugt.

## Grenzen

- Ein vollständiger Windows-EXE-/PyInstaller-Smoke bleibt ein separater
  Release-Schritt.
- macOS-Notarisierung, Linux-Pakete und native Tray-Interaktion sind nicht Teil
  dieses Source-Smokes.
- Der Workflow belegt erst nach einem erfolgreichen CI-Lauf die jeweilige
  Runner-Plattform; bis dahin ist die Matrix eine reproduzierbare Prüfvorgabe.
