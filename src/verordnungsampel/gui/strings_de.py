"""GUI-Strings — i18n-Bridge.

Ursprünglich enthielt dieses Modul deutsche Konstanten direkt im Code.
Seit der i18n-Umstellung (data/translations/<lang>.json) wirkt es als
Backwards-Compatible Bridge: Attribut-Zugriffe wie ``S.APP_TITLE`` werden
über :func:`verordnungsampel.i18n.t` aufgelöst und folgen automatisch der
aktiven Sprache (siehe ``i18n.set_language``).

Der Modulname bleibt erhalten, damit bestehende Imports weiter funktionieren:

    >>> from verordnungsampel.gui import strings_de as S
    >>> S.APP_TITLE  # liefert deutsche oder englische Version je nach Sprache

Neuer Code sollte direkt ``verordnungsampel.i18n.t("KEY")`` benutzen.
"""

from __future__ import annotations

from verordnungsampel import i18n


# Statische Liste aller Keys, die diese Bridge nach außen exponiert.
# Wird beim ersten Zugriff verifiziert (i18n liefert ansonsten TranslationError).
_EXPORTED_KEYS: frozenset[str] = frozenset({
    "APP_TITLE", "APP_TAGLINE",
    "TRAY_TOOLTIP", "TRAY_TOOLTIP_STATUS", "TRAY_SHOW", "TRAY_HIDE", "TRAY_QUIT",
    "MENU_FILE", "MENU_QUIT", "MENU_VIEW", "MENU_ALWAYS_ON_TOP",
    "MENU_MINIMAL_MODE", "MENU_TRANSPARENCY", "MENU_HELP", "MENU_ABOUT",
    "TAB_CHECK", "TAB_JUSTIFY", "TAB_WORKFLOW", "TAB_LOG",
    "TAB_REMINDER", "TAB_SOURCES",
    "CHECK_ICD_LABEL", "CHECK_ATC_LABEL", "CHECK_AGE_LABEL",
    "CHECK_BUTTON", "CHECK_NO_LOG", "CHECK_RESULT_LABEL",
    "CHECK_SOURCES_LABEL", "CHECK_PB_LABEL",
    "CHECK_HINT_EMPTY", "CHECK_HINT_UNKNOWN",
    "CHECK_ERROR_MISSING", "CHECK_ERROR_GENERIC",
    "AMPEL_GRUEN", "AMPEL_GELB", "AMPEL_ROT", "AMPEL_NONE",
    "JUSTIFY_NO_DATA", "JUSTIFY_GRUEN_HINT", "JUSTIFY_INTRO",
    "JUSTIFY_CONFIRM", "JUSTIFY_SUBMIT", "JUSTIFY_SUCCESS",
    "JUSTIFY_ERROR_HEAD",
    "WORKFLOW_INTRO", "WORKFLOW_PRAXIS", "WORKFLOW_PRAXIS_ADRESSE",
    "WORKFLOW_ARZT", "WORKFLOW_BSNR", "WORKFLOW_LANR", "WORKFLOW_KK",
    "WORKFLOW_PATIENT", "WORKFLOW_GENERATE", "WORKFLOW_COPY",
    "WORKFLOW_SAVE", "WORKFLOW_NO_DATA", "WORKFLOW_KEINE_AKTION",
    "WORKFLOW_COPIED", "WORKFLOW_SAVED",
    "LOG_REFRESH", "LOG_VERIFY", "LOG_EMPTY",
    "LOG_VERIFY_OK", "LOG_VERIFY_FAIL",
    "REMINDER_QUARTAL", "REMINDER_GENERATE",
    "REMINDER_ERROR", "REMINDER_EMPTY",
    "BTN_OK", "BTN_CANCEL", "BTN_CLOSE",
    "STATUS_READY", "ABOUT_TEXT",
    "HINT_NOT_MEDICAL_DEVICE", "STATUS_PERMANENT_DISCLAIMER",
    "DISCLAIMER_DIALOG_TITLE", "DISCLAIMER_DIALOG_HEADLINE",
    "DISCLAIMER_CHECK_NOT_VALIDATED", "DISCLAIMER_CHECK_NOT_CERTIFIED",
    "DISCLAIMER_CHECK_DOCTOR_RESPONSIBILITY", "DISCLAIMER_CHECK_OWN_RISK",
    "DISCLAIMER_BTN_ACCEPT", "DISCLAIMER_BTN_REJECT",
    "DISCLAIMER_INFO_BUTTONS",
})


def __getattr__(name: str) -> str:
    """PEP 562 — dynamischer Modul-Attribut-Zugriff über i18n."""
    if name.startswith("_") or name not in _EXPORTED_KEYS:
        raise AttributeError(
            f"module 'verordnungsampel.gui.strings_de' has no attribute '{name}'"
        )
    return i18n.t(name)


def __dir__() -> list[str]:
    """Sichtbare Attribute für ``dir(strings_de)``."""
    return sorted(_EXPORTED_KEYS)


__all__ = sorted(_EXPORTED_KEYS)
