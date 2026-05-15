from __future__ import annotations

from renew_curve.ui.theme import build_stylesheet


def default_personalization_settings() -> dict[str, str]:
    return {
        "theme": "light",
        "accent": "blue",
        "density": "comfortable",
        "default_snooze": "10m",
        "theme_style": "clean_mountain",
        "sticker_scope": "main_only",
        "functional_window_sticker_density": "low",
        "sticker_mode": "selected",
        "selected_sticker_id": "",
        "background_overlay": "60",
        "background_blur": "0",
        "background_darken": "20",
        "background_mode": "selected",
        "today_background_id": "",
        "next_background_id": "",
        "all_background_id": "",
    }


def stylesheet_for_personalization(settings: dict[str, str]) -> str:
    dark = settings.get("theme_style") == "dark_focus" or settings.get("theme") == "dark"
    compact = settings.get("density") == "compact"
    return build_stylesheet(
        accent=settings.get("accent", "blue"),
        dark=dark,
        compact=compact,
    )
