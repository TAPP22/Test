"""Main menu and first-person raycaster gameplay."""

import math
import subprocess
import sys
from pathlib import Path

import pygame

from maps import load_maps
from settings_store import GAME_MODES, QUALITY_RAYS, load_settings, save_settings
from textures import build_texture

WIDTH, HEIGHT = 960, 600
FOV = math.radians(66)
RAYS = 480
JUMP_SPEED = 6.2
JUMP_GRAVITY = 18.0
JUMP_RELEASE_GRAVITY = 30.0
BLOCK_STEP_HEIGHT = 0.55
ROOT = Path(__file__).resolve().parent
TEXTURE_CACHE = {}
MODEL_MESHES = {
	"crystal": (
		[(0, 0, 0.0), (-0.28, 0, 0.48), (0, -0.25, 0.48), (0.28, 0, 0.48), (0, 0.25, 0.48), (0, 0, 1.05)],
		[(0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1), (5, 2, 1), (5, 3, 2), (5, 4, 3), (5, 1, 4)],
		(92, 207, 204),
	),
	"chest": (
		[(-0.4, -0.28, 0), (0.4, -0.28, 0), (0.4, 0.28, 0), (-0.4, 0.28, 0), (-0.4, -0.28, 0.42), (0.4, -0.28, 0.42), (0.4, 0.28, 0.42), (-0.4, 0.28, 0.42), (-0.4, -0.28, 0.55), (0.4, -0.28, 0.55), (0.4, 0.28, 0.55), (-0.4, 0.28, 0.55)],
		[(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 9, 8), (5, 6, 10, 9), (6, 7, 11, 10), (7, 4, 8, 11), (8, 9, 10, 11)],
		(176, 112, 62),
	),
	"statue": (
		[(-0.32, -0.25, 0), (0.32, -0.25, 0), (0.32, 0.25, 0), (-0.32, 0.25, 0), (-0.24, -0.2, 0.32), (0.24, -0.2, 0.32), (0.24, 0.2, 0.32), (-0.24, 0.2, 0.32), (-0.2, -0.18, 0.72), (0.2, -0.18, 0.72), (0.2, 0.18, 0.72), (-0.2, 0.18, 0.72), (0, 0, 0.98)],
		[(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 9, 8), (5, 6, 10, 9), (6, 7, 11, 10), (7, 4, 8, 11), (8, 9, 12), (9, 10, 12), (10, 11, 12), (11, 8, 12)],
		(151, 164, 145),
	),
	"sentinel": (
		[(-0.3, -0.24, 0), (0.3, -0.24, 0), (0.3, 0.24, 0), (-0.3, 0.24, 0),
		 (-0.23, -0.2, 0.28), (0.23, -0.2, 0.28), (0.23, 0.2, 0.28), (-0.23, 0.2, 0.28),
		 (-0.28, -0.23, 0.72), (0.28, -0.23, 0.72), (0.28, 0.23, 0.72), (-0.28, 0.23, 0.72),
		 (0, 0, 1.02), (-0.1, -0.24, 0.55), (0.1, -0.24, 0.55)],
		[(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 9, 8), (5, 6, 10, 9), (6, 7, 11, 10), (7, 4, 8, 11), (8, 9, 12), (9, 10, 12), (10, 11, 12), (11, 8, 12), (13, 14, 12)],
		(188, 74, 65),
	),
}

LIGHT_DIRECTION = math.radians(30)


def clamp(value, minimum, maximum):
	return max(minimum, min(maximum, value))


def compute_light_factor(distance, angle, facing_direction):
	base = 0.55 + 0.75 * math.cos(angle - facing_direction - LIGHT_DIRECTION)
	attenuation = 1.0 / (1.0 + distance * 0.28)
	return clamp(base * attenuation + 0.28, 0.22, 1.5)


def apply_light(base_color, factor):
	return tuple(max(0, min(255, int(channel * factor))) for channel in base_color)


def draw_environment_glow(screen, width, height, horizon, direction):
	sun_x = width * 0.5 + math.cos(direction + LIGHT_DIRECTION) * width * 0.25
	sun_y = max(18, horizon * 0.62 - math.sin(direction + LIGHT_DIRECTION) * height * 0.12)
	glow = pygame.Surface((width, height), pygame.SRCALPHA)
	for index in range(10, 0, -1):
		radius = int(min(width, height) * (0.06 + index * 0.04))
		alpha = max(8, 30 + index * 12)
		pygame.draw.ellipse(glow, (255, 220, 160, alpha), (sun_x - radius, sun_y - radius, radius * 2, radius * 2))
	screen.blit(glow, (0, 0))

	shadow = pygame.Surface((width, height), pygame.SRCALPHA)
	for depth in range(0, height - horizon, 6):
		alpha = clamp(12 + depth * 0.18, 10, 78)
		pygame.draw.rect(shadow, (0, 0, 0, int(alpha)), (0, horizon + depth, width, 6))
	screen.blit(shadow, (0, 0))


def wall_at(grid, x, y):
	column, row = int(x), int(y)
	return not (0 <= row < len(grid) and 0 <= column < len(grid[0])) or grid[row][column] in "1TABCL"


def block_dimensions(block):
	return (clamp(float(block.get("width", 0.8)), 0.15, 2.5),
			clamp(float(block.get("depth", 0.8)), 0.15, 2.5),
			clamp(float(block.get("height", 0.4)), 0.1, 2.5))


def block_overlaps(block, x, y, radius=0.18):
	width, depth, _height = block_dimensions(block)
	return (abs(x - block["x"]) < width / 2 + radius
			and abs(y - block["y"]) < depth / 2 + radius)


def custom_block_blocks(objects, x, y):
	for block in objects:
		if block.get("type") != "block" or not block_overlaps(block, x, y):
			continue
		_width, _depth, height = block_dimensions(block)
		block_z = max(0.0, float(block.get("z_offset", 0.0)))
		if block_z >= 0.9 or not block.get("climbable", True) or height > BLOCK_STEP_HEIGHT:
			return True
	return False


