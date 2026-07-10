"""Lokaler Flask-Prototyp fuer die Browser-/PWA-Linie.

Der Prototyp fuehrt bewusst keine zweite Fachlogik ein, sondern nutzt
dieselben Evaluations- und Praxisbesonderheitsfunktionen wie CLI und GUI.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from flask import Flask, Response, jsonify, render_template_string, request

from verordnungsampel import __version__
from verordnungsampel.db.connection import open_database
from verordnungsampel.db.seed import ensure_seed_data
from verordnungsampel.engine.evaluator import evaluate
from verordnungsampel.engine.justification_fsm import (
    JustificationAnswers,
    JustificationError,
    JustificationFSM,
)
from verordnungsampel.engine.praxisbesonderheit import find_matching
from verordnungsampel.output import WorkflowContext, build_workflow

MANIFEST = {
    "name": "VerordnungsAmpel",
    "short_name": "VA-Check",
    "description": "Lokaler Ampel-Check für Verordnungsrisiken aus öffentlichen Regelwerken.",
    "start_url": "/",
    "id": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": "#f5f1e8",
    "theme_color": "#355f3d",
    "lang": "de-DE",
    "icons": [
        {"src": "/static/icons/Icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "/static/icons/Icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {
            "src": "/static/icons/Icon-maskable-192.png",
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "maskable",
        },
        {
            "src": "/static/icons/Icon-maskable-512.png",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "maskable",
        },
    ],
}

SW_JS = """\
const CACHE_NAME = "verordnungsampel-v2";
const STATIC_ASSETS = [
  "/manifest.webmanifest",
  "/offline.html",
  "/static/icons/Icon-192.png",
  "/static/icons/Icon-512.png",
  "/static/icons/Icon-maskable-192.png",
  "/static/icons/Icon-maskable-512.png",
  "/static/icons/apple-touch-icon-180.png",
];
self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((c) => c.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() => caches.match("/offline.html"))
    );
    return;
  }
  event.respondWith(
    caches.match(event.request, {ignoreSearch: true}).then((cached) => cached || fetch(event.request))
  );
});
"""

DISCLAIMER_TEXT = (
    "Informationswerk, nicht klinisch validiert, kein Medizinprodukt. "
    "Die VerordnungsAmpel ersetzt nicht die ärztliche Prüfung im Einzelfall."
)

AMPel_LABELS = {
    "gruen": "Grün",
    "gelb": "Gelb",
    "rot": "Rot",
}

HTML_TEMPLATE = """
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>VerordnungsAmpel Web-Prototyp</title>
  <link rel="manifest" href="/manifest.webmanifest">
  <meta name="theme-color" content="#355f3d">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="VA-Check">
  <link rel="apple-touch-icon" sizes="180x180" href="/static/icons/apple-touch-icon-180.png">
  <style>
    :root {
      --bg: linear-gradient(180deg, #f5f1e8 0%, #eef3e4 100%);
      --panel: rgba(255, 255, 255, 0.9);
      --border: rgba(38, 55, 43, 0.12);
      --text: #1e2a20;
      --muted: #526154;
      --green: #2f7d32;
      --yellow: #b98900;
      --red: #b53a2d;
      --shadow: 0 18px 40px rgba(34, 52, 39, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--text);
      background: var(--bg);
      min-height: 100vh;
      padding-top: env(safe-area-inset-top, 0px);
      padding-right: env(safe-area-inset-right, 0px);
      padding-bottom: env(safe-area-inset-bottom, 0px);
      padding-left: env(safe-area-inset-left, 0px);
    }
    main {
      width: min(980px, calc(100% - 2rem));
      margin: 2rem auto 3rem;
    }
    .hero, .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 24px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(8px);
    }
    .hero {
      padding: 1.75rem;
      margin-bottom: 1rem;
    }
    .hero h1 {
      margin: 0 0 0.5rem;
      font-size: clamp(2rem, 4vw, 3rem);
      line-height: 1;
    }
    .hero p, .hero li, .card p, .card li {
      color: var(--muted);
      line-height: 1.5;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-top: 1rem;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.45rem 0.8rem;
      border-radius: 999px;
      background: rgba(47, 125, 50, 0.08);
      color: var(--text);
      font-size: 0.95rem;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1rem;
      margin-top: 1rem;
    }
    .card {
      padding: 1.25rem;
    }
    label {
      display: block;
      font-weight: 600;
      margin-bottom: 0.35rem;
    }
    input, textarea {
      width: 100%;
      border: 1px solid rgba(34, 52, 39, 0.16);
      border-radius: 14px;
      padding: 0.85rem 1rem;
      font: inherit;
      background: rgba(255, 255, 255, 0.96);
      color: var(--text);
    }
    textarea {
      min-height: 7.5rem;
      resize: vertical;
    }
    input:focus, textarea:focus {
      outline: 2px solid rgba(47, 125, 50, 0.25);
      border-color: rgba(47, 125, 50, 0.4);
    }
    .checkbox {
      display: flex;
      gap: 0.7rem;
      align-items: flex-start;
      margin-top: 1rem;
      color: var(--muted);
      font-weight: 500;
      line-height: 1.45;
    }
    .checkbox input {
      width: auto;
      margin-top: 0.2rem;
    }
    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      margin-top: 1rem;
    }
    button {
      border: 0;
      border-radius: 14px;
      padding: 0.9rem 1.1rem;
      font: inherit;
      font-weight: 700;
      color: white;
      background: linear-gradient(135deg, #355f3d, #4a7b52);
      cursor: pointer;
      min-height: 44px;
      min-width: 44px;
    }
    .hint {
      margin-top: 0.75rem;
      font-size: 0.95rem;
    }
    .alert {
      padding: 0.9rem 1rem;
      border-radius: 16px;
      margin-top: 1rem;
      font-weight: 600;
    }
    .alert.error {
      background: rgba(181, 58, 45, 0.12);
      color: #7f261e;
    }
    .alert.success {
      background: rgba(47, 125, 50, 0.12);
      color: #214d27;
    }
    .result-head {
      display: flex;
      justify-content: space-between;
      gap: 1rem;
      align-items: center;
      margin-bottom: 1rem;
      flex-wrap: wrap;
    }
    .status-badge {
      font-size: 1rem;
      font-weight: 700;
      padding: 0.55rem 0.95rem;
      border-radius: 999px;
      color: white;
    }
    .status-badge.gruen { background: var(--green); }
    .status-badge.gelb { background: var(--yellow); }
    .status-badge.rot { background: var(--red); }
    .rule-list, .pb-list {
      display: grid;
      gap: 0.8rem;
      margin-top: 1rem;
    }
    .rule {
      border: 1px solid var(--border);
      border-left: 6px solid var(--green);
      border-radius: 18px;
      padding: 0.9rem 1rem;
      background: rgba(255, 255, 255, 0.82);
    }
    .rule.gelb { border-left-color: var(--yellow); }
    .rule.rot { border-left-color: var(--red); }
    .rule h3 {
      margin: 0 0 0.45rem;
      font-size: 1rem;
    }
    .rule p {
      margin: 0.2rem 0;
    }
    .footer-note {
      margin-top: 1rem;
      font-size: 0.95rem;
      color: var(--muted);
    }
    code {
      font-family: "Cascadia Code", "Consolas", monospace;
      font-size: 0.95em;
    }
    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      border-radius: 16px;
      background: rgba(30, 42, 32, 0.06);
      border: 1px solid var(--border);
      padding: 1rem;
      color: var(--text);
      line-height: 1.45;
    }
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h1>VerordnungsAmpel</h1>
      <p>Lokaler Browser-Prototyp für die geplante Web/PWA-Linie. Die bestehende Ampel-Engine, die Praxisbesonderheiten und die Seed-Daten werden direkt aus dem Python-Kern genutzt.</p>
      <div class="meta">
        <span class="pill">Version {{ version }}</span>
        <span class="pill">Nur lokal</span>
        <span class="pill">Kein Persistenz-Workflow im Browser</span>
      </div>
    </section>

    <section class="card">
      <form method="post" novalidate>
        <div class="grid">
          <div>
            <label for="icd">ICD-10-GM</label>
            <input id="icd" name="icd" value="{{ form_data.icd }}" placeholder="z. B. I10" required>
          </div>
          <div>
            <label for="atc">ATC</label>
            <input id="atc" name="atc" value="{{ form_data.atc }}" placeholder="z. B. C09AA02" required>
          </div>
          <div>
            <label for="alter">Alter (optional)</label>
            <input id="alter" name="alter" value="{{ form_data.alter }}" placeholder="z. B. 72" inputmode="numeric">
          </div>
        </div>
        <div class="button-row">
          <button type="submit">Prüfung ausführen</button>
        </div>
        <p class="hint">{{ disclaimer }}</p>
      </form>

      {% if error %}
        <div class="alert error">{{ error }}</div>
      {% endif %}
    </section>

    {% if result %}
      <section class="card" style="margin-top: 1rem;">
        <div class="result-head">
          <div>
            <h2 style="margin: 0 0 0.35rem;">Prüfergebnis</h2>
            <p style="margin: 0;">ICD <code>{{ result.icd }}</code> · ATC <code>{{ result.atc }}</code>{% if result.alter is not none %} · Alter {{ result.alter }}{% endif %}</p>
          </div>
          <span class="status-badge {{ result.gesamt }}">{{ ampel_labels[result.gesamt] }}</span>
        </div>

        {% if result.container_hinweise %}
          <p><strong>Container-Hinweise:</strong> {{ result.container_hinweise | join(", ") }}</p>
        {% endif %}

        <div class="rule-list">
          {% for treffer in result.treffer %}
            <article class="rule {{ treffer.ampel }}">
              <h3>{{ ampel_labels[treffer.ampel] }} · {{ treffer.regel }}</h3>
              <p>{{ treffer.begruendung }}</p>
              {% if treffer.quelle %}
                <p><strong>Quelle:</strong> {{ treffer.quelle.kuerzel }} — {{ treffer.quelle.titel }}{% if treffer.quelle.stand %} (Stand {{ treffer.quelle.stand }}){% endif %}</p>
              {% endif %}
              {% if treffer.container %}
                <p><strong>Container:</strong> {{ treffer.container }}</p>
              {% endif %}
            </article>
          {% endfor %}
        </div>

        {% if result.praxisbesonderheiten %}
          <h2 style="margin-top: 1.35rem;">Praxisbesonderheiten</h2>
          <div class="pb-list">
            {% for pb in result.praxisbesonderheiten %}
              <article class="rule gruen">
                <h3>{{ pb.bezeichnung }}</h3>
                <p>ATC-Muster: <code>{{ pb.atc_pattern }}</code>{% if pb.icd_pattern %} · ICD-Muster: <code>{{ pb.icd_pattern }}</code>{% endif %}</p>
                {% if pb.quelle %}
                  <p><strong>Quelle:</strong> {{ pb.quelle.kuerzel }} — {{ pb.quelle.titel }}</p>
                {% endif %}
              </article>
            {% endfor %}
          </div>
        {% endif %}

        <p class="footer-note">API-Pendant für spätere PWA-Schichten: <code>POST /api/check</code></p>
      </section>

      <div class="grid">
        <section class="card">
          <h2 style="margin-top: 0;">Strukturierte Begründung</h2>
          <p>Lokale Web-Maske für den HSM-Pfad aus der CLI. Sie validiert die Angaben, schreibt aber im Browser-Prototyp keinen Compliance-Log.</p>
          <form method="post" novalidate>
            <input type="hidden" name="web_action" value="justify">
            <input type="hidden" name="icd" value="{{ result.icd }}">
            <input type="hidden" name="atc" value="{{ result.atc }}">
            <input type="hidden" name="alter" value="{{ result.alter or '' }}">
            <label for="diagnose">Diagnose und Verlauf</label>
            <textarea id="diagnose" name="diagnose" placeholder="Diagnose, Schweregrad und Verlauf festhalten">{{ followup_data.diagnose }}</textarea>

            <label for="vorbehandlung">Vorbehandlung</label>
            <textarea id="vorbehandlung" name="vorbehandlung" placeholder="Substanzen, Dauer, Dosis und Ergebnis">{{ followup_data.vorbehandlung }}</textarea>

            <label for="therapieversagen">Therapieversagen / Kontraindikation</label>
            <textarea id="therapieversagen" name="therapieversagen" placeholder="Warum war die Vorbehandlung nicht ausreichend?">{{ followup_data.therapieversagen }}</textarea>

            <label for="praxisbesonderheit">Praxisbesonderheit (optional)</label>
            <textarea id="praxisbesonderheit" name="praxisbesonderheit" placeholder="Leer lassen, wenn keine einschlägige Praxisbesonderheit vorliegt">{{ followup_data.praxisbesonderheit }}</textarea>

            <details>
              <summary>BSG-Off-Label-Kriterien</summary>
              <label for="schwerwiegende_erkrankung">Schwerwiegende Erkrankung</label>
              <textarea id="schwerwiegende_erkrankung" name="schwerwiegende_erkrankung">{{ followup_data.schwerwiegende_erkrankung }}</textarea>
              <label for="keine_alternative">Keine Alternative</label>
              <textarea id="keine_alternative" name="keine_alternative">{{ followup_data.keine_alternative }}</textarea>
              <label for="begruendete_erfolgsaussicht">Begründete Erfolgsaussicht</label>
              <textarea id="begruendete_erfolgsaussicht" name="begruendete_erfolgsaussicht">{{ followup_data.begruendete_erfolgsaussicht }}</textarea>
            </details>

            <label class="checkbox">
              <input type="checkbox" name="confirm" value="on"{% if followup_data.confirm %} checked{% endif %}>
              Ich bestätige, dass die Angaben im Moment der Verordnung zutreffen.
            </label>
            <div class="button-row">
              <button type="submit">Begründung prüfen</button>
            </div>
          </form>

          {% if justification_result %}
            <div class="alert success">Begründung validiert. Erforderliche Schritte: {{ justification_result.required_states | join(", ") if justification_result.required_states else "keine" }}.</div>
          {% endif %}
        </section>

        <section class="card">
          <h2 style="margin-top: 0;">Vorab-Workflow</h2>
          <p>Lokale Web-Maske für Antrag, Stellungnahme oder internen Hinweis. Patientendaten sollen pseudonymisiert bleiben.</p>
          <form method="post" novalidate>
            <input type="hidden" name="web_action" value="workflow">
            <input type="hidden" name="icd" value="{{ result.icd }}">
            <input type="hidden" name="atc" value="{{ result.atc }}">
            <input type="hidden" name="alter" value="{{ result.alter or '' }}">
            <div class="grid">
              <div>
                <label for="kk">Krankenkasse</label>
                <input id="kk" name="kk" value="{{ workflow_data.kk }}" placeholder="z. B. Musterkasse">
              </div>
              <div>
                <label for="patient">Patienten-Kürzel</label>
                <input id="patient" name="patient" value="{{ workflow_data.patient }}" placeholder="z. B. P-4711">
              </div>
              <div>
                <label for="praxis">Praxis</label>
                <input id="praxis" name="praxis" value="{{ workflow_data.praxis }}" placeholder="z. B. Musterpraxis">
              </div>
              <div>
                <label for="arzt">Arzt / Ärztin</label>
                <input id="arzt" name="arzt" value="{{ workflow_data.arzt }}" placeholder="z. B. Dr. med. Muster">
              </div>
            </div>
            <div class="button-row">
              <button type="submit">Workflow-Text erzeugen</button>
            </div>
          </form>

          {% if workflow_result %}
            <div class="alert success">Workflow-Typ: {{ workflow_result.workflow.workflow_type }}</div>
            <pre>{{ workflow_result.rendered_text }}</pre>
          {% endif %}
        </section>
      </div>
    {% endif %}
  </main>
  <script>
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js");
    }
  </script>
