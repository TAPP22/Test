"""Timeline-style editor for map intro and event cutscenes."""

import sys

import pygame

from maps import load_maps, save_map

WIDTH, HEIGHT = 760, 500


def main():
	map_id = sys.argv[1] if len(sys.argv) > 1 else "atrium"
	pygame.init()
	screen = pygame.display.set_mode((WIDTH, HEIGHT))
	pygame.display.set_caption(f"Cutscene Studio | {map_id}")
	clock = pygame.time.Clock()
	title_font = pygame.font.Font(None, 36)
	font = pygame.font.Font(None, 27)
	small = pygame.font.Font(None, 21)
	maps = load_maps()
	if map_id not in maps:
		pygame.quit()
		return 1
	data = maps[map_id]
	scenes = [dict(scene) for scene in data.get("cutscenes", [])]
	selected = 0
	field = "title"
	preview_until = 0
	message = "Click un campo e scrivi. CTRL+S salva la timeline."
	if not scenes:
		scenes.append({"title": "", "text": "", "duration": 4.0})
	running = True
	while running:
		clock.tick(60)
		scene = scenes[selected]
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False
			elif event.type == pygame.TEXTINPUT:
				scene[field] = (scene.get(field, "") + event.text)[:180 if field == "text" else 48]
			elif event.type == pygame.KEYDOWN:
				if event.key == pygame.K_ESCAPE:
					running = False
				elif event.key == pygame.K_BACKSPACE:
					scene[field] = scene.get(field, "")[:-1]
				elif event.key == pygame.K_TAB:
					field = "text" if field == "title" else "title"
				elif event.key == pygame.K_LEFT:
					selected = max(0, selected - 1)
				elif event.key == pygame.K_RIGHT:
					selected = min(len(scenes) - 1, selected + 1)
				elif event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
					save_map(map_id, {**data, "cutscenes": scenes})
					message = f"Salvato: {len(scenes)} scene"
			elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				if pygame.Rect(28, 132, 700, 48).collidepoint(event.pos):
					field = "title"
				elif pygame.Rect(28, 198, 700, 116).collidepoint(event.pos):
					field = "text"
				elif pygame.Rect(28, 346, 58, 38).collidepoint(event.pos):
					scene["duration"] = max(1.0, float(scene.get("duration", 4)) - 1)
				elif pygame.Rect(94, 346, 58, 38).collidepoint(event.pos):
					scene["duration"] = min(30.0, float(scene.get("duration", 4)) + 1)
				elif pygame.Rect(184, 346, 126, 38).collidepoint(event.pos):
					scenes.append({"title": "Nuova scena", "text": "Descrivi cosa succede...", "duration": 4.0})
					selected = len(scenes) - 1
					field = "title"
				elif pygame.Rect(320, 346, 126, 38).collidepoint(event.pos):
					if len(scenes) > 1:
						scenes.pop(selected)
						selected = min(selected, len(scenes) - 1)
				elif pygame.Rect(456, 346, 126, 38).collidepoint(event.pos):
					preview_until = pygame.time.get_ticks() + int(float(scene.get("duration", 4)) * 1000)
				elif pygame.Rect(592, 346, 136, 38).collidepoint(event.pos):
					save_map(map_id, {**data, "cutscenes": scenes})
					message = f"Salvato: {len(scenes)} scene"

		screen.fill((23, 30, 29))
		screen.blit(title_font.render("CUTSCENE STUDIO", True, (235, 237, 225)), (28, 28))
		screen.blit(small.render(f"{data['name']}  /  Scena {selected + 1} di {len(scenes)}", True, (164, 191, 170)), (30, 78))
		pygame.draw.rect(screen, (43, 54, 50), (28, 132, 700, 48), border_radius=4)
		screen.blit(small.render("TITOLO" + ("  |" if field == "title" else ""), True, (166, 192, 173)), (40, 140))
		screen.blit(font.render(scene.get("title", ""), True, (240, 238, 221)), (40, 155))
		pygame.draw.rect(screen, (43, 54, 50), (28, 198, 700, 116), border_radius=4)
		screen.blit(small.render("TESTO" + ("  |" if field == "text" else ""), True, (166, 192, 173)), (40, 207))
		for line_index, start in enumerate(range(0, len(scene.get("text", "")), 62)):
			screen.blit(small.render(scene["text"][start:start + 62], True, (240, 238, 221)), (40, 236 + line_index * 22))
		for rect, label in (((28, 346, 58, 38), "-1s"), ((94, 346, 58, 38), "+1s"), ((184, 346, 126, 38), "+ SCENA"), ((320, 346, 126, 38), "RIMUOVI"), ((456, 346, 126, 38), "ANTEPRIMA"), ((592, 346, 136, 38), "SALVA")):
			bounds = pygame.Rect(rect)
			pygame.draw.rect(screen, (70, 99, 85) if bounds.collidepoint(pygame.mouse.get_pos()) else (42, 54, 50), bounds, border_radius=4)
			screen.blit(small.render(label, True, (240, 238, 221)), small.render(label, True, (240, 238, 221)).get_rect(center=bounds.center))
		screen.blit(small.render(f"Durata: {float(scene.get('duration', 4)):.0f} secondi  |  Frecce: cambia scena  |  TAB: cambia campo  |  CTRL+S: salva", True, (163, 183, 166)), (28, 414))
		screen.blit(small.render(message, True, (179, 205, 179)), (28, 447))
		if pygame.time.get_ticks() < preview_until:
			pygame.draw.rect(screen, (7, 11, 12), (0, 0, WIDTH, 112))
			pygame.draw.rect(screen, (7, 11, 12), (0, HEIGHT - 112, WIDTH, 112))
			screen.blit(font.render(scene.get("title", ""), True, (240, 238, 221)), (45, 28))
			screen.blit(small.render(scene.get("text", ""), True, (223, 229, 216)), (45, 66))
		pygame.display.flip()
	pygame.quit()
	return 0


if __name__ == "__main__":
	sys.exit(main())