def block_support_height(objects, x, y):
	return max((block_dimensions(block)[2] for block in objects
				if block.get("type") == "block" and block.get("climbable", True)
				and block_dimensions(block)[2] <= BLOCK_STEP_HEIGHT
				and abs(x - block["x"]) <= block_dimensions(block)[0] / 2
				and abs(y - block["y"]) <= block_dimensions(block)[1] / 2), default=0.0)


def find_stair_destination(layers, layer_index, column, row, stair_tile):
	if stair_tile == "U":
		destination_index, destination_tile = layer_index + 1, "V"
	elif stair_tile == "V":
		destination_index, destination_tile = layer_index - 1, "U"
	else:
		return None
	if not 0 <= destination_index < len(layers):
		return None
	destination_grid = layers[destination_index]["grid"]
	if not (0 <= row < len(destination_grid) and 0 <= column < len(destination_grid[row])):
		return None
	if destination_grid[row][column] != destination_tile or wall_at(destination_grid, column + 0.5, row + 0.5):
		return None
	return destination_index, column + 0.5, row + 0.5


def trigger_action(tile):
	return {"J": "jump", "Y": "boost"}.get(tile)


def apply_route_trigger(tile, jump_height, jump_velocity, speed_boost_until, game_mode, now):
	action = trigger_action(tile)
	message = ""
	if action == "jump" and game_mode != "no_jump":
		jump_height = 0.0
		jump_velocity = JUMP_SPEED * 1.65
		message = "Piastra salto!"
	elif action == "boost":
		speed_boost_until = now + 2500
		message = "Boost attivo!"
	return jump_height, jump_velocity, speed_boost_until, message


def update_touch_triggers(objects, px, py, previous_contacts, jump_height, jump_velocity,
						 speed_boost_until, game_mode, now):
	current_contacts = set()
	message = ""
	for index, trigger in enumerate(objects):
		if trigger.get("type") != "trigger" or trigger.get("triggered_by") != "touch":
			continue
		width = clamp(float(trigger.get("width", 0.7)), 0.2, 2.5)
		depth = clamp(float(trigger.get("depth", 0.7)), 0.2, 2.5)
		if abs(px - trigger["x"]) > width / 2 or abs(py - trigger["y"]) > depth / 2:
			continue
		contact_id = trigger.get("id", index)
		current_contacts.add(contact_id)
		if contact_id in previous_contacts:
			continue
		action = trigger.get("action", "move")
		if action == "move":
			group_id = int(trigger.get("group_id", 0))
			move_blocks = clamp(float(trigger.get("move_blocks", 1.0)), 0.1, 10.0)
			moved = 0
			if group_id > 0:
				for block in objects:
					if block.get("type") == "block" and int(block.get("group_id", 0)) == group_id:
						block["z_offset"] = max(0.0, float(block.get("z_offset", 0.0))) + move_blocks
						moved += 1
			message = f"Gruppo {group_id}: {moved} blocchi mossi"
		elif action in ("jump", "boost"):
			tile = "J" if action == "jump" else "Y"
			jump_height, jump_velocity, speed_boost_until, message = apply_route_trigger(
				tile, jump_height, jump_velocity, speed_boost_until, game_mode, now)
		return current_contacts, jump_height, jump_velocity, speed_boost_until, message
	return current_contacts, jump_height, jump_velocity, speed_boost_until, message


def advance_jump(height, velocity, delta_time, held):
	gravity = JUMP_GRAVITY if held else JUMP_RELEASE_GRAVITY
	new_height = height + velocity * delta_time - 0.5 * gravity * delta_time * delta_time
	new_velocity = velocity - gravity * delta_time
	if new_height <= 0 and new_velocity < 0:
		return 0.0, 0.0
	return max(0.0, new_height), new_velocity


def find_interactable(objects, px, py, direction, grid=None, max_distance=1.8):
	nearby = []
	for object_data in objects:
		if object_data.get("type") == "block":
			continue
		delta_x = object_data["x"] - px
		delta_y = object_data["y"] - py
		distance = math.hypot(delta_x, delta_y)
		angle = math.atan2(delta_y, delta_x)
		angle_delta = (angle - direction + math.pi) % (2 * math.pi) - math.pi
		visible = grid is None or distance < cast_ray(grid, px, py, angle)[0] + 0.15
		if distance <= max_distance and abs(angle_delta) <= 0.55 and visible:
			nearby.append((distance, object_data))
	return min(nearby, key=lambda pair: pair[0])[1] if nearby else None


def find_paired_gate(grid, tile, current_x, current_y):
	for row, line in enumerate(grid):
		for column, candidate in enumerate(line):
			if candidate == tile and (column != current_x or row != current_y):
				return column + 0.5, row + 0.5
	return None


def find_gate_exit(grid, gate_x, gate_y, direction):
	forward_x, forward_y = math.cos(direction), math.sin(direction)
	candidates = []
	for offset_x, offset_y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
		if not wall_at(grid, gate_x + offset_x + 0.5, gate_y + offset_y + 0.5):
			dot = offset_x * forward_x + offset_y * forward_y
			candidates.append((dot, gate_x + offset_x + 0.5, gate_y + offset_y + 0.5))
	if candidates:
		_, exit_x, exit_y = max(candidates)
		return exit_x, exit_y
	return gate_x + 0.5, gate_y + 0.5


def cast_ray(grid, px, py, ray_angle):
	direction_x, direction_y = math.cos(ray_angle), math.sin(ray_angle)
	map_x, map_y = int(px), int(py)
	delta_x = abs(1 / direction_x) if direction_x else float("inf")
	delta_y = abs(1 / direction_y) if direction_y else float("inf")
	step_x = 1 if direction_x >= 0 else -1
	step_y = 1 if direction_y >= 0 else -1
	side_x = (px - map_x) * delta_x if direction_x < 0 else (map_x + 1 - px) * delta_x
	side_y = (py - map_y) * delta_y if direction_y < 0 else (map_y + 1 - py) * delta_y
	while True:
		if side_x < side_y:
			side_x += delta_x
			map_x += step_x
			distance, vertical_side = side_x - delta_x, True
		else:
			side_y += delta_y
			map_y += step_y
			distance, vertical_side = side_y - delta_y, False
		if not (0 <= map_y < len(grid) and 0 <= map_x < len(grid[0])):
			return max(distance, 0.05), vertical_side, "1", 0.0
		tile = grid[map_y][map_x]
		if tile in "1DTABCL":
			hit_x = px + direction_x * distance
			hit_y = py + direction_y * distance
			texture_u = hit_y % 1 if vertical_side else hit_x % 1
			return max(distance, 0.05), vertical_side, tile, texture_u