</body>
</html>
"""


def _parse_alter(raw_value: Any) -> int | None:
    """Parst das optionale Alter aus Formular- oder JSON-Daten."""
    if raw_value in (None, ""):
        return None
    try:
        alter = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Alter muss eine ganze Zahl sein.") from exc
    if alter < 0:
        raise ValueError("Alter darf nicht negativ sein.")
    return alter


def _ensure_seed_data(conn: sqlite3.Connection) -> None:
    """Laedt Seed-Daten beim ersten Web-Zugriff automatisch nach."""
    ensure_seed_data(conn)


def _evaluate_case(
    icd: str | None,
    atc: str | None,
    alter: Any = None,
    *,
    db_path: str | None = None,
):
    """Fuehrt die gemeinsame Fachlogik aus und liefert rohe Ergebnisobjekte."""
    icd_norm = (icd or "").strip().upper()
    atc_norm = (atc or "").strip().upper()
    if not icd_norm:
        raise ValueError("ICD-10-GM-Code fehlt.")
    if not atc_norm:
        raise ValueError("ATC-Code fehlt.")

    alter_value = _parse_alter(alter)
    conn, _ = open_database(db_path)
    try:
        _ensure_seed_data(conn)
        ergebnis = evaluate(icd_norm, atc_norm, alter=alter_value, conn=conn)
        praxisbesonderheiten = find_matching(icd_norm, atc_norm, conn=conn)
    finally:
        conn.close()
    return ergebnis, praxisbesonderheiten


def _serialize_check(ergebnis: Any, praxisbesonderheiten: list[Any]) -> dict[str, Any]:
    """Serialisiert Ampel- und Praxisbesonderheiten-Daten fuer Browser/API."""
    payload = ergebnis.to_dict()
    payload["container_hinweise"] = ergebnis.container_hinweise
    payload["praxisbesonderheiten"] = [pb.to_dict() for pb in praxisbesonderheiten]
    return payload


def _run_check(
    icd: str | None,
    atc: str | None,
    alter: Any = None,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Fuehrt eine Browser-Pruefung gegen die bestehende Fachlogik aus."""
    ergebnis, praxisbesonderheiten = _evaluate_case(icd, atc, alter, db_path=db_path)
    return _serialize_check(ergebnis, praxisbesonderheiten)


