"""Compact map editor with a live first-person 3D preview."""

import math
import re
import sys
import subprocess
from pathlib import Path

import pygame

from game import render_world
from maps import load_maps, save_map

WIDTH, HEIGHT = 1024, 680
GRID_ORIGIN = (20, 112)
PREVIEW_RECT = pygame.Rect(520, 104, 484, 270)
PALETTES = {
	"sky": [(95, 155, 205), (118, 166, 178), (88, 104, 151), (119, 174, 151)],
	"floor": [(58, 55, 52), (48, 62, 62), (68, 61, 83), (48, 73, 58)],
	"wall": [(220, 175, 125), (125, 195, 175), (210, 115, 92), (177, 190, 133)],
}
BRUSHES = {pygame.K_1: "1", pygame.K_2: "0", pygame.K_3: "D", pygame.K_4: "S", pygame.K_5: "T"}
PUZZLE_BRUSHES = {pygame.K_c: "C", pygame.K_p: "P", pygame.K_q: "Q", pygame.K_l: "L"}
ROUTE_BRUSHES = {pygame.K_u: "U", pygame.K_v: "V", pygame.K_j: "J", pygame.K_y: "Y"}
PUZZLE_TILES = ("C", "P", "Q", "L", "U", "V", "J", "Y", "B")
TILE_LABELS = {"C": "Cassa", "P": "Runa P", "Q": "Runa Q", "L": "Blocco L",
			   "U": "Scala su", "V": "Scala giu", "J": "Salto", "Y": "Boost", "B": "Blocco 3D"}
MODEL_TOOLS = {pygame.K_6: "crystal", pygame.K_7: "chest", pygame.K_8: "statue"}
ENEMY_TOOLS = {pygame.K_f: "sentinel"}
TILE_COLORS = {"1": (92, 111, 101), "0": (36, 45, 43), "D": (199, 157, 83), "T": (72, 143, 151),
			   "C": (156, 100, 58), "P": (193, 145, 66), "Q": (72, 158, 187), "L": (102, 128, 153),
			   "U": (117, 160, 115), "V": (117, 160, 115), "J": (221, 130, 54), "Y": (58, 158, 196)}
TEXTURE_STYLES = ("brick", "stone", "panel")


def fresh_grid(width=16, height=9):
	return ["1" * width] + ["1" + "0" * (width - 2) + "1" for _ in range(height - 2)] + ["1" * width]


