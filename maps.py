"""Map loading and saving for pyRender."""

import json
import re
from pathlib import Path

MAPS_DIR = Path(__file__).resolve().parent / "maps"
VALID_TILES = frozenset("01DTABCPQLUVJY")


def load_maps():
	maps = {}
	MAPS_DIR.mkdir(exist_ok=True)
	for path in sorted(MAPS_DIR.glob("*.json")):
		try:
			data = json.loads(path.read_text(encoding="utf-8"))
			grid = data["grid"]
			if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
				continue
			if any(tile not in VALID_TILES for row in grid for tile in row):
				continue
			data["id"] = path.stem
			data.setdefault("name", path.stem.replace("_", " ").title())
			data.setdefault("level", 1)
			data.setdefault("texture_style", "brick")
			data.setdefault("colors", {"sky": [95, 155, 205], "floor": [58, 55, 52], "wall": [220, 175, 125]})
			data.setdefault("spawn", [2.5, 1.5, 0.0])
			data.setdefault("portal", {"map": "", "spawn": [2.5, 1.5, 0.0]})
			data.setdefault("objects", [])
			data.setdefault("cutscenes", [])
			data.setdefault("portals", [])
			custom_texture = data.get("custom_texture", [])
			if (not isinstance(custom_texture, list) or not custom_texture or len(custom_texture) > 64
					or not isinstance(custom_texture[0], list) or not 1 <= len(custom_texture[0]) <= 64
					or any(not isinstance(row, list) or len(row) != len(custom_texture[0]) for row in custom_texture)
					or any(not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color) for row in custom_texture for color in row)):
				custom_texture = []
			data["custom_texture"] = custom_texture
			layers = data.get("layers") or [{"name": "Piano 1", "grid": grid, "objects": data["objects"], "enemies": []}]
			valid_layers = []
			for layer in layers:
				layer_grid = layer.get("grid", [])
				if not layer_grid or not layer_grid[0] or any(len(row) != len(layer_grid[0]) for row in layer_grid):
					continue
				if any(tile not in VALID_TILES for row in layer_grid for tile in row):
					continue
				valid_layers.append({"name": layer.get("name", f"Piano {len(valid_layers) + 1}"),
									 "grid": layer_grid, "objects": layer.get("objects", []),
									 "enemies": layer.get("enemies", [])})
			if not valid_layers:
				continue
			data["layers"] = valid_layers
			maps[path.stem] = data
		except (OSError, ValueError, KeyError, TypeError):
			continue
	return maps


def save_map(map_id, data):
	MAPS_DIR.mkdir(exist_ok=True)
	path = MAPS_DIR / f"{map_id}.json"
	path.write_text(json.dumps(data, indent=2), encoding="utf-8")
	return path