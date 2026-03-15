"""
Kindred v2.4.0 - Internationalization (i18n) Framework
Simple JSON-based translation system.
"""

import contextvars
import json
from pathlib import Path

from app.config import DEFAULT_LOCALE

_LOCALE_DIR = Path(__file__).parent.parent / "locales"
_translations: dict[str, dict] = {}
_current_locale_var = contextvars.ContextVar('locale', default=DEFAULT_LOCALE)


def _load_locale(locale: str) -> dict:
    """Load translation file for a locale."""
    path = _LOCALE_DIR / f"{locale}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def init_i18n():
    """Initialize i18n system and load default locale."""
    _LOCALE_DIR.mkdir(parents=True, exist_ok=True)
    # Create default English locale if it doesn't exist
    en_path = _LOCALE_DIR / "en.json"
    if not en_path.exists():
        en_strings = {
            "app_name": "Kindred",
            "tagline": "Compatibility-first dating + social platform",
            "login": "Log In",
            "signup": "Sign Up",
            "email": "Email",
            "password": "Password",
            "display_name": "Display Name",
            "matches": "Matches",
            "messages": "Messages",
            "discover": "Discover",
            "profile": "Profile",
            "settings": "Settings",
            "groups": "Groups",
            "events": "Events",
            "stories": "Stories",
            "compatibility": "Compatibility",
            "send_message": "Send Message",
            "like": "Like",
            "super_like": "Super Like",
            "block": "Block",
            "report": "Report",
            "search": "Search",
            "no_results": "No results found",
            "loading": "Loading...",
            "save": "Save",
            "cancel": "Cancel",
            "delete": "Delete",
            "confirm": "Confirm",
            "logout": "Log Out",
            "notifications": "Notifications",
            "online": "Online",
            "offline": "Offline",
            "typing": "typing...",
            "new_match": "New Match!",
            "compatibility_score": "Compatibility Score",
            "view_profile": "View Profile",
            "edit_profile": "Edit Profile",
            "change_password": "Change Password",
            "account_settings": "Account Settings",
            "privacy_settings": "Privacy Settings",
            "notification_settings": "Notification Settings",
            "two_factor_auth": "Two-Factor Authentication",
            "data_export": "Export My Data",
            "delete_account": "Delete Account",
            "incognito_mode": "Incognito Mode",
            "active_sessions": "Active Sessions",
        }
        with open(en_path, "w", encoding="utf-8") as f:
            json.dump(en_strings, f, indent=2, ensure_ascii=False)
    _translations["en"] = _load_locale("en")
    if DEFAULT_LOCALE != "en":
        _translations[DEFAULT_LOCALE] = _load_locale(DEFAULT_LOCALE)


def t(key: str, locale: str = None, **kwargs) -> str:
    """Translate a key. Falls back to English, then the raw key."""
    loc = locale or _current_locale_var.get()
    if loc not in _translations:
        _translations[loc] = _load_locale(loc)
    text = _translations.get(loc, {}).get(key)
    if text is None:
        text = _translations.get("en", {}).get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def get_available_locales() -> list[str]:
    """List available locale codes."""
    _LOCALE_DIR.mkdir(parents=True, exist_ok=True)
    return [p.stem for p in _LOCALE_DIR.glob("*.json")]


def get_translations(locale: str) -> dict:
    """Get all translations for a locale."""
    if locale not in _translations:
        _translations[locale] = _load_locale(locale)
    return _translations.get(locale, {})


def set_locale(locale: str):
    _current_locale_var.set(locale)
    if locale not in _translations:
        _translations[locale] = _load_locale(locale)