def find_puzzle_target(grid, px, py, direction, max_distance=1.8):
	targets = []
	for row, line in enumerate(grid):
		for column, tile in enumerate(line):
			if tile not in "PQ":
				continue
			target_x, target_y = column + 0.5, row + 0.5
			delta_x, delta_y = target_x - px, target_y - py
			distance = math.hypot(delta_x, delta_y)
			angle_delta = (math.atan2(delta_y, delta_x) - direction + math.pi) % (2 * math.pi) - math.pi
			visible_distance = cast_ray(grid, px, py, math.atan2(delta_y, delta_x))[0]
			if distance <= max_distance and abs(angle_delta) <= 0.4 and distance < visible_distance + 0.1:
				targets.append((distance, column, row, tile))
	return min(targets) if targets else None


def activate_puzzle_tile(grid, column, row):
	if grid[row][column] not in "PQ":
		return False
	grid[row] = grid[row][:column] + grid[row][column].lower() + grid[row][column + 1:]
	required_tiles = [(tile_x, tile_y) for tile_y, line in enumerate(grid)
					  for tile_x, tile in enumerate(line) if tile in "PQpq"]
	required_types = {grid[tile_y][tile_x].upper() for tile_x, tile_y in required_tiles}
	if not {"P", "Q"}.issubset(required_types) or not all(grid[tile_y][tile_x].islower() for tile_x, tile_y in required_tiles):
		return False
	for tile_y, line in enumerate(grid):
		grid[tile_y] = line.replace("L", "0")
	return True


