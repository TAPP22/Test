"""pyRender: a simple first-person raycaster made with pygame.

Run: python PyRender.py
Dependency: python -m pip install pygame
Controls: WASD to move, left/right arrows to turn, Esc to quit.
"""

import math
import sys

import pygame

WIDTH, HEIGHT = 960, 600
FOV = math.radians(66)
RAYS = 480
WORLD = (
	"1111111111111111",
	"1000000000000001",
	"1011100010111001",
	"1000100000100001",
	"1000101110101101",
	"1000001000000101",
	"1011001001100001",
	"1000000000000001",
	"1111111111111111",
	
)


def wall_at(x, y):
	column, row = int(x), int(y)
	return not (0 <= row < len(WORLD) and 0 <= column < len(WORLD[0])) or WORLD[row][column] == "1"


def cast_ray(px, py, ray_angle):
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
		if wall_at(map_x + 0.5, map_y + 0.5):
			return max(distance, 0.05), vertical_side


def render(screen, px, py, direction):
	screen.fill((0, 0, 0))
	pygame.draw.rect(screen, (95, 155, 205), (0, 0, WIDTH, HEIGHT // 2))
	pygame.draw.rect(screen, (58, 55, 52), (0, HEIGHT // 2, WIDTH, HEIGHT // 2))

	for ray in range(RAYS):
		ray_angle = direction - FOV / 2 + FOV * (ray + 0.5) / RAYS
		distance, vertical_side = cast_ray(px, py, ray_angle)
		distance *= max(0.001, math.cos(ray_angle - direction))
		height = min(HEIGHT * 2, int(HEIGHT / max(distance, 0.05)))
		brightness = max(30, 230 - int(distance * 18))
		if vertical_side:
			brightness = int(brightness * 0.72)
		color = (brightness, int(brightness * 0.82), int(brightness * 0.62))
		x = ray * WIDTH // RAYS
		pygame.draw.rect(screen, color, (x, (HEIGHT - height) // 2, WIDTH // RAYS + 1, height))


def main():
	from game import main as run_game
	return run_game()


if __name__ == "__main__":
	sys.exit(main())
