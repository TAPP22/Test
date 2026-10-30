"""Persistent user settings for pyRender."""

import json
from pathlib import Path

SETTINGS_PATH = Path(__file__).resolve().parent / "settings.json"
DEFAULTS = {
	"mouse_sensitivity": 0.0025,
	"mouse_look": True,
	"invert_mouse_y": False,
	"fov": 66,
	"quality": "balanced",
	"fullscreen": False,
	"soft_shadows": True,
	"game_mode": "explore",
}
QUALITY_RAYS = {"performance": 240, "balanced": 360, "high": 480}
GAME_MODES = ("explore", "sprint", "no_jump")


def load_settings():
	try:
		stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
		if not isinstance(stored, dict):
			stored = {}
	except (OSError, ValueError, TypeError):
		stored = {}
	settings = {**DEFAULTS, **stored}
	settings["mouse_sensitivity"] = max(0.0005, min(0.01, float(settings["mouse_sensitivity"])))
	settings["fov"] = max(50, min(100, int(settings["fov"])))
	if settings["quality"] not in QUALITY_RAYS:
		settings["quality"] = DEFAULTS["quality"]
	if settings["game_mode"] not in GAME_MODES:
		settings["game_mode"] = DEFAULTS["game_mode"]
	for key in ("mouse_look", "invert_mouse_y", "fullscreen", "soft_shadows"):
		settings[key] = bool(settings[key])
	return settings


def save_settings(settings):
	SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")