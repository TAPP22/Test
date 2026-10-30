"""Procedural wall textures used by the raycaster and editor preview."""

import pygame

TEXTURE_SIZE = 64


def build_texture(kind, base_color, style="brick"):
	texture = pygame.Surface((TEXTURE_SIZE, TEXTURE_SIZE), pygame.SRCALPHA)
	base = tuple(base_color)
	for y in range(TEXTURE_SIZE):
		for x in range(TEXTURE_SIZE):
			shade = 0
			if kind == "wall":
				if style == "stone":
					row = y // 20
					offset_x = (row % 2) * 13
					stone_edge = (y % 20 in (0, 1)) or ((x + offset_x) % 26 in (0, 1))
					shade = -38 if stone_edge else ((x * 3 + y * 5) % 19) - 9
				elif style == "panel":
					panel_edge = x % 16 in (0, 1) or y % 32 in (0, 1)
					shade = -38 if panel_edge else ((x * 2 + y * 3) % 15) - 7
				else:
					row = y // 16
					offset_x = 16 if row % 2 else 0
					brick_edge = (y % 16 in (0, 1)) or ((x + offset_x) % 32 in (0, 1))
					shade = -42 if brick_edge else ((x * 3 + y * 5) % 13) - 6
				alpha = 255
			elif kind == "door":
				plank_edge = x % 16 in (0, 1) or y in (0, 1, 62, 63)
				shade = -48 if plank_edge else ((x * 5 + y * 2) % 11) - 5
				alpha = 255
			elif kind == "glass":
				frame = x in range(0, 4) or y in range(0, 4) or x in range(60, 64) or y in range(60, 64)
				frame = frame or x in range(30, 34) or y in range(30, 34)
				shade = -35 if frame else 16 + ((x + y) % 15)
				alpha = 225 if frame else 105
			elif kind == "crate":
				plank_edge = x % 16 in (0, 1) or y % 21 in (0, 1)
				brace = abs((x % 32) - (y % 32)) <= 2 or abs((x % 32) + (y % 32) - 31) <= 2
				shade = -42 if plank_edge else ((x * 3 + y * 5) % 15) - 7
				if brace and not plank_edge:
					shade = 24
				alpha = 255
			elif kind == "locked":
				distance = ((x - 32) ** 2 + (y - 32) ** 2) ** 0.5
				frame = x in range(0, 4) or y in range(0, 4) or x in range(60, 64) or y in range(60, 64)
				rune = abs(distance - 17) < 2 or abs(x - 32) < 2 and y in range(20, 45)
				shade = ((x * 2 + y * 3) % 13) - 6
				if rune:
					shade = 50
				if frame:
					shade = -48
				alpha = 255
			elif kind in ("portal_a", "portal_b"):
				center_x = x - TEXTURE_SIZE / 2
				center_y = y - TEXTURE_SIZE / 2
				ring = abs((center_x * center_x + center_y * center_y) ** 0.5 - 21) < 4
				wave = int((x * 3 + y * 5) % 22)
				shade = 35 if ring else wave - 12
				alpha = 255
			else:
				shade = ((x * 7 + y * 3) % 17) - 8
				alpha = 255
			texture.set_at((x, y), tuple(max(0, min(255, channel + shade)) for channel in base) + (alpha,))
	return texture