def _is_truthy(value: Any) -> bool:
    """Normalisiert Checkbox-/JSON-Werte fuer den Confirm-Schritt."""
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "ja", "on"}
    return False


def _normalize_justification_answers(raw: Any) -> JustificationAnswers:
    """Mappt Web-Formular- oder JSON-Antworten auf den FSM-Vertrag."""
    if not isinstance(raw, dict):
        raw = {}
    bsg = raw.get("bsg_off_label")
    if not isinstance(bsg, dict):
        bsg = {
            "schwerwiegende_erkrankung": raw.get("schwerwiegende_erkrankung", ""),
            "keine_alternative": raw.get("keine_alternative", ""),
            "begruendete_erfolgsaussicht": raw.get("begruendete_erfolgsaussicht", ""),
        }
    return JustificationAnswers(
        data={
            "diagnose": raw.get("diagnose", ""),
            "vorbehandlung": raw.get("vorbehandlung", ""),
            "therapieversagen": raw.get("therapieversagen", ""),
            "bsg_off_label": bsg,
            "praxisbesonderheit": raw.get("praxisbesonderheit", ""),
            "confirm": _is_truthy(raw.get("confirm")),
        }
    )


def _run_justification(
    icd: str | None,
    atc: str | None,
    alter: Any = None,
    answers: Any = None,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Validiert eine strukturierte Begruendung fuer den Web/PWA-Pfad."""
    ergebnis, praxisbesonderheiten = _evaluate_case(icd, atc, alter, db_path=db_path)
    fsm = JustificationFSM(ergebnis)
    justification = fsm.run(_normalize_justification_answers(answers))
    return {
        "result": _serialize_check(ergebnis, praxisbesonderheiten),
        "required_steps": [step.state.value for step in fsm.iter_steps()],
        "justification": justification.to_dict(),
    }


def _workflow_context_from_mapping(raw: Any) -> WorkflowContext:
    """Erzeugt den optionalen Workflow-Kontext aus Formular- oder JSON-Daten."""
    if not isinstance(raw, dict):
        raw = {}
    return WorkflowContext(
        praxis_name=raw.get("praxis_name") or raw.get("praxis"),
        praxis_adresse=raw.get("praxis_adresse"),
        arzt_name=raw.get("arzt_name") or raw.get("arzt"),
        bsnr=raw.get("bsnr"),
        lanr=raw.get("lanr"),
        kk_name=raw.get("kk_name") or raw.get("kk"),
        patient_kennung=raw.get("patient_kennung") or raw.get("patient"),
    )


def _run_workflow(
    icd: str | None,
    atc: str | None,
    alter: Any = None,
    context: Any = None,
    *,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Generiert den Vorab-Workflow ueber die bestehende Workflow-Engine."""
    ergebnis, praxisbesonderheiten = _evaluate_case(icd, atc, alter, db_path=db_path)
    output = build_workflow(ergebnis, _workflow_context_from_mapping(context))
    return {
        "result": _serialize_check(ergebnis, praxisbesonderheiten),
        "workflow": output.to_dict(),
        "rendered_text": output.render_full(),
    }


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    """Erstellt die Flask-Anwendung fuer lokalen Browser-Zugriff."""
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE=None,
        DISCLAIMER=DISCLAIMER_TEXT,
    )
    app.json.sort_keys = False
    if test_config:
        app.config.update(test_config)

    @app.get("/health")
    def health() -> Any:
        return jsonify(
            {
                "status": "ok",
                "service": "verordnungsampel-web",
                "version": __version__,
            }
        )

    @app.route("/", methods=["GET", "POST"])
    def index() -> str:
        result = None
        justification_result = None
        workflow_result = None
        error = None
        form_data = {
            "icd": request.form.get("icd", ""),
            "atc": request.form.get("atc", ""),
            "alter": request.form.get("alter", ""),
        }
        followup_data = {
            "diagnose": request.form.get("diagnose", ""),
            "vorbehandlung": request.form.get("vorbehandlung", ""),
            "therapieversagen": request.form.get("therapieversagen", ""),
            "praxisbesonderheit": request.form.get("praxisbesonderheit", ""),
            "schwerwiegende_erkrankung": request.form.get("schwerwiegende_erkrankung", ""),
            "keine_alternative": request.form.get("keine_alternative", ""),
            "begruendete_erfolgsaussicht": request.form.get("begruendete_erfolgsaussicht", ""),
            "confirm": request.form.get("confirm") == "on",
        }
        workflow_data = {
            "kk": request.form.get("kk", ""),
            "patient": request.form.get("patient", ""),
            "praxis": request.form.get("praxis", ""),
            "arzt": request.form.get("arzt", ""),
        }
        if request.method == "POST":
            web_action = request.form.get("web_action", "check")
            try:
                result = _run_check(
                    form_data["icd"],
                    form_data["atc"],
                    form_data["alter"],
                    db_path=app.config.get("DATABASE"),
                )
                if web_action == "justify":
                    payload = _run_justification(
                        form_data["icd"],
                        form_data["atc"],
                        form_data["alter"],
                        followup_data,
                        db_path=app.config.get("DATABASE"),
                    )
                    result = payload["result"]
                    justification_result = payload["justification"]
                elif web_action == "workflow":
                    payload = _run_workflow(
                        form_data["icd"],
                        form_data["atc"],
                        form_data["alter"],
                        workflow_data,
                        db_path=app.config.get("DATABASE"),
                    )
                    result = payload["result"]
                    workflow_result = {
                        "workflow": payload["workflow"],
                        "rendered_text": payload["rendered_text"],
                    }
            except JustificationError as exc:
                error = "Begründung unvollständig: " + "; ".join(exc.errors)
            except ValueError as exc:
                error = str(exc)
        return render_template_string(
            HTML_TEMPLATE,
            ampel_labels=AMPel_LABELS,
            disclaimer=app.config["DISCLAIMER"],
            followup_data=followup_data,
            error=error,
            form_data=form_data,
            justification_result=justification_result,
            result=result,
            workflow_data=workflow_data,
            workflow_result=workflow_result,
            version=__version__,
        )

    @app.post("/api/check")
    def api_check() -> Any:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"status": "error", "error": "JSON-Objekt erwartet."}), 400
        try:
            result = _run_check(
                payload.get("icd"),
                payload.get("atc"),
                payload.get("alter"),
                db_path=app.config.get("DATABASE"),
            )
        except ValueError as exc:
            return jsonify({"status": "error", "error": str(exc)}), 400
        return jsonify(
            {
                "status": "ok",
                "version": __version__,
                "disclaimer": app.config["DISCLAIMER"],
                "result": result,
            }
        )

    @app.post("/api/justify")
    def api_justify() -> Any:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"status": "error", "error": "JSON-Objekt erwartet."}), 400
        try:
            result = _run_justification(
                payload.get("icd"),
                payload.get("atc"),
                payload.get("alter"),
                payload.get("answers", {}),
                db_path=app.config.get("DATABASE"),
            )
        except JustificationError as exc:
            return jsonify({"status": "error", "errors": exc.errors}), 400
        except ValueError as exc:
            return jsonify({"status": "error", "error": str(exc)}), 400
        return jsonify(
            {
                "status": "ok",
                "version": __version__,
                "disclaimer": app.config["DISCLAIMER"],
                **result,
            }
        )

    @app.post("/api/workflow")
    def api_workflow() -> Any:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"status": "error", "error": "JSON-Objekt erwartet."}), 400
        try:
            result = _run_workflow(
                payload.get("icd"),
                payload.get("atc"),
                payload.get("alter"),
                payload.get("context", {}),
                db_path=app.config.get("DATABASE"),
            )
        except ValueError as exc:
            return jsonify({"status": "error", "error": str(exc)}), 400
        return jsonify(
            {
                "status": "ok",
                "version": __version__,
                "disclaimer": app.config["DISCLAIMER"],
                **result,
            }
        )

    @app.get("/manifest.webmanifest")
    def manifest() -> Any:
        return Response(json.dumps(MANIFEST, ensure_ascii=False), mimetype="application/manifest+json")

    @app.get("/sw.js")
    def service_worker() -> Any:
        return Response(SW_JS, mimetype="application/javascript",
                        headers={"Service-Worker-Allowed": "/"})

    @app.get("/offline.html")
    def offline() -> Any:
        return (
            "<html><body><h1>Lokal nicht erreichbar</h1>"
            "<p>Starten Sie den Python-Server neu.</p></body></html>",
            200,
        )

    return app