class CompactEditor:
	def __init__(self):
		pygame.init()
		self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
		self.fullscreen = False
		pygame.display.set_caption("pyRender | Editor compatto e preview 3D")
		self.clock = pygame.time.Clock()
		self.title_font = pygame.font.Font(None, 34)
		self.font = pygame.font.Font(None, 24)
		self.small = pygame.font.Font(None, 19)
		self.maps = load_maps()
		self.map_ids = list(self.maps)
		self.map_index = 0
		self.grid = fresh_grid()
		self.colors = {key: values[0] for key, values in PALETTES.items()}
		self.name = "nuova_mappa"
		self.portal_target = self.map_ids[0] if self.map_ids else ""
		self.level = 1
		self.texture_style = "brick"
		self.spawn = [2.5, 1.5, 0.0]
		self.objects = []
		self.enemies = []
		self.block_size = [0.8, 0.8, 0.4]
		self.layers = [{"name": "Piano 1", "grid": self.grid, "objects": self.objects, "enemies": self.enemies}]
		self.layer_index = 0
		self.preview_mode = "game"
		self.cutscenes = []
		self.custom_texture = []
		self.portals = []
		self.portal_tool = False
		self.portal_next = "A"
		self.enemy_tool = None
		self.external_tools = []
		self.brush = "1"
		self.object_tool = None
		self.active_field = "name"
		self.preview_direction = 0.0
		self.dragging_preview = False
		self.message = "Cassa C | Rune P/Q | Scale U/V | Trigger J/Y | B crea blocco 3D"
		self.running = True
		if "atrium" in self.map_ids:
			self.map_index = self.map_ids.index("atrium")
			self.load_map()

	@property
	def cell_size(self):
		return min(28, 476 // len(self.grid[0]), 278 // len(self.grid))

	def grid_rect(self, column, row):
		cell = self.cell_size
		return pygame.Rect(GRID_ORIGIN[0] + column * cell, GRID_ORIGIN[1] + row * cell, cell - 1, cell - 1)

	def load_map(self):
		if not self.map_ids:
			self.message = "Nessuna mappa salvata da caricare"
			return
		data = self.maps[self.map_ids[self.map_index]]
		self.grid = list(data["grid"])
		self.colors = {key: tuple(value) for key, value in data["colors"].items()}
		self.name = self.map_ids[self.map_index]
		self.portal_target = data.get("portal", {}).get("map", "")
		self.level = data.get("level", 1)
		self.texture_style = data.get("texture_style", "brick")
		self.spawn = list(data.get("spawn", [2.5, 1.5, 0.0]))
		self.objects = [dict(item) for item in data.get("objects", [])]
		self.enemies = [dict(item) for item in data.get("enemies", [])]
		self.cutscenes = [dict(item) for item in data.get("cutscenes", [])]
		self.custom_texture = [list(row) for row in data.get("custom_texture", [])]
		self.portals = [dict(item) for item in data.get("portals", [])]
		self.layers = [{"name": layer["name"], "grid": list(layer["grid"]),
						"objects": [dict(item) for item in layer.get("objects", [])],
						"enemies": [dict(item) for item in layer.get("enemies", [])]} for layer in data["layers"]]
		self.layer_index = min(self.layer_index, len(self.layers) - 1)
		self.activate_layer(self.layer_index)
		self.preview_direction = self.spawn[2]
		self.message = f"Caricata: {data['name']}"

	def activate_layer(self, index):
		self.layer_index = max(0, min(index, len(self.layers) - 1))
		layer = self.layers[self.layer_index]
		self.grid = layer["grid"]
		self.objects = layer["objects"]
		self.enemies = layer["enemies"]
		self.message = f"Piano selezionato: {layer['name']}"

	def add_layer(self):
		self.layers.append({"name": f"Piano {len(self.layers) + 1}",
							"grid": fresh_grid(len(self.grid[0]), len(self.grid)), "objects": [], "enemies": []})
		self.activate_layer(len(self.layers) - 1)

	def remove_layer(self):
		if len(self.layers) <= 1:
			self.message = "La mappa deve avere almeno un piano"
			return
		self.layers.pop(self.layer_index)
		self.activate_layer(max(0, self.layer_index - 1))

	def duplicate_last_object(self):
		if not self.objects:
			self.message = "Nessun modello da duplicare"
			return
		clone = dict(self.objects[-1])
		clone["x"] = min(len(self.grid[0]) - 1.5, clone["x"] + 1)
		clone["y"] = min(len(self.grid) - 1.5, clone["y"] + 1)
		self.objects.append(clone)
		self.message = "Modello duplicato"

	def save(self):
		map_id = re.sub(r"[^a-zA-Z0-9_-]", "_", self.name.strip()).strip("_").lower()
		if not map_id:
			self.message = "Inserisci un nome valido"
			return
		spawn_x, spawn_y = int(self.spawn[0]), int(self.spawn[1])
		self.grid[spawn_y] = self.grid[spawn_y][:spawn_x] + "0" + self.grid[spawn_y][spawn_x + 1:]
		self.layers[self.layer_index]["grid"] = self.grid
		self.layers[self.layer_index]["objects"] = self.objects
		self.layers[self.layer_index]["enemies"] = self.enemies
		data = {"name": self.name.replace("_", " ").title(), "level": self.level,
				"texture_style": self.texture_style, "grid": self.grid,
				"colors": self.colors, "spawn": self.spawn,
				"portal": {"map": self.portal_target.strip().lower(), "spawn": [2.5, 1.5, 0.0]},
				"objects": self.objects, "enemies": self.enemies, "layers": self.layers,
				"cutscenes": self.cutscenes, "custom_texture": self.custom_texture,
				"portals": self.portals}
		save_map(map_id, data)
		self.maps = load_maps()
		self.map_ids = list(self.maps)
		self.map_index = self.map_ids.index(map_id)
		self.message = f"Salvata: maps/{map_id}.json"

	def resize(self, width_delta=0, height_delta=0):
		old = self.grid
		width = max(8, min(48, len(old[0]) + width_delta))
		height = max(7, min(32, len(old) + height_delta))
		new_grid = []
		for row in range(height):
			if row in (0, height - 1):
				new_grid.append("1" * width)
			elif row < len(old) - 1:
				interior = old[row][1:min(width - 1, len(old[row]) - 1)]
				new_grid.append("1" + interior + "0" * (width - 2 - len(interior)) + "1")
			else:
				new_grid.append("1" + "0" * (width - 2) + "1")
		self.grid = new_grid
		self.layers[self.layer_index]["grid"] = self.grid
		if int(self.spawn[0]) >= width - 1 or int(self.spawn[1]) >= height - 1:
			self.spawn = [1.5, 1.5, 0.0]

	def paint(self, column, row):
		if not 0 <= row < len(self.grid) or not 0 <= column < len(self.grid[0]):
			return
		if self.object_tool:
			if self.grid[row][column] != "0":
				self.message = "Posiziona i modelli su una cella vuota"
				return
			if self.object_tool == "block":
				self.objects.append({"x": column + 0.5, "y": row + 0.5, "type": "block",
								 "width": self.block_size[0], "depth": self.block_size[1],
								 "height": self.block_size[2], "climbable": True,
								 "color": [166, 116, 76], "name": "Blocco personalizzato"})
				self.message = f"Blocco {self.block_size[0]:.1f} x {self.block_size[1]:.1f} x {self.block_size[2]:.1f} posizionato"
			else:
				self.objects.append({"x": column + 0.5, "y": row + 0.5, "type": self.object_tool,
								 "name": self.object_tool.title(), "message": f"Hai esaminato: {self.object_tool}.", "action": "inspect"})
			self.object_tool = None
		elif self.enemy_tool:
			if self.grid[row][column] != "0":
				self.message = "Piazza il nemico su una cella libera"
				return
			self.enemies.append({"x": column + 0.5, "y": row + 0.5, "type": self.enemy_tool, "name": "Guardiano"})
			self.enemy_tool = None
			self.message = "Guardiano aggiunto al piano"
		elif self.portal_tool:
			if self.portal_next == "A" and any(tile in "AB" for line in self.grid for tile in line):
				self.message = "Rimuovi la coppia A/B esistente prima di crearne un'altra"
				self.portal_tool = False
				return
			if self.grid[row][column] != "1":
				self.message = "I varchi si piazzano sulle celle muro"
				return
			self.grid[row] = self.grid[row][:column] + self.portal_next + self.grid[row][column + 1:]
			self.message = f"Lato {self.portal_next} piazzato; scegli l'altra parete"
			if self.portal_next == "A":
				self.portal_next = "B"
			else:
				self.portal_next = "A"
				self.portal_tool = False
		elif self.brush == "S":
			self.spawn = [column + 0.5, row + 0.5, self.spawn[2]]
			self.grid[row] = self.grid[row][:column] + "0" + self.grid[row][column + 1:]
		else:
			self.grid[row] = self.grid[row][:column] + self.brush + self.grid[row][column + 1:]

	def handle_event(self, event):
		if event.type == pygame.QUIT:
			self.running = False
		elif event.type == pygame.TEXTINPUT:
			if self.active_field == "name":
				self.name = (self.name + re.sub(r"[^a-zA-Z0-9_-]", "", event.text))[:24]
			else:
				self.portal_target = (self.portal_target + re.sub(r"[^a-zA-Z0-9_-]", "", event.text))[:24]
		elif event.type == pygame.KEYDOWN:
			if event.key == pygame.K_ESCAPE:
				self.running = False
			elif event.key == pygame.K_F11:
				self.fullscreen = not self.fullscreen
				self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN if self.fullscreen else 0)
			elif event.key == pygame.K_n and event.mod & pygame.KMOD_CTRL:
				self.grid = fresh_grid()
				self.colors = {key: values[0] for key, values in PALETTES.items()}
				self.name = "nuova_mappa"
				self.portal_target = ""
				self.level = 1
				self.texture_style = "brick"
				self.spawn = [2.5, 1.5, 0.0]
				self.objects = []
				self.enemies = []
				self.layers = [{"name": "Piano 1", "grid": self.grid, "objects": self.objects, "enemies": self.enemies}]
				self.cutscenes, self.custom_texture, self.portals = [], [], []
				self.layer_index = 0
				self.active_field = "name"
				self.message = "Nuova mappa: scrivi il nome e disegna il livello"
			elif event.key == pygame.K_BACKSPACE:
				if self.active_field == "name":
					self.name = self.name[:-1]
				else:
					self.portal_target = self.portal_target[:-1]
			elif event.key == pygame.K_TAB:
				self.active_field = "portal" if self.active_field == "name" else "name"
			elif event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
				self.save()
			elif event.key in BRUSHES:
				self.brush, self.object_tool = BRUSHES[event.key], None
				self.enemy_tool = None
				self.portal_tool = False
			elif event.key in PUZZLE_BRUSHES:
				self.brush, self.object_tool = PUZZLE_BRUSHES[event.key], None
				self.enemy_tool = None
				self.portal_tool = False
			elif event.key in ROUTE_BRUSHES:
				self.brush, self.object_tool = ROUTE_BRUSHES[event.key], None
				self.enemy_tool = None
				self.portal_tool = False
			elif event.key == pygame.K_b:
				self.object_tool = "block"
				self.enemy_tool = None
				self.portal_tool = False
				self.message = "Blocco 3D: ,/. larghezza | M/N profondita | [/] altezza"
			elif event.key in (pygame.K_COMMA, pygame.K_PERIOD):
				self.block_size[0] = max(0.2, min(2.5, self.block_size[0] + (0.1 if event.key == pygame.K_PERIOD else -0.1)))
				self.message = f"Larghezza blocco: {self.block_size[0]:.1f}"
			elif event.key in (pygame.K_m, pygame.K_n):
				self.block_size[1] = max(0.2, min(2.5, self.block_size[1] + (0.1 if event.key == pygame.K_n else -0.1)))
				self.message = f"Profondita blocco: {self.block_size[1]:.1f}"
			elif event.key in MODEL_TOOLS:
				self.object_tool = MODEL_TOOLS[event.key]
			elif event.key == pygame.K_9:
				self.object_tool = None
				self.message = f"Modelli piazzati: {len(self.objects)}"
			elif event.key == pygame.K_0:
				self.duplicate_last_object()
			elif event.key in ENEMY_TOOLS:
				self.enemy_tool = ENEMY_TOOLS[event.key]
				self.object_tool = None
				self.portal_tool = False
			elif event.key == pygame.K_g:
				self.portal_tool = True
				self.portal_next = "A"
				self.object_tool = None
				self.message = "Clicca due pareti: arancio A, ciano B"
			elif event.key == pygame.K_EQUALS:
				self.resize(width_delta=1)
			elif event.key == pygame.K_MINUS:
				self.resize(width_delta=-1)
			elif event.key == pygame.K_RIGHTBRACKET:
				if self.object_tool == "block":
					self.block_size[2] = min(2.5, self.block_size[2] + 0.1)
					self.message = f"Altezza blocco: {self.block_size[2]:.1f}"
				else:
					self.resize(height_delta=1)
			elif event.key == pygame.K_LEFTBRACKET:
				if self.object_tool == "block":
					self.block_size[2] = max(0.1, self.block_size[2] - 0.1)
					self.message = f"Altezza blocco: {self.block_size[2]:.1f}"
				else:
					self.resize(height_delta=-1)
			elif event.key == pygame.K_PAGEUP:
				self.activate_layer(self.layer_index + 1)
			elif event.key == pygame.K_PAGEDOWN:
				self.activate_layer(self.layer_index - 1)
			elif event.key == pygame.K_INSERT:
				self.add_layer()
			elif event.key == pygame.K_DELETE:
				self.remove_layer()
			elif event.key == pygame.K_LEFT:
				self.preview_direction -= 0.12
			elif event.key == pygame.K_RIGHT:
				self.preview_direction += 0.12
		elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
			if pygame.Rect(790, 26, 100, 34).collidepoint(event.pos):
				self.open_tool("TextureEditor.py")
			elif pygame.Rect(896, 26, 108, 34).collidepoint(event.pos):
				self.open_tool("CutsceneEditor.py")
			elif pygame.Rect(20, 70, 142, 26).collidepoint(event.pos):
				if any(tile in "AB" for line in self.grid for tile in line):
					self.message = "Rimuovi la coppia A/B esistente prima di crearne un'altra"
				else:
					self.portal_tool = True
					self.portal_next = "A"
					self.object_tool = None
					self.message = "Clicca due pareti: arancio A, ciano B"
			elif PREVIEW_RECT.collidepoint(event.pos):
				self.dragging_preview = True
			elif GRID_ORIGIN[0] <= event.pos[0] < GRID_ORIGIN[0] + len(self.grid[0]) * self.cell_size and GRID_ORIGIN[1] <= event.pos[1] < GRID_ORIGIN[1] + len(self.grid) * self.cell_size:
				column = (event.pos[0] - GRID_ORIGIN[0]) // self.cell_size
				row = (event.pos[1] - GRID_ORIGIN[1]) // self.cell_size
				self.paint(column, row)
			elif 378 <= event.pos[1] < 410 and 20 <= event.pos[0] < 500:
				tile_index = (event.pos[0] - 20) // 52
				if tile_index < len(PUZZLE_TILES):
					tile = PUZZLE_TILES[tile_index]
					if tile == "B":
						self.object_tool = "block"
						self.enemy_tool = None
						self.message = "Blocco 3D: ,/. larghezza | M/N profondita | [/] altezza"
					else:
						self.brush = tile
						self.object_tool = self.enemy_tool = None
					self.portal_tool = False
			elif 414 <= event.pos[1] < 446 and 20 <= event.pos[0] < 500:
				tool_index = (event.pos[0] - 20) // 94
				if tool_index < len(BRUSHES):
					self.brush = list(BRUSHES.values())[tool_index]
					self.object_tool = None
					self.portal_tool = False
					self.enemy_tool = None
			elif 450 <= event.pos[1] < 482 and 20 <= event.pos[0] < 500:
				tool_index = (event.pos[0] - 20) // 118
				if tool_index < len(MODEL_TOOLS):
					self.object_tool = list(MODEL_TOOLS.values())[tool_index]
				elif tool_index == 3:
					self.object_tool = "block"
					self.enemy_tool = None
					self.portal_tool = False
			elif pygame.Rect(520, 398, 220, 32).collidepoint(event.pos):
				self.active_field = "name"
			elif pygame.Rect(750, 398, 254, 32).collidepoint(event.pos):
				self.active_field = "portal"
			elif pygame.Rect(520, 440, 145, 34).collidepoint(event.pos):
				self.cycle_color("sky")
			elif pygame.Rect(674, 440, 145, 34).collidepoint(event.pos):
				self.cycle_color("floor")
			elif pygame.Rect(829, 440, 175, 34).collidepoint(event.pos):
				self.cycle_color("wall")
			elif pygame.Rect(520, 486, 44, 32).collidepoint(event.pos):
				self.level = max(1, self.level - 1)
			elif pygame.Rect(568, 486, 44, 32).collidepoint(event.pos):
				self.level += 1
			elif pygame.Rect(620, 486, 60, 32).collidepoint(event.pos):
				self.resize(width_delta=-1)
			elif pygame.Rect(684, 486, 60, 32).collidepoint(event.pos):
				self.resize(width_delta=1)
			elif pygame.Rect(748, 486, 60, 32).collidepoint(event.pos):
				self.resize(height_delta=-1)
			elif pygame.Rect(812, 486, 60, 32).collidepoint(event.pos):
				self.resize(height_delta=1)
			elif pygame.Rect(876, 486, 128, 32).collidepoint(event.pos):
				self.save()
			elif pygame.Rect(520, 532, 54, 32).collidepoint(event.pos):
				self.map_index = (self.map_index - 1) % max(1, len(self.map_ids))
			elif pygame.Rect(580, 532, 54, 32).collidepoint(event.pos):
				self.map_index = (self.map_index + 1) % max(1, len(self.map_ids))
			elif pygame.Rect(642, 532, 126, 32).collidepoint(event.pos):
				self.load_map()
			elif pygame.Rect(780, 532, 108, 32).collidepoint(event.pos):
				if self.objects:
					self.objects.pop()
					self.message = "Ultimo modello rimosso"
			elif pygame.Rect(896, 532, 108, 32).collidepoint(event.pos):
				self.texture_style = TEXTURE_STYLES[(TEXTURE_STYLES.index(self.texture_style) + 1) % len(TEXTURE_STYLES)]
			elif pygame.Rect(520, 574, 68, 32).collidepoint(event.pos):
				self.activate_layer(self.layer_index - 1)
			elif pygame.Rect(594, 574, 68, 32).collidepoint(event.pos):
				self.activate_layer(self.layer_index + 1)
			elif pygame.Rect(668, 574, 90, 32).collidepoint(event.pos):
				self.add_layer()
			elif pygame.Rect(764, 574, 90, 32).collidepoint(event.pos):
				self.remove_layer()
			elif pygame.Rect(860, 574, 144, 32).collidepoint(event.pos):
				self.preview_mode = "below" if self.preview_mode == "game" else "game"
		elif event.type == pygame.MOUSEMOTION:
			if self.dragging_preview and event.buttons[0]:
				self.preview_direction += event.rel[0] * 0.012
			elif event.buttons[0] and GRID_ORIGIN[0] <= event.pos[0] < GRID_ORIGIN[0] + len(self.grid[0]) * self.cell_size and GRID_ORIGIN[1] <= event.pos[1] < GRID_ORIGIN[1] + len(self.grid) * self.cell_size:
				self.paint((event.pos[0] - GRID_ORIGIN[0]) // self.cell_size, (event.pos[1] - GRID_ORIGIN[1]) // self.cell_size)
		elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
			self.dragging_preview = False
		elif event.type == pygame.MOUSEWHEEL:
			mouse_x, mouse_y = pygame.mouse.get_pos()
			if GRID_ORIGIN[0] <= mouse_x <= GRID_ORIGIN[0] + len(self.grid[0]) * self.cell_size and GRID_ORIGIN[1] <= mouse_y <= GRID_ORIGIN[1] + len(self.grid) * self.cell_size:
				self.activate_layer(self.layer_index + event.y)

	def cycle_color(self, key):
		palette = PALETTES[key]
		try:
			index = palette.index(self.colors[key])
		except ValueError:
			index = -1
		self.colors[key] = palette[(index + 1) % len(palette)]

	def draw(self):
		screen = self.screen
		screen.fill((24, 31, 30))
		screen.blit(self.title_font.render("EDITOR MAPPE", True, (233, 236, 220)), (20, 24))
		self.label("U/V scale | J/Y trigger | B blocco", (520, 34), self.small, (157, 174, 161))
		self.button((790, 26, 100, 34), "TEXTURE")
		self.button((896, 26, 108, 34), "CUTSCENE")
		self.draw_grid()
		self.draw_preview()
		self.draw_controls()
		pygame.display.flip()

	def draw_grid(self):
		for row, line in enumerate(self.grid):
			for column, tile in enumerate(line):
				rect = self.grid_rect(column, row)
				fallback = (237, 139, 73) if tile == "A" else (74, 190, 211) if tile == "B" else (36, 45, 43)
				pygame.draw.rect(self.screen, TILE_COLORS.get(tile, fallback), rect)
				if tile in "PQ":
					pygame.draw.circle(self.screen, (237, 239, 211), rect.center, max(2, self.cell_size // 7), 2)
				elif tile in "UV":
					for step in range(3):
						y = rect.bottom - 3 - step * max(2, self.cell_size // 5)
						pygame.draw.line(self.screen, (222, 237, 207), (rect.left + 3, y), (rect.right - 3, y), 2)
				elif tile in "JY":
					glyph = "^" if tile == "J" else ">"
					text = self.small.render(glyph, True, (245, 245, 225))
					self.screen.blit(text, text.get_rect(center=rect.center))
				if abs(self.spawn[0] - column - 0.5) < 0.01 and abs(self.spawn[1] - row - 0.5) < 0.01:
					pygame.draw.circle(self.screen, (245, 242, 220), rect.center, max(3, self.cell_size // 5))
		for model in self.objects:
			if model.get("type") == "block":
				continue
			point = (int(GRID_ORIGIN[0] + model["x"] * self.cell_size), int(GRID_ORIGIN[1] + model["y"] * self.cell_size))
			pygame.draw.circle(self.screen, (105, 220, 204), point, max(4, self.cell_size // 5), 2)
		for enemy in self.enemies:
			point = (int(GRID_ORIGIN[0] + enemy["x"] * self.cell_size), int(GRID_ORIGIN[1] + enemy["y"] * self.cell_size))
			pygame.draw.circle(self.screen, (211, 76, 67), point, max(5, self.cell_size // 3))
			pygame.draw.circle(self.screen, (255, 220, 184), point, max(2, self.cell_size // 8), 1)
		for block in self.objects:
			if block.get("type") != "block":
				continue
			bounds = pygame.Rect(0, 0, max(3, int(block.get("width", 0.8) * self.cell_size)),
							 max(3, int(block.get("depth", 0.8) * self.cell_size)))
			bounds.center = (int(GRID_ORIGIN[0] + block["x"] * self.cell_size), int(GRID_ORIGIN[1] + block["y"] * self.cell_size))
			pygame.draw.rect(self.screen, block.get("color", (166, 116, 76)), bounds)
			pygame.draw.rect(self.screen, (236, 208, 153), bounds, 1)
		pygame.draw.rect(self.screen, (67, 83, 75), (16, 104, self.cell_size * len(self.grid[0]) + 8, self.cell_size * len(self.grid) + 8), 1)
		self.label(f"{len(self.grid[0])} x {len(self.grid)}  |  {self.layers[self.layer_index]['name']}", (20, 100), self.small, (160, 183, 166))
		self.button((20, 70, 142, 26), "VARCO A/B")
		for index, tile in enumerate(PUZZLE_TILES):
			selected = self.object_tool == "block" if tile == "B" else self.brush == tile and not self.object_tool
			self.tool_button((20 + index * 52, 378, 48, 28), tile, selected)
		for index, (key, tile) in enumerate(BRUSHES.items()):
			label = {"1": "Muro", "0": "Gomma", "D": "Porta", "S": "Spawn", "T": "Vetro"}[tile]
			self.tool_button((20 + index * 94, 414, 88, 30), f"{key - pygame.K_0} {label}", self.brush == tile and not self.object_tool)
		for index, (key, model_type) in enumerate(MODEL_TOOLS.items()):
			self.tool_button((20 + index * 118, 450, 110, 30), f"{key - pygame.K_0} {model_type.title()}", self.object_tool == model_type)
		self.tool_button((374, 450, 106, 30), "F Guardiano", self.enemy_tool == "sentinel")
		selection = f"Varco {self.portal_next}" if self.portal_tool else self.enemy_tool or self.object_tool or self.brush
		if self.object_tool == "block":
			selection = f"BLOCCO {self.block_size[0]:.1f}x{self.block_size[1]:.1f}x{self.block_size[2]:.1f}"
		self.label(f"Modelli {len(self.objects)} | Nemici {len(self.enemies)} | Cutscene {len(self.cutscenes)} | {selection}", (20, 488), self.small, (157, 174, 161))

	def draw_preview(self):
		if self.preview_mode == "game":
			preview = pygame.Surface(PREVIEW_RECT.size)
			px, py, _angle = self.spawn
			render_world(preview, self.grid, self.colors, px, py, self.preview_direction,
						 objects=[*self.objects, *self.enemies], texture_style=self.texture_style,
						 custom_texture=self.custom_texture)
			self.screen.blit(preview, PREVIEW_RECT.topleft)
			self.label("ANTEPRIMA 3D LIVE  |  trascina per ruotare", (520, 82), self.small, (179, 201, 180))
		else:
			self.draw_layer_stack()
		pygame.draw.rect(self.screen, (126, 151, 132), PREVIEW_RECT, 1)

	def draw_layer_stack(self):
		area = PREVIEW_RECT
		pygame.draw.rect(self.screen, (31, 40, 38), area)
		count = len(self.layers)
		max_dimension = max(max(len(layer["grid"][0]) for layer in self.layers), max(len(layer["grid"]) for layer in self.layers))
		unit = min(7.0, 250 / max_dimension)
		center_x = area.centerx
		base_y = area.y + 38
		step_y = unit * 0.48
		layer_gap = min(42, 170 / max(1, count))
		for index, layer in enumerate(self.layers):
			grid = layer["grid"]
			layer_y = base_y + (count - index - 1) * layer_gap
			for row in range(len(grid) - 1, -1, -1):
				for column in range(len(grid[row])):
					tile = grid[row][column]
					center = (center_x + (column - row) * unit, layer_y + (column + row) * step_y)
					points = [(center[0], center[1] - step_y), (center[0] + unit, center[1]),
							  (center[0], center[1] + step_y), (center[0] - unit, center[1])]
					if tile == "1":
						color = (84, 105, 93) if index == self.layer_index else (52, 65, 61)
					elif tile == "A":
						color = (237, 139, 73)
					elif tile == "B":
						color = (74, 190, 211)
					elif tile == "D":
						color = (184, 145, 81)
					elif tile == "T":
						color = (73, 135, 145)
					elif tile in TILE_COLORS:
						color = TILE_COLORS[tile]
					else:
						color = (66, 83, 76) if index == self.layer_index else (41, 52, 49)
					pygame.draw.polygon(self.screen, color, points)
					pygame.draw.polygon(self.screen, (30, 39, 36), points, 1)
					if tile in "1CL":
						lower_points = [(point[0], point[1] + 8) for point in points]
						pygame.draw.polygon(self.screen, (35, 44, 41), [points[2], points[3], lower_points[3], lower_points[2]])
						pygame.draw.polygon(self.screen, (43, 53, 49), [points[1], points[2], lower_points[2], lower_points[1]])
			if index > 0:
				left = (center_x - (len(grid) - 1) * unit, layer_y + (len(grid) - 1) * step_y)
				right = (center_x + (len(grid[0]) - 1) * unit, layer_y + (len(grid[0]) - 1) * step_y)
				pygame.draw.line(self.screen, (26, 34, 32), left, (left[0], left[1] + 8), 3)
				pygame.draw.line(self.screen, (26, 34, 32), right, (right[0], right[1] + 8), 3)
			if index == self.layer_index:
				self.label(f"{layer['name']}  (selezionato)", (area.x + 10, int(layer_y - 20)), self.small, (226, 215, 164))
		self.label("SEZIONE 3D DAL BASSO  |  piani sovrapposti", (520, 82), self.small, (179, 201, 180))

	def draw_controls(self):
		self.field("Nome", self.name, pygame.Rect(520, 398, 220, 32), self.active_field == "name")
		self.field("Porta ->", self.portal_target, pygame.Rect(750, 398, 254, 32), self.active_field == "portal")
		for key, rect in (("sky", (520, 440, 145, 34)), ("floor", (674, 440, 145, 34)), ("wall", (829, 440, 175, 34))):
			self.swatch(key, rect)
		self.button((520, 486, 44, 32), "L-")
		self.button((568, 486, 44, 32), "L+")
		self.button((620, 486, 60, 32), "W-")
		self.button((684, 486, 60, 32), "W+")
		self.button((748, 486, 60, 32), "H-")
		self.button((812, 486, 60, 32), "H+")
		self.button((876, 486, 128, 32), "SALVA")
		self.button((520, 532, 54, 32), "< MAP")
		self.button((580, 532, 54, 32), "MAP >")
		self.button((642, 532, 126, 32), "CARICA")
		self.button((780, 532, 108, 32), "RIMUOVI")
		self.button((896, 532, 108, 32), f"TEX {self.texture_style[:5].upper()}")
		self.button((520, 574, 68, 32), "PIANO -")
		self.button((594, 574, 68, 32), "PIANO +")
		self.button((668, 574, 90, 32), "+ PIANO")
		self.button((764, 574, 90, 32), "- PIANO")
		self.button((860, 574, 144, 32), "VISTA DAL BASSO" if self.preview_mode == "game" else "VISTA GIOCO")
		self.label(f"Piano {self.layer_index + 1}/{len(self.layers)}  |  {self.layers[self.layer_index]['name']}  |  preview {math.degrees(self.preview_direction) % 360:.0f}°", (520, 614), self.small, (157, 174, 161))
		self.label(self.message, (20, 614), self.small, (169, 200, 173))

	def label(self, text, position, font=None, color=(225, 230, 215)):
		self.screen.blit((font or self.font).render(text, True, color), position)

	def button(self, rect, text):
		bounds = pygame.Rect(rect)
		hovered = bounds.collidepoint(pygame.mouse.get_pos())
		pygame.draw.rect(self.screen, (77, 104, 93) if hovered else (43, 54, 50), bounds, border_radius=4)
		self.screen.blit(self.small.render(text, True, (235, 237, 225)), self.small.render(text, True, (235, 237, 225)).get_rect(center=bounds.center))

	def tool_button(self, rect, text, selected):
		bounds = pygame.Rect(rect)
		hovered = bounds.collidepoint(pygame.mouse.get_pos())
		fill = (77, 104, 93) if selected else (55, 69, 64) if hovered else (37, 46, 44)
		pygame.draw.rect(self.screen, fill, bounds, border_radius=4)
		pygame.draw.rect(self.screen, (95, 119, 105), bounds, 1, border_radius=4)
		label = self.small.render(text, True, (235, 237, 225))
		self.screen.blit(label, label.get_rect(center=bounds.center))

	def field(self, label, value, rect, active):
		pygame.draw.rect(self.screen, (49, 64, 59) if active else (37, 46, 44), rect, border_radius=4)
		self.label(f"{label}: {value or '_'}", (rect.x + 8, rect.y + 8), self.small)

	def swatch(self, key, rect):
		bounds = pygame.Rect(rect)
		pygame.draw.rect(self.screen, (43, 54, 50), bounds, border_radius=4)
		pygame.draw.rect(self.screen, self.colors[key], (bounds.right - 34, bounds.y + 5, 26, 24), border_radius=3)
		self.label(key.upper(), (bounds.x + 9, bounds.y + 9), self.small)

	def run(self):
		while self.running:
			self.clock.tick(30)
			self.refresh_external_tools()
			for event in pygame.event.get():
				self.handle_event(event)
			self.draw()
		pygame.quit()
		return 0

	def open_tool(self, filename):
		map_id = re.sub(r"[^a-zA-Z0-9_-]", "_", self.name.strip()).strip("_").lower()
		self.save()
		tool_path = Path(__file__).resolve().parent / filename
		process = subprocess.Popen([sys.executable, str(tool_path), map_id])
		self.external_tools.append((process, map_id))
		self.message = f"Aperto {filename} per {map_id}"

	def refresh_external_tools(self):
		remaining = []
		finished_maps = []
		for process, map_id in self.external_tools:
			if process.poll() is None:
				remaining.append((process, map_id))
			else:
				finished_maps.append(map_id)
		if not finished_maps:
			return
		self.maps = load_maps()
		self.map_ids = list(self.maps)
		for map_id in finished_maps:
			if map_id not in self.maps:
				continue
			data = self.maps[map_id]
			self.cutscenes = [dict(item) for item in data.get("cutscenes", [])]
			self.custom_texture = [list(row) for row in data.get("custom_texture", [])]
			self.message = f"Aggiornato {map_id}"
		self.external_tools = remaining


def main():
	return CompactEditor().run()


if __name__ == "__main__":
	sys.exit(main())