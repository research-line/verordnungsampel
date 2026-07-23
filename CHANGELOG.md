# Changelog / Änderungsprotokoll

Alle wesentlichen Änderungen an diesem Projekt werden hier dokumentiert.
Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.1.0/).

## [Unreleased]

### Geändert / Changed
- Das kompakte Tray-Ampelsymbol exponiert den aktuellen Ampelstatus jetzt
  zusätzlich im Tooltip (`GRÜN`, `GELB`, `ROT`) statt dauerhaft nur den
  statischen App-Namen zu zeigen. Dadurch bleibt die ikonische Systray-UI
  unverändert, ist für Screenreader- und Tastaturnutzung aber klarer.

### Hinzugefügt / Added
- `llms.txt` als maschinenlesbarer Projektkontext mit klarer Nicht-MDSW-,
  Nicht-CDS- und Research-Use-Only-Abgrenzung.
- Zusätzlicher README-Screenshot `README/screenshots/main-window.png` für das
  eigentliche Ampel-Hauptfenster; der vorhandene Disclaimer-Screenshot bleibt als
  Sicherheitshinweis sichtbar.
- GitHub Actions für Windows-Testläufe sowie Stale-/Welcome-Community-Workflows.
- `EXPORTFORMAT.md` als Planungsgrundlage für dateibasierte, pseudonymisierte Fallbündel und Regelwerks-Snapshots ohne Cloud-Synchronisierung.
- PySide6-basierte Tray-GUI (Companion-Modus neben Praxisverwaltungssystemen)
- Vollständiger AM-RL-Seed-Datensatz (Anlagen III, V, VI-A, VI-B)
- Coverage-Analyse für Ampel-Entscheidungen: `coverage --cases cases.json`
  berechnet C(S)=erklärte Fälle/alle Fälle mit Regel-Treffern und Default-Grün-Liste
- i18n-Infrastruktur (DE/EN): JSON-basierte Übersetzungen unter
  `data/translations/de.json` und `data/translations/en.json`, neues Modul
  `verordnungsampel.i18n` mit `t()`, `set_language()`, `get_language()`,
  `available_languages()`. Schema angelehnt an Geiger 2026 (DOI 10.5281/zenodo.18736725, MIT).
  Bestehender Code (`from gui import strings_de as S; S.APP_TITLE`) wird per
  PEP 562-Bridge weiterhin unterstützt und reagiert auf Sprachwechsel.
- Erstes KI-basiertes Rechtsgutachten: Status als Informationswerk vs. MDSW
- DSGVO-Konzept (Verarbeitungsverzeichnis, TOMs, Betroffenenrechte, Löschkonzept)
- GitHub-Pflichtdateien (CODE_OF_CONDUCT, SECURITY, CONTRIBUTING, FUNDING)
- Reproduzierbarer lokaler Windows-Build via `build_exe.bat` und `verordnungsampel_gui.py`
- Gitignore-Abdeckung für lokale Build-Artefakte, Secrets, Credentials und Test-Locks erweitert
- SQLite-Schema v2 mit Relationstabellen für AM-RL-, Praxisbesonderheits- und
  Regelwerks-Patterns zu bekannten ICD-/ATC-Codes
- Seed-Loader füllt diese Code-Relationen nach jedem `init` idempotent neu
- Test-Suite-Wachstum: 24 neue Tests in `tests/test_i18n.py`
  (Lazy-Load, Fallback DE↔EN, Format-Substitution, Bridge-Kompatibilität,
  Konsistenz DE/EN-Keysets)
- Test-Suite-Wachstum: 2 neue DB-Tests für Schema-v2-Relationen und
  idempotente Pattern-Expansion
- iOS-PWA-Meta-Tags im Web-Prototyp: `viewport-fit=cover`, `theme-color #355f3d`,
  `apple-mobile-web-app-status-bar-style: default`, `apple-mobile-web-app-title: VA-Check`
  (P3 Mobile PWA-Smoke gemäß PORTIERUNGSPLAN.md)
- `apple-touch-icon-180.png` für iOS Add-to-Home-Screen (aus `Icon-192.png` via Pillow LANCZOS skaliert)
- Safe-Area-Padding: `env(safe-area-inset-*)` im Body-CSS für Notch/Home-Indicator-Freihaltebereich
- Apple HIG Touch-Target: `min-height: 44px; min-width: 44px` am Submit-Button
- Service Worker `CACHE_NAME` auf `verordnungsampel-v2` angehoben; `{ignoreSearch: true}`
  bei `caches.match()`; `apple-touch-icon-180.png` im Precache-Manifest ergänzt
- 9 Tests in `tests/test_web_app.py` für iOS-PWA-Anforderungen: viewport-fit, theme-color,
  apple-status-bar-style, apple-title, apple-touch-icon href/sizes, manifest display:standalone,
  Icon-Endpoint-Status-200, Safe-Area-CSS (168 Tests gesamt)

### Geändert / Changed
- README, `llms.txt`, `docs/WEB_MVP.md` und Paketmetadaten mit kanonischer
  Um:bruch-Projektseite, lokalen PWA-/Web-Nutzungshinweisen und zusätzlichen
  AM-RL-/G-BA-/Arzneimittel-Richtlinie-Suchankern synchronisiert.
- README und `llms.txt` markieren den aktuellen kanonischen GitHub-Pfad
  `um-bruch/verordnungsampel`, den früheren Redirect-Pfad
  `research-line/verordnungsampel` und den aktuellen ST-001-Kontext unter
  `um-bruch/regressangst`.
