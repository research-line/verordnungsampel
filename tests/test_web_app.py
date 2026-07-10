"""Tests fuer den lokalen Flask-Web-Prototyp."""

from verordnungsampel.web.app import create_app


def _make_client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "web-prototype.db"),
        }
    )
    return app.test_client()


def _valid_justification_answers():
    return {
        "diagnose": "Angststoerung mit belastender Symptomatik und dokumentiertem Verlauf",
        "vorbehandlung": "Nicht-medikamentoese Massnahmen und SSRI-Versuch wurden dokumentiert.",
        "therapieversagen": "Vorbehandlung war wegen Unvertraeglichkeit und fehlender Wirkung nicht ausreichend.",
        "praxisbesonderheit": "",
        "bsg_off_label": {
            "schwerwiegende_erkrankung": "Schwerwiegende Erkrankung wurde fachlich dokumentiert.",
            "keine_alternative": "Keine geeignete Standardalternative ist verfuegbar.",
            "begruendete_erfolgsaussicht": "Die Erfolgsaussicht ist anhand der Akte begruendet.",
        },
        "confirm": True,
    }


def test_health_endpoint_reports_ok(tmp_path):
    client = _make_client(tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["service"] == "verordnungsampel-web"


def test_api_check_returns_structured_result(tmp_path):
    client = _make_client(tmp_path)

    response = client.post(
        "/api/check",
        json={"icd": "I10", "atc": "C09AA02"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["result"]["icd"] == "I10"
    assert payload["result"]["atc"] == "C09AA02"
    assert payload["result"]["gesamt"] in {"gruen", "gelb", "rot"}
    assert isinstance(payload["result"]["treffer"], list)
    assert "disclaimer" in payload


def test_api_check_validates_required_fields(tmp_path):
    client = _make_client(tmp_path)

    response = client.post("/api/check", json={"icd": "", "atc": ""})

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["status"] == "error"
    assert "ICD" in payload["error"]


def test_api_justify_returns_structured_justification(tmp_path):
    client = _make_client(tmp_path)

    response = client.post(
        "/api/justify",
        json={
            "icd": "F41",
            "atc": "N05BA01",
            "alter": 72,
            "answers": _valid_justification_answers(),
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["result"]["icd"] == "F41"
    assert payload["justification"]["confirmed"] is True
    assert "diagnose" in payload["justification"]["answers"]


def test_api_justify_reports_validation_errors(tmp_path):
    client = _make_client(tmp_path)

    response = client.post(
        "/api/justify",
        json={
            "icd": "F41",
            "atc": "N05BA01",
            "alter": 72,
            "answers": {"diagnose": "zu kurz"},
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["status"] == "error"
    assert "errors" in payload
    assert any("confirm" in item for item in payload["errors"])


def test_api_workflow_returns_rendered_text(tmp_path):
    client = _make_client(tmp_path)

    response = client.post(
        "/api/workflow",
        json={
            "icd": "R52.1",
            "atc": "QV12",
            "context": {
                "kk": "Musterkasse",
                "praxis": "Musterpraxis",
                "arzt": "Dr. Muster",
                "patient": "P-4711",
            },
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["workflow"]["workflow_type"]
    assert "VORAB-KLAERUNGS-WORKFLOW" in payload["rendered_text"]
    assert payload["result"]["icd"] == "R52.1"


def test_html_form_renders_result(tmp_path):
    client = _make_client(tmp_path)

    response = client.post(
        "/",
        data={"icd": "F41", "atc": "N05BA01", "alter": "72"},
    )

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Prüfergebnis" in page
    assert "N05BA01" in page


def test_html_form_renders_justify_and_workflow_panels(tmp_path):
    client = _make_client(tmp_path)

    response = client.post(
        "/",
        data={"icd": "F41", "atc": "N05BA01", "alter": "72"},
    )

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Strukturierte Begründung" in page
    assert "Vorab-Workflow" in page
    assert 'name="web_action" value="justify"' in page
    assert 'name="web_action" value="workflow"' in page


def test_html_workflow_form_renders_generated_text(tmp_path):
    client = _make_client(tmp_path)

    response = client.post(
        "/",
        data={
            "web_action": "workflow",
            "icd": "R52.1",
            "atc": "QV12",
            "kk": "Musterkasse",
            "patient": "P-4711",
        },
    )

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Workflow-Typ:" in page
    assert "VORAB-KLAERUNGS-WORKFLOW" in page


def test_manifest_endpoint_returns_manifest_json(tmp_path):
    client = _make_client(tmp_path)

    response = client.get("/manifest.webmanifest")

    assert response.status_code == 200
    assert "application/manifest+json" in response.content_type


def test_manifest_has_pwa_required_fields(tmp_path):
    client = _make_client(tmp_path)

    response = client.get("/manifest.webmanifest")

    data = response.get_json(force=True)
    assert data["display"] == "standalone"
    assert "id" in data
    assert "scope" in data
    assert data["start_url"]


def test_sw_endpoint_returns_javascript(tmp_path):
    client = _make_client(tmp_path)

    response = client.get("/sw.js")

    assert response.status_code == 200
    assert "javascript" in response.content_type
    assert b"verordnungsampel-v2" in response.data


def test_offline_fallback_endpoint(tmp_path):
    client = _make_client(tmp_path)

    response = client.get("/offline.html")

    assert response.status_code == 200
    assert b"erreichbar" in response.data


def test_index_html_references_manifest_and_sw(tmp_path):
    client = _make_client(tmp_path)

    response = client.get("/")

    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "manifest.webmanifest" in page
    assert "sw.js" in page


def test_index_html_viewport_fit_cover(tmp_path):
    page = _make_client(tmp_path).get("/").get_data(as_text=True)
    assert "viewport-fit=cover" in page


def test_index_html_theme_color_meta(tmp_path):
    page = _make_client(tmp_path).get("/").get_data(as_text=True)
    assert 'name="theme-color"' in page
    assert "#355f3d" in page


def test_index_html_apple_status_bar_style_default(tmp_path):
    page = _make_client(tmp_path).get("/").get_data(as_text=True)
    assert "apple-mobile-web-app-status-bar-style" in page
    assert 'content="default"' in page


def test_index_html_apple_title(tmp_path):
    page = _make_client(tmp_path).get("/").get_data(as_text=True)
    assert "apple-mobile-web-app-title" in page
    assert "VA-Check" in page


def test_index_html_apple_touch_icon_href(tmp_path):
    page = _make_client(tmp_path).get("/").get_data(as_text=True)
    assert "apple-touch-icon" in page
    assert "/static/icons/apple-touch-icon-180.png" in page


def test_index_html_apple_touch_icon_sizes(tmp_path):
    page = _make_client(tmp_path).get("/").get_data(as_text=True)
    assert 'sizes="180x180"' in page


def test_manifest_display_standalone(tmp_path):
    data = _make_client(tmp_path).get("/manifest.webmanifest").get_data(as_text=True)
    assert '"standalone"' in data


def test_apple_touch_icon_endpoint_returns_200(tmp_path):
    response = _make_client(tmp_path).get("/static/icons/apple-touch-icon-180.png")
    assert response.status_code == 200


def test_index_html_safe_area_css(tmp_path):
    page = _make_client(tmp_path).get("/").get_data(as_text=True)
    assert "env(safe-area-inset-top" in page
    assert "env(safe-area-inset-bottom" in page


# --- Regressionstests Bugsweep 2026-06-20 ---

def test_manifest_non_maskable_icons_have_purpose_any(tmp_path):
    """Bug #1: Nicht-maskable Icons müssen purpose='any' haben (Browser-Installierbarkeit)."""
    data = _make_client(tmp_path).get("/manifest.webmanifest").get_json(force=True)
    non_maskable = [i for i in data["icons"] if i.get("purpose") != "maskable"]
    assert len(non_maskable) >= 2
    for icon in non_maskable:
        assert icon.get("purpose") == "any", f"Icon {icon['src']} fehlt purpose='any'"


def test_manifest_all_four_icons_present(tmp_path):
    """Bug #1: Alle 4 Icons (2× any, 2× maskable) müssen vorhanden sein."""
    data = _make_client(tmp_path).get("/manifest.webmanifest").get_json(force=True)
    assert len(data["icons"]) == 4
    purposes = {i.get("purpose") for i in data["icons"]}
    assert "any" in purposes
    assert "maskable" in purposes


def test_app_json_sort_keys_false(tmp_path):
    """Bug #2: app.json.sort_keys muss False sein (JSON_SORT_KEYS Config-Key in Flask 3.0 entfernt)."""
    from verordnungsampel.web.app import create_app
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})
    assert app.json.sort_keys is False