def draw_puzzle_markers(screen, grid, px, py, direction, horizon, focal_length, wall_depths):
	width = screen.get_width()
	forward_x, forward_y = math.cos(direction), math.sin(direction)
	for row, line in enumerate(grid):
		for column, tile in enumerate(line):
			if tile not in "PQpq":
				continue
			delta_x, delta_y = column + 0.5 - px, row + 0.5 - py
			depth = delta_x * forward_x + delta_y * forward_y
			if depth <= 0.2:
				continue
			lateral = -delta_x * forward_y + delta_y * forward_x
			center_x = int(width / 2 + lateral * focal_length / depth)
			if center_x < 0 or center_x >= width:
				continue
			ray_index = min(len(wall_depths) - 1, max(0, int(center_x / width * len(wall_depths))))
			if depth >= wall_depths[ray_index]:
				continue
			radius = max(3, int(focal_length * 0.16 / depth))
			center_y = int(horizon + radius * 0.2)
			is_active = tile.islower()
			if is_active:
				color = (102, 244, 211)
			elif tile.upper() == "P":
				color = (244, 190, 83)
			else:
				color = (95, 205, 239)
			points = [(center_x, center_y - radius // 2), (center_x + radius, center_y),
					  (center_x, center_y + radius // 2), (center_x - radius, center_y)]
			pygame.draw.polygon(screen, (24, 34, 33), points)
			pygame.draw.polygon(screen, color, points, max(1, radius // 8))
			pygame.draw.circle(screen, color, (center_x, center_y), max(2, radius // 5))


def draw_route_tiles(screen, grid, px, py, direction, horizon, focal_length, wall_depths):
	width = screen.get_width()
	forward_x, forward_y = math.cos(direction), math.sin(direction)
	tile_colors = {"U": (172, 210, 157), "V": (172, 210, 157), "J": (255, 166, 69), "Y": (91, 209, 245)}
	for row, line in enumerate(grid):
		for column, tile in enumerate(line):
			if tile not in tile_colors:
				continue
			delta_x, delta_y = column + 0.5 - px, row + 0.5 - py
			depth = delta_x * forward_x + delta_y * forward_y
			if depth <= 0.2:
				continue
			lateral = -delta_x * forward_y + delta_y * forward_x
			center_x = int(width / 2 + lateral * focal_length / depth)
			if center_x < 0 or center_x >= width:
				continue
			ray_index = min(len(wall_depths) - 1, max(0, int(center_x / width * len(wall_depths))))
			if depth >= wall_depths[ray_index]:
				continue
			size = max(4, int(focal_length * 0.24 / depth))
			center_y = int(horizon + size * 0.35)
			color = tile_colors[tile]
			if tile in "UV":
				for step in range(3):
					y = center_y - step * max(2, size // 5)
					pygame.draw.line(screen, color, (center_x - size // 2, y), (center_x + size // 2, y), max(1, size // 8))
			else:
				pygame.draw.rect(screen, (24, 34, 33), (center_x - size // 2, center_y - size // 4, size, size // 2))
				pygame.draw.rect(screen, color, (center_x - size // 2, center_y - size // 4, size, size // 2), max(1, size // 9))
				if tile == "J":
					pygame.draw.line(screen, color, (center_x, center_y + size // 5), (center_x, center_y - size // 5), max(1, size // 7))
				else:
					pygame.draw.line(screen, color, (center_x - size // 5, center_y), (center_x + size // 5, center_y), max(1, size // 7))


def render_world(screen, grid, colors, px, py, direction, pitch=0.0, jump_height=0.0, objects=(), texture_style="brick", custom_texture=(), fov=FOV, ray_count_override=None, soft_shadows=True):
	width, height = screen.get_size()
	ray_count = ray_count_override or max(80, width // 2)
	focal_length = width / (2 * math.tan(fov / 2))
	jump_screen_offset = jump_height * focal_length / 1.6
	horizon = max(0, min(height, int(height / 2 + pitch * height + jump_screen_offset)))
	pygame.draw.rect(screen, colors["sky"], (0, 0, width, height))
	draw_environment_glow(screen, width, height, horizon, direction)
	pygame.draw.rect(screen, colors["floor"], (0, horizon, width, height - horizon))
	wall_depths = []
	for ray in range(ray_count):
		ray_angle = direction - fov / 2 + fov * (ray + 0.5) / ray_count
		distance, vertical_side, tile, texture_u = cast_ray(grid, px, py, ray_angle)
		distance *= max(0.001, math.cos(ray_angle - direction))
		wall_depths.append(distance)
		wall_height = min(height * 2, int(height / max(distance, 0.05)))
		brightness = max(30, int((230 - distance * 18) * compute_light_factor(distance, ray_angle, direction)))
		if vertical_side:
			brightness = int(brightness * 0.72)
		material = {"1": "wall", "D": "door", "T": "glass", "A": "portal_a", "B": "portal_b", "C": "crate", "L": "locked"}[tile]
		material_colors = {"D": (190, 170, 95), "T": (118, 196, 198), "A": (237, 139, 73), "B": (74, 190, 211),
						   "C": (172, 112, 62), "L": (118, 150, 177)}
		base = material_colors.get(tile, colors["wall"])
		cache_key = material, tuple(base), texture_style
		if tile == "1" and custom_texture:
			custom_key = ("custom", tuple(tuple(row) for row in custom_texture))
			if custom_key not in TEXTURE_CACHE:
				custom_surface = pygame.Surface((len(custom_texture[0]), len(custom_texture)))
				for texture_y, texture_row in enumerate(custom_texture):
					for texture_x, color in enumerate(texture_row):
						custom_surface.set_at((texture_x, texture_y), pygame.Color(color))
				TEXTURE_CACHE[custom_key] = custom_surface
			texture = TEXTURE_CACHE[custom_key]
		else:
			if cache_key not in TEXTURE_CACHE:
				TEXTURE_CACHE[cache_key] = build_texture(material, base, texture_style)
			texture = TEXTURE_CACHE[cache_key]
		texture_x = min(texture.get_width() - 1, int(texture_u * texture.get_width()))
		strip = texture.subsurface((texture_x, 0, 1, texture.get_height()))
		x0 = ray * width // ray_count
		x1 = (ray + 1) * width // ray_count + 1
		strip = pygame.transform.scale(strip, (x1 - x0, max(1, wall_height)))
		if brightness < 230:
			strip.fill((brightness, brightness, brightness, 255), special_flags=pygame.BLEND_RGBA_MULT)
		screen.blit(strip, (x0, horizon - wall_height // 2))
	draw_puzzle_markers(screen, grid, px, py, direction, horizon, focal_length, wall_depths)
	draw_route_tiles(screen, grid, px, py, direction, horizon, focal_length, wall_depths)
	draw_models(screen, objects, px, py, direction, horizon, jump_height, focal_length, wall_depths, soft_shadows)


def draw_soft_shadow(screen, center_x, center_y, radius_x, radius_y):
	width, height = screen.get_size()
	left, top = int(center_x - radius_x), int(center_y - radius_y)
	shadow_width, shadow_height = max(2, int(radius_x * 2)), max(2, int(radius_y * 2))
	if left >= width or top >= height or left + shadow_width <= 0 or top + shadow_height <= 0:
		return
	shadow = pygame.Surface((shadow_width, shadow_height), pygame.SRCALPHA)
	for index in range(7, 0, -1):
		inset_x = int(shadow_width * (1 - index / 5) / 2)
		inset_y = int(shadow_height * (1 - index / 5) / 2)
		alpha = 12 + index * 16
		pygame.draw.ellipse(shadow, (8, 12, 12, alpha), (inset_x, inset_y, shadow_width - inset_x * 2, shadow_height - inset_y * 2))
	screen.blit(shadow, (left, top))


def draw_models(screen, objects, px, py, direction, horizon, jump_height, focal_length, wall_depths, soft_shadows=True):
	width, _height = screen.get_size()
	forward_x, forward_y = math.cos(direction), math.sin(direction)
	for object_data in sorted(objects, key=lambda item: math.hypot(item["x"] - px, item["y"] - py), reverse=True):
		delta_x, delta_y = object_data["x"] - px, object_data["y"] - py
		depth = delta_x * forward_x + delta_y * forward_y
		if depth <= 0.2:
			continue
		if object_data.get("type") == "trigger":
			continue
		lateral = -delta_x * forward_y + delta_y * forward_x
		object_angle = math.atan2(delta_y, delta_x)
		light_factor = compute_light_factor(depth, object_angle, direction)
		center_x = int(width / 2 + lateral * focal_length / depth)
		if center_x < -width // 2 or center_x > width * 1.5:
			continue
		ray_index = min(len(wall_depths) - 1, max(0, int(center_x / width * len(wall_depths))))
		if depth >= wall_depths[ray_index]:
			continue
		if object_data.get("type") == "block":
			block_width, block_depth, block_height = block_dimensions(object_data)
			half_width, half_depth = block_width / 2, block_depth / 2
			vertices = [(-half_width, -half_depth, 0), (half_width, -half_depth, 0),
						(half_width, half_depth, 0), (-half_width, half_depth, 0),
						(-half_width, -half_depth, block_height), (half_width, -half_depth, block_height),
						(half_width, half_depth, block_height), (-half_width, half_depth, block_height)]
			faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6),
					 (3, 0, 4, 7), (4, 5, 6, 7), (0, 3, 2, 1)]
			base_color = tuple(object_data.get("color", (166, 116, 76)))
		else:
			vertices, faces, base_color = MODEL_MESHES.get(object_data.get("type", "crystal"), MODEL_MESHES["crystal"])
		if soft_shadows:
			shadow_y = horizon + focal_length * 0.18 / depth
			shadow_width = max(2, focal_length * (0.52 + 0.16 * light_factor) / depth)
			draw_soft_shadow(screen, center_x, shadow_y, shadow_width, max(2, shadow_width * 0.28))
		projected = []
		for local_x, local_y, world_z in vertices:
			local_lateral = lateral + local_x
			local_depth = depth + local_y
			object_z = float(object_data.get("z_offset", 0.0))
			projected.append((width / 2 + local_lateral * focal_length / local_depth,
						  horizon - (world_z + object_z - jump_height) * focal_length / local_depth))
		for face_index, face in enumerate(faces):
			average_depth = depth + sum(vertices[index][1] for index in face) / len(face)
			if average_depth >= wall_depths[ray_index]:
				continue
			shade = 0.5 + 0.55 * light_factor + (face_index % 4) * 0.08
			color = apply_light(base_color, clamp(shade, 0.35, 1.5))
			points = [projected[index] for index in face]
			pygame.draw.polygon(screen, color, points)
			pygame.draw.polygon(screen, tuple(int(channel * 0.55) for channel in base_color), points, 1)


def draw_text(surface, font, text, position, color=(235, 237, 230)):
	surface.blit(font.render(text, True, color), position)


def draw_button(surface, font, rect, label, mouse_position, selected=False):
	button = pygame.Rect(rect)
	fill = (77, 104, 93) if selected or button.collidepoint(mouse_position) else (38, 48, 46)
	pygame.draw.rect(surface, fill, button, border_radius=5)
	pygame.draw.rect(surface, (105, 132, 118), button, 1, border_radius=5)
	text = font.render(label, True, (242, 240, 222))
	surface.blit(text, text.get_rect(center=button.center))
	return button


def main():
	pygame.init()
	settings = load_settings()
	fullscreen_flag = pygame.FULLSCREEN if settings["fullscreen"] else 0
	screen = pygame.display.set_mode((WIDTH, HEIGHT), fullscreen_flag)
	scene_surface = pygame.Surface((WIDTH // 2, HEIGHT // 2))
	pygame.display.set_caption("pyRender | Raycaster")
	clock = pygame.time.Clock()
	title_font = pygame.font.Font(None, 64)
	font = pygame.font.Font(None, 30)
	small_font = pygame.font.Font(None, 22)
	maps = load_maps()
	if not maps:
		pygame.quit()
		return 1
	map_ids = list(maps)
	selected_map = "atrium" if "atrium" in maps else map_ids[0]
	map_scroll = 0
	sensitivity = settings["mouse_sensitivity"]
	mouse_look = settings["mouse_look"]
	invert_mouse_y = settings["invert_mouse_y"]
	game_mode = settings["game_mode"]
	mode = "menu"
	px, py, direction = 2.5, 1.5, 0.0
	layer_index = 0
	pitch, jump_height, jump_velocity = 0.0, 0.0, 0.0
	last_message, message_until = "", 0
	player_elevation = 0.0
	speed_boost_until = 0
	last_stair_contact = None
	trigger_contacts = set()
	active_cutscene = None
	cutscene_queue = []
	cutscene_until = 0
	run_started = 0
	portal_cooldown = 0.0
	editor_process = None
	running = True

	def enter_game(map_id):
		nonlocal selected_map, px, py, direction, layer_index, pitch, jump_height, jump_velocity, mode
		nonlocal active_cutscene, cutscene_queue, cutscene_until, run_started
		nonlocal player_elevation, speed_boost_until, last_stair_contact, trigger_contacts
		selected_map = map_id
		px, py, direction = maps[map_id]["spawn"]
		layer_index = 0
		pitch, jump_height, jump_velocity = 0.0, 0.0, 0.0
		player_elevation, speed_boost_until, last_stair_contact = 0.0, 0, None
		trigger_contacts = set()
		mode = "game"
		run_started = pygame.time.get_ticks()
		cutscene_queue = list(maps[map_id].get("cutscenes", []))
		active_cutscene = cutscene_queue.pop(0) if cutscene_queue else None
		cutscene_until = pygame.time.get_ticks() + int(active_cutscene.get("duration", 4) * 1000) if active_cutscene else 0
		pygame.event.set_grab(True)
		pygame.mouse.set_visible(False)

	while running:
		dt = min(clock.tick(60) / 1000, 0.05)
		mouse_position = pygame.mouse.get_pos()
		if editor_process is not None and editor_process.poll() is not None:
			previous_map = selected_map
			maps = load_maps()
			map_ids = list(maps)
			selected_map = previous_map if previous_map in maps else map_ids[0]
			editor_process = None
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
				settings["fullscreen"] = not settings["fullscreen"]
				screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN if settings["fullscreen"] else 0)
				save_settings(settings)
			elif mode == "game":
				if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					mode = "menu"
					pygame.event.set_grab(False)
					pygame.mouse.set_visible(True)
				elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and jump_height == 0 and not active_cutscene and game_mode != "no_jump":
					jump_velocity = JUMP_SPEED
				elif event.type == pygame.KEYDOWN and event.key == pygame.K_PAGEUP:
					layer_index = min(layer_index + 1, len(maps[selected_map]["layers"]) - 1)
					last_stair_contact = None
				elif event.type == pygame.KEYDOWN and event.key == pygame.K_PAGEDOWN:
					layer_index = max(0, layer_index - 1)
					last_stair_contact = None
				elif event.type == pygame.KEYDOWN and event.key == pygame.K_e:
					active_layer = maps[selected_map]["layers"][layer_index]
					objects = active_layer.get("objects", [])
					target_object = find_interactable(objects, px, py, direction, active_layer["grid"])
					if target_object:
						last_message = target_object.get("message", target_object.get("name", "Oggetto"))
						message_until = pygame.time.get_ticks() + 2600
						if target_object.get("action") == "collect":
							objects.remove(target_object)
					else:
						grid = active_layer["grid"]
						target_tile = find_puzzle_target(grid, px, py, direction)
						if target_tile:
							_, tile_x, tile_y, tile_type = target_tile
							if activate_puzzle_tile(grid, tile_x, tile_y):
								last_message = "Enigma risolto: blocco aperto!"
							elif tile_type in "PQ":
								last_message = f"Runa {tile_type} attivata: cerca tutte le altre rune"
							message_until = pygame.time.get_ticks() + 2200
				elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE) and active_cutscene:
					active_cutscene = cutscene_queue.pop(0) if cutscene_queue else None
					cutscene_until = pygame.time.get_ticks() + int(active_cutscene.get("duration", 4) * 1000) if active_cutscene else 0
				elif event.type == pygame.MOUSEMOTION and mouse_look:
					direction += event.rel[0] * sensitivity
					vertical_sign = 1 if invert_mouse_y else -1
					pitch = max(-0.45, min(0.45, pitch + event.rel[1] * sensitivity * vertical_sign))
			elif mode == "maps" and event.type == pygame.MOUSEWHEEL:
				map_scroll = max(0, min(max(0, len(map_ids) - 5), map_scroll - event.y))
			elif mode != "game":
				if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
					if mode == "menu":
						running = False
					else:
						mode = "menu"
				elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
					if mode == "menu":
						if start_button.collidepoint(event.pos):
							enter_game(selected_map)
						elif maps_button.collidepoint(event.pos):
							mode = "maps"
						elif settings_button.collidepoint(event.pos):
							mode = "settings"
						elif modes_button.collidepoint(event.pos):
							mode = "modes"
						elif editor_button.collidepoint(event.pos):
							editor_process = subprocess.Popen([sys.executable, str(ROOT / "MapEditor.py")], cwd=ROOT)
						elif quit_button.collidepoint(event.pos):
							running = False
					elif mode == "maps":
						for visible_index in range(5):
							index = map_scroll + visible_index
							if index < len(map_ids) and pygame.Rect(300, 180 + visible_index * 56, 440, 44).collidepoint(event.pos):
								selected_map = map_ids[index]
						if back_button.collidepoint(event.pos):
							mode = "menu"
					elif mode == "settings":
						if lower_button.collidepoint(event.pos):
							sensitivity = max(0.0005, sensitivity - 0.0005)
							settings["mouse_sensitivity"] = sensitivity
						elif raise_button.collidepoint(event.pos):
							sensitivity = min(0.01, sensitivity + 0.0005)
							settings["mouse_sensitivity"] = sensitivity
						elif mouse_button.collidepoint(event.pos):
							mouse_look = not mouse_look
							settings["mouse_look"] = mouse_look
						elif invert_button.collidepoint(event.pos):
							invert_mouse_y = not invert_mouse_y
							settings["invert_mouse_y"] = invert_mouse_y
						elif fov_lower_button.collidepoint(event.pos):
							settings["fov"] = max(50, settings["fov"] - 4)
						elif fov_raise_button.collidepoint(event.pos):
							settings["fov"] = min(100, settings["fov"] + 4)
						elif quality_button.collidepoint(event.pos):
							quality_names = list(QUALITY_RAYS)
							quality_index = quality_names.index(settings["quality"])
							settings["quality"] = quality_names[(quality_index + 1) % len(quality_names)]
						elif fullscreen_button.collidepoint(event.pos):
							settings["fullscreen"] = not settings["fullscreen"]
							screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN if settings["fullscreen"] else 0)
						elif shadows_button.collidepoint(event.pos):
							settings["soft_shadows"] = not settings["soft_shadows"]
						elif back_button.collidepoint(event.pos):
							mode = "menu"
						save_settings(settings)
					elif mode == "modes":
						for index, mode_id in enumerate(GAME_MODES):
							if pygame.Rect(250, 170 + index * 92, 460, 54).collidepoint(event.pos):
								game_mode = mode_id
								settings["game_mode"] = mode_id
								save_settings(settings)
							if back_button.collidepoint(event.pos):
								mode = "menu"

		if mode == "game":
			if active_cutscene and pygame.time.get_ticks() >= cutscene_until:
				active_cutscene = cutscene_queue.pop(0) if cutscene_queue else None
				cutscene_until = pygame.time.get_ticks() + int(active_cutscene.get("duration", 4) * 1000) if active_cutscene else 0
			if portal_cooldown > 0:
				portal_cooldown = max(0.0, portal_cooldown - dt)
			active_layer = maps[selected_map]["layers"][layer_index]
			grid = active_layer["grid"]
			active_objects = active_layer.get("objects", [])
			active_enemies = active_layer.get("enemies", [])
			keys = pygame.key.get_pressed()
			direction += (int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])) * 2.0 * dt
			previous_cell = (int(px), int(py))
			forward = 0 if active_cutscene else int(keys[pygame.K_w] or keys[pygame.K_UP]) - int(keys[pygame.K_s] or keys[pygame.K_DOWN])
			strafe = 0 if active_cutscene else int(keys[pygame.K_d]) - int(keys[pygame.K_a])
			move_speed = 4.8 if pygame.time.get_ticks() < speed_boost_until else 3.0
			dx = (math.cos(direction) * forward - math.sin(direction) * strafe) * move_speed * dt
			dy = (math.sin(direction) * forward + math.cos(direction) * strafe) * move_speed * dt
			if not wall_at(grid, px + dx, py) and not custom_block_blocks(active_objects, px + dx, py):
				px += dx
			if not wall_at(grid, px, py + dy) and not custom_block_blocks(active_objects, px, py + dy):
				py += dy
			player_elevation = block_support_height(active_objects, px, py)
			if jump_height > 0 or jump_velocity > 0:
				jump_height, jump_velocity = advance_jump(
					jump_height, jump_velocity, dt, bool(keys[pygame.K_SPACE]))
			current_cell = (int(px), int(py))
			if current_cell != previous_cell:
				entered_tile = grid[current_cell[1]][current_cell[0]]
				jump_height, jump_velocity, speed_boost_until, trigger_message = apply_route_trigger(
					entered_tile, jump_height, jump_velocity, speed_boost_until, game_mode, pygame.time.get_ticks())
				if trigger_message:
					last_message = trigger_message
					message_until = pygame.time.get_ticks() + 1200
			trigger_contacts, jump_height, jump_velocity, speed_boost_until, trigger_message = update_touch_triggers(
				active_objects, px, py, trigger_contacts, jump_height, jump_velocity,
				speed_boost_until, game_mode, pygame.time.get_ticks())
			if trigger_message:
				last_message = trigger_message
				message_until = pygame.time.get_ticks() + 1500
			for enemy in active_enemies if not active_cutscene else []:
				delta_x, delta_y = px - enemy["x"], py - enemy["y"]
				distance = math.hypot(delta_x, delta_y)
				if 0.65 < distance < 8 and distance < cast_ray(grid, enemy["x"], enemy["y"], math.atan2(delta_y, delta_x))[0] + 0.2:
					speed = 0.75 * dt / max(distance, 0.01)
					enemy_dx, enemy_dy = delta_x * speed, delta_y * speed
					if not wall_at(grid, enemy["x"] + enemy_dx, enemy["y"]) and not custom_block_blocks(active_objects, enemy["x"] + enemy_dx, enemy["y"]):
						enemy["x"] += enemy_dx
					if not wall_at(grid, enemy["x"], enemy["y"] + enemy_dy) and not custom_block_blocks(active_objects, enemy["x"], enemy["y"] + enemy_dy):
						enemy["y"] += enemy_dy
				elif distance <= 0.65 and not active_cutscene:
					px, py, direction = maps[selected_map]["spawn"]
					last_message = "Il Guardiano ti ha ricondotto all'ingresso"
					message_until = pygame.time.get_ticks() + 1800
					break
			stair_row, stair_column = int(py), int(px)
			stair_tile = grid[stair_row][stair_column]
			stair_contact = (layer_index, stair_row, stair_column)
			if stair_tile in "UV" and stair_contact != last_stair_contact:
				destination = find_stair_destination(maps[selected_map]["layers"], layer_index,
											 stair_column, stair_row, stair_tile)
				if destination:
					layer_index, px, py = destination
					last_stair_contact = (layer_index, stair_row, stair_column)
					player_elevation = 0.0
					active_layer = maps[selected_map]["layers"][layer_index]
					grid = active_layer["grid"]
					active_objects = active_layer.get("objects", [])
					active_enemies = active_layer.get("enemies", [])
					last_message = f"Piano: {active_layer['name']}"
					message_until = pygame.time.get_ticks() + 1600
			elif stair_tile not in "UV":
				last_stair_contact = None
			if grid[int(py)][int(px)] == "D":
				portal = maps[selected_map].get("portal", {})
				target = portal.get("map")
				if target in maps:
					px, py, direction = portal.get("spawn", maps[target]["spawn"])
					selected_map = target
					layer_index = 0
					player_elevation = 0.0
					last_stair_contact = None
					cutscene_queue = list(maps[selected_map].get("cutscenes", []))
					active_cutscene = cutscene_queue.pop(0) if cutscene_queue else None
					cutscene_until = pygame.time.get_ticks() + int(active_cutscene.get("duration", 4) * 1000) if active_cutscene else 0
					active_layer = maps[selected_map]["layers"][layer_index]
					grid = active_layer["grid"]
					active_objects = active_layer.get("objects", [])
					active_enemies = active_layer.get("enemies", [])
					last_message = f"Mappa: {maps[target]['name']}"
					message_until = pygame.time.get_ticks() + 1800
			elif portal_cooldown == 0:
				gate_contact = None
				for gate_y, gate_row in enumerate(grid):
					for gate_x, gate_tile in enumerate(gate_row):
						if gate_tile in "AB" and math.hypot(px - gate_x - 0.5, py - gate_y - 0.5) <= 0.72:
							gate_contact = (gate_x, gate_y, gate_tile)
							break
					if gate_contact:
						break
				if gate_contact:
					gate_x, gate_y, gate_tile = gate_contact
					paired = find_paired_gate(grid, "B" if gate_tile == "A" else "A", gate_x, gate_y)
					if paired:
						px, py = find_gate_exit(grid, int(paired[0]), int(paired[1]), direction)
						portal_cooldown = 0.65
						last_message = "Varco collegato"
						message_until = pygame.time.get_ticks() + 1000
			render_world(scene_surface, grid, maps[selected_map]["colors"], px, py, direction,
						 pitch, jump_height + player_elevation, [*active_objects, *active_enemies], maps[selected_map].get("texture_style", "brick"),
						 maps[selected_map].get("custom_texture", []), math.radians(settings["fov"]),
						 QUALITY_RAYS[settings["quality"]], settings["soft_shadows"])
			screen.blit(pygame.transform.scale(scene_surface, (WIDTH, HEIGHT)), (0, 0))
			if pygame.time.get_ticks() < message_until:
				draw_text(screen, font, last_message, (WIDTH // 2 - 90, 30))
			if game_mode == "sprint":
				run_seconds = max(0, (pygame.time.get_ticks() - run_started) // 1000)
				draw_text(screen, font, f"TEMPO  {run_seconds // 60:02}:{run_seconds % 60:02}", (WIDTH - 190, 22))
			pygame.draw.line(screen, "white", (WIDTH // 2 - 7, HEIGHT // 2), (WIDTH // 2 + 7, HEIGHT // 2))
			pygame.draw.line(screen, "white", (WIDTH // 2, HEIGHT // 2 - 7), (WIDTH // 2, HEIGHT // 2 + 7))
			draw_text(screen, small_font, f"{game_mode.replace('_', ' ').upper()} | Piano {layer_index + 1}/{len(maps[selected_map]['layers'])} | WASD | Mouse | E usa | Esc", (14, HEIGHT - 30))
			nearby_object = find_interactable(active_objects, px, py, direction, grid)
			if nearby_object and pygame.time.get_ticks() >= message_until:
				draw_text(screen, font, f"E  {nearby_object.get('name', 'Interagisci')}", (WIDTH // 2 - 90, 34))
			elif find_puzzle_target(grid, px, py, direction) and pygame.time.get_ticks() >= message_until:
				draw_text(screen, font, "E  Attiva runa", (WIDTH // 2 - 90, 34), (242, 205, 119))
			if active_cutscene:
				pygame.draw.rect(screen, (10, 14, 14), (0, 0, WIDTH, 116))
				pygame.draw.rect(screen, (10, 14, 14), (0, HEIGHT - 126, WIDTH, 126))
				draw_text(screen, font, active_cutscene.get("title", ""), (54, 28))
				draw_text(screen, small_font, active_cutscene.get("text", ""), (54, 66))
				draw_text(screen, small_font, "Invio per continuare", (WIDTH - 190, HEIGHT - 32), (170, 190, 173))
		else:
			screen.fill((21, 28, 27))
			pygame.draw.rect(screen, (32, 43, 40), (0, 0, WIDTH, HEIGHT))
			pygame.draw.line(screen, (93, 120, 104), (80, 110), (880, 110), 2)
			if mode == "menu":
				pygame.draw.rect(screen, (193, 139, 74), (100, 91, 8, 48))
				draw_text(screen, title_font, "TAPPETO22", (122, 91), (231, 207, 159))
				draw_text(screen, small_font, "PYRENDER / RAYCASTER", (124, 132), (164, 191, 170))
				draw_text(screen, small_font, f"LIVELLO {maps[selected_map].get('level', 1)}  /  {maps[selected_map]['name']}", (104, 157), (165, 190, 170))
				start_button = draw_button(screen, font, (104, 220, 320, 54), "Gioca", mouse_position, True)
				maps_button = draw_button(screen, font, (104, 288, 320, 48), "Seleziona mappa", mouse_position)
				settings_button = draw_button(screen, font, (104, 350, 320, 48), "Impostazioni", mouse_position)
				editor_button = draw_button(screen, font, (104, 412, 320, 48), "Apri editor mappe", mouse_position)
				quit_button = draw_button(screen, font, (104, 474, 320, 48), "Esci", mouse_position)
				modes_button = draw_button(screen, font, (104, 532, 320, 48), "Modalita di gioco", mouse_position)
				draw_text(screen, small_font, "RAYCASTER  /  ESPLORA LE MAPPE", (560, 470), (165, 190, 170))
				draw_text(screen, font, f"{game_mode.replace('_', ' ').title()}  /  F11 fullscreen", (560, 496))
			elif mode == "maps":
				draw_text(screen, title_font, "Scegli mappa", (300, 92))
				screen.set_clip(pygame.Rect(292, 168, 460, 292))
				for visible_index in range(5):
					index = map_scroll + visible_index
					if index < len(map_ids):
						map_id = map_ids[index]
						label = f"Livello {maps[map_id].get('level', 1)}  |  {maps[map_id]['name']}"
						draw_button(screen, font, (300, 180 + visible_index * 56, 440, 44), label, mouse_position, map_id == selected_map)
				screen.set_clip(None)
				draw_text(screen, small_font, f"{map_scroll + 1}-{min(map_scroll + 5, len(map_ids))} / {len(map_ids)}  |  rotella per scorrere", (300, 466), (165, 190, 170))
				back_button = draw_button(screen, font, (400, 500, 160, 46), "Indietro", mouse_position)
			elif mode == "settings":
				draw_text(screen, title_font, "Impostazioni", (300, 92))
				draw_text(screen, font, "Sensibilita mouse", (270, 160))
				lower_button = draw_button(screen, font, (510, 150, 52, 40), "-", mouse_position)
				draw_text(screen, font, f"{sensitivity:.4f}", (580, 159))
				raise_button = draw_button(screen, font, (665, 150, 52, 40), "+", mouse_position)
				draw_text(screen, font, "Campo visivo", (270, 218))
				fov_lower_button = draw_button(screen, font, (510, 208, 52, 40), "-", mouse_position)
				draw_text(screen, font, f"{settings['fov']} gradi", (580, 217))
				fov_raise_button = draw_button(screen, font, (665, 208, 52, 40), "+", mouse_position)
				quality_button = draw_button(screen, font, (270, 270, 447, 42), f"Qualita rendering: {settings['quality']}", mouse_position)
				mouse_button = draw_button(screen, font, (270, 324, 447, 42), f"Mouse look: {'attivo' if mouse_look else 'disattivato'}", mouse_position, mouse_look)
				invert_button = draw_button(screen, font, (270, 378, 447, 42), f"Inverti asse verticale: {'si' if invert_mouse_y else 'no'}", mouse_position, invert_mouse_y)
				fullscreen_button = draw_button(screen, font, (270, 432, 447, 42), f"Fullscreen: {'attivo' if settings['fullscreen'] else 'disattivato'} (F11)", mouse_position, settings["fullscreen"])
				shadows_button = draw_button(screen, font, (270, 486, 447, 42), f"Ombre morbide: {'attive' if settings['soft_shadows'] else 'disattive'}", mouse_position, settings["soft_shadows"])
				back_button = draw_button(screen, font, (400, 532, 160, 46), "Indietro", mouse_position)
			elif mode == "modes":
				draw_text(screen, title_font, "Modalita di gioco", (280, 92))
				mode_labels = {
					"explore": ("Esplora", "Nessun timer: esplora mappe e oggetti con calma."),
					"sprint": ("Corsa a tempo", "Cronometro sempre visibile. Cerca l'uscita più veloce."),
					"no_jump": ("Precisione", "Il salto e disattivato: conta il percorso, non la fretta."),
				}
				for index, mode_id in enumerate(GAME_MODES):
					label, description = mode_labels[mode_id]
					draw_button(screen, font, (250, 170 + index * 92, 460, 54), label, mouse_position, game_mode == mode_id)
					draw_text(screen, small_font, description, (270, 228 + index * 92), (165, 190, 170))
				back_button = draw_button(screen, font, (400, 500, 160, 46), "Indietro", mouse_position)
		pygame.display.flip()

	pygame.event.set_grab(False)
	pygame.mouse.set_visible(True)
	pygame.quit()
	return 0


if __name__ == "__main__":
	sys.exit(main())