- README-Discoverability für `VerordnungsAmpel`, AM-RL/G-BA, ICD-10-GM/ATC,
  PRISCUS 2.0, Praxisbesonderheiten und local-first Health-Policy-Research
  verbessert, ohne Wirk- oder Validierungsversprechen zu ergänzen.
- Paketbeschreibung, Keywords und Classifiers in `pyproject.toml` auf
  Research-Use-Only und Information-Analysis statt Medical-Software-Positionierung
  geschärft.
- Ordner-Lifecycle: DEV → PreGit → GO-PRI; GitHub-Sichtbarkeit ist inzwischen öffentlich.
- Repository-URL: github.com/um-bruch/verordnungsampel
- Der lokale `.SOFTWARE`-Ordnername bleibt bis zur nächsten Lifecycle-Bereinigung unverändert.
- Zweckbestimmung neu formuliert: **"Regress-Prävention"** als Vermarktungsbegriff fallengelassen (Risiko § 444 BGB Zusicherung, § 5 UWG irreführende Werbung, MDR-Zweckbestimmung). Neu: "Softwareentwurf zur Anzeige bekannter Regress-Risikoindikatoren aus öffentlichen Regelwerken — zu Forschungs- und Weiterentwicklungszwecken, ohne Gewähr." Betroffen: README, NOTICE, pyproject.toml, GUI-Strings, DSGVO-Konzept, Marktvergleich.
- Desktop-Packaging dokumentiert: lokaler PyInstaller-Onedir-Build mit Seed-Daten und Tray-Icons
- Öffentliche Konzept- und Ressourcen-Dokumentation um Hinweise auf lokale Referenzspiegel und interne Projektnamen bereinigt.
- README, User-Guide und Seed-Dokumentation auf den aktuellen Stand der 151 Tests, die Quellen-Ansicht und den manuellen AM-RL-Update-Check gebracht.
- README-Testzahl auf 168 / 168 korrigiert (beide Sprachsektionen); `llms.txt` auf Standardformat mit `## Audience`, `## Search Phrases` und `## Last-checked` gebracht.
- README-Teststand auf 154 lokale Tests aktualisiert.
- Repo-Hygiene ergänzt: `.gitattributes` für stabile Zeilenenden und `.gitignore` für SQLite-Sidecars, Coverage-, Cache- und Zertifikatsartefakte.
- Repo-Hygiene nachgezogen: lokale Portierungspläne und interne Steuerungsdateien bleiben aus dem öffentlichen GitHub-Repo heraus; `llms.txt` und Web-MVP-Doku verweisen nur noch auf öffentliche Einstiegspunkte.
- Repo-Hygiene (Review-Loop 2026-07-23): `.gitignore` um `_archive/` und `*.bak`
  ergänzt; zwei verwaiste Bugsweep-Backup-Dateien aus `src/verordnungsampel/web/`
  dorthin verschoben, damit Wegwerf-Artefakte nicht mehr im Working Tree bzw.
  in `git status` auftauchen.

### Behoben / Fixed
- GUI-RichText-Ausgaben in Check- und Regelwerke-Tab escapen jetzt auch
  DB-/Quellenfelder, Container, Praxisbesonderheiten, Fehlertexte und
  Quellen-URLs vor `setHtml`.
- Deutsche Nutzertexte im Regelwerke-Tab nutzen echte Umlaute für "angestoßen" und "Einträge".
- Marketing-Blacklist: "KI" als interne Abkürzung für Kontraindikation ersetzt (Verwechslungsgefahr mit AI/KI); "KI-gestützt" → "KI-basiert" in USER-GUIDE

## [0.1.0] - 2026-04-08

### Hinzugefügt / Added
- MVP-Kern mit allen 5 KONZEPT-Funktionen
- SQLite-Regelwerk (`db/schema.py`, `db/seed.py`, `db/connection.py`)
- Ampel-Engine GRÜN/GELB/ROT mit Container-Logik (`engine/evaluator.py`, `engine/rules.py`)
- Kryptografische Hash-Chain als Compliance-Log (`audit/compliance_log.py`)
- Strukturierte Begründungspflicht als Hierarchical State Machine (`engine/justification_fsm.py`)
  Pattern adaptiert aus Geiger (2026) *"An Integrated Multiaxial Model for Computer-Assisted Psychiatric Diagnosis"*, Section 9 (DOI 10.5281/zenodo.18736725)
- Vorab-Klärungs-Workflow container-sensitiv (`output/vorab_workflow.py`):
  PFLICHT_ANTRAG / VERBOTEN_HINWEIS / STELLUNGNAHME / KEINE_AKTION
- Praxisbesonderheiten-Erkennung + Quartalsreminder (`engine/praxisbesonderheit.py`)
- CLI-Frontend mit 7 Subcommands: `init`, `check`, `log`, `verify`, `justify`, `workflow`, `remind`
- Interaktives Demo-Menü (`start.bat` mit 14 Optionen)
- Seed-Daten MVP-Umfang: 10 Quellen, 13 ICD-10, 16 ATC, 4 AM-RL-Anlagen, 2 Praxisbesonderheiten, 10 Regeln
- Test-Suite: 86/86 tests passed
- Projekt-Dokumentation: KONZEPT.md, README.md, CODE_AUDIT.md, RESOURCES_DIAGNOSTIC_PAPER.md

### Architekturentscheidungen
- Python-Stdlib-only für MVP-Kern (sqlite3, json, hashlib, argparse, datetime)
- GPL-3.0-Lizenz
- Kein PVS, kein Medical Device, keine Patientendaten (nur ICD- und ATC-Codes)
- Lokale Speicherung in SQLite (`%APPDATA%\VerordnungsAmpel\regelwerk.db`)
