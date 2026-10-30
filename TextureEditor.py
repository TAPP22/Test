"""Pixel texture painter for pyRender wall materials."""

import sys
from collections import deque

import pygame

from maps import load_maps, save_map

WIDTH, HEIGHT = 660, 610
SIZE = 16
CELL = 24
ORIGIN = (24, 76)
PALETTE = [
	"#182126", "#31484b", "#55736f", "#91a89b", "#d8c8a4", "#c8794b",
	"#eea05c", "#e8d9bd", "#f4f0e2", "#4e8d91", "#86c6bb", "#5278a0",
	"#8d5b73", "#b2463a", "#dce8df", "#ffffff",
]


def main():
	map_id = sys.argv[1] if len(sys.argv) > 1 else "atrium"
	pygame.init()
	screen = pygame.display.set_mode((WIDTH, HEIGHT))
	pygame.display.set_caption(f"Texture Painter | {map_id}")
	clock = pygame.time.Clock()
	font = pygame.font.Font(None, 28)
	small = pygame.font.Font(None, 21)
	maps = load_maps()
	if map_id not in maps:
		pygame.quit()
		return 1
	data = maps[map_id]
	stored = data.get("custom_texture", [])
	pixels = [list(row) for row in stored] if len(stored) == SIZE and all(len(row) == SIZE for row in stored) else [["#31484b" for _ in range(SIZE)] for _ in range(SIZE)]
	selected = PALETTE[6]
	tool = "brush"

	def paint(x, y):
		nonlocal selected
		if tool == "eyedropper":
			selected = pixels[y][x]
		elif tool == "fill":
			target = pixels[y][x]
			queue = deque([(x, y)])
			seen = set()
			while queue:
				point_x, point_y = queue.popleft()
				if (point_x, point_y) in seen:
					continue
				seen.add((point_x, point_y))
				if pixels[point_y][point_x] != target:
					continue
				pixels[point_y][point_x] = selected
				queue.extend((next_x, next_y) for next_x, next_y in ((point_x + 1, point_y), (point_x - 1, point_y), (point_x, point_y + 1), (point_x, point_y - 1))
							 if 0 <= next_x < SIZE and 0 <= next_y < SIZE and (next_x, next_y) not in seen)
		else:
			pixels[y][x] = "#31484b" if tool == "eraser" else selected

	running = True
	while running:
		clock.tick(60)
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
				running = False
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
				save_map(map_id, {**data, "custom_texture": pixels})
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_b:
				tool = "brush"
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
				tool = "fill"
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_i:
				tool = "eyedropper"
			elif event.type == pygame.KEYDOWN and event.key == pygame.K_e:
				tool = "eraser"
			elif event.type == pygame.MOUSEBUTTONDOWN:
				if event.button == 1:
					palette_index = (event.pos[1] - 76) // 38
					palette_column = (event.pos[0] - 442) // 38
					if 442 <= event.pos[0] < 646 and 76 <= event.pos[1] < 76 + 4 * 38 and 0 <= palette_index * 6 + palette_column < len(PALETTE):
						selected = PALETTE[palette_index * 6 + palette_column]
					elif ORIGIN[0] <= event.pos[0] < ORIGIN[0] + SIZE * CELL and ORIGIN[1] <= event.pos[1] < ORIGIN[1] + SIZE * CELL:
						x, y = (event.pos[0] - ORIGIN[0]) // CELL, (event.pos[1] - ORIGIN[1]) // CELL
						paint(x, y)
				elif event.button == 3 and ORIGIN[0] <= event.pos[0] < ORIGIN[0] + SIZE * CELL and ORIGIN[1] <= event.pos[1] < ORIGIN[1] + SIZE * CELL:
					x, y = (event.pos[0] - ORIGIN[0]) // CELL, (event.pos[1] - ORIGIN[1]) // CELL
					pixels[y][x] = "#31484b"
			elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
				if ORIGIN[0] <= event.pos[0] < ORIGIN[0] + SIZE * CELL and ORIGIN[1] <= event.pos[1] < ORIGIN[1] + SIZE * CELL:
					x, y = (event.pos[0] - ORIGIN[0]) // CELL, (event.pos[1] - ORIGIN[1]) // CELL
					paint(x, y)

		screen.fill((24, 31, 30))
		screen.blit(font.render(f"TEXTURE 16 x 16  /  {data['name']}", True, (235, 237, 225)), (24, 24))
		for y in range(SIZE):
			for x in range(SIZE):
				rect = pygame.Rect(ORIGIN[0] + x * CELL, ORIGIN[1] + y * CELL, CELL - 1, CELL - 1)
				pygame.draw.rect(screen, pixels[y][x], rect)
		for index, color in enumerate(PALETTE):
			x = 442 + (index % 6) * 34
			y = 76 + (index // 6) * 38
			rect = pygame.Rect(x, y, 28, 28)
			pygame.draw.rect(screen, color, rect)
			if color == selected:
				pygame.draw.rect(screen, (246, 245, 225), rect, 2)
		pygame.draw.rect(screen, selected, (442, 246, 130, 58))
		screen.blit(small.render("Colore attivo", True, (235, 237, 225)), (442, 314))
		pygame.draw.rect(screen, (70, 99, 85), (442, 366, 202, 44), border_radius=4)
		screen.blit(font.render("CTRL+S  SALVA", True, (245, 241, 220)), (454, 378))
		screen.blit(small.render(f"Tool: {tool}", True, (235, 237, 225)), (442, 432))
		screen.blit(small.render("B pennello | F riempi", True, (174, 193, 177)), (442, 458))
		screen.blit(small.render("I contagocce | E gomma", True, (174, 193, 177)), (442, 484))
		screen.blit(small.render("Click destro: gomma | CTRL+S salva", True, (174, 193, 177)), (442, 510))
		pygame.display.flip()
	pygame.quit()
	return 0


if __name__ == "__main__":
	sys.exit(main())
