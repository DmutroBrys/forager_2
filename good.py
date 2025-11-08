import pygame
import sys
import random

pygame.init()

# Розміри екрану
WIDTH, HEIGHT = 600, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Forager-like Game')

# Кольори
LIGHT_BLUE = (135, 206, 250)
GREEN = (34, 139, 34)
RED = (255, 0, 0)
YELLOW = (255, 215, 0)
clock = pygame.time.Clock()

# -------------------------------
# Світ
# -------------------------------
WORLD_WIDTH, WORLD_HEIGHT = 1000, 1000

# -------------------------------
# Клас гравця
# -------------------------------
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 30, 30)
        self.rect.center = (WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
        self.speed = 5

        self.images = {
            "idle": pygame.transform.scale(pygame.image.load("player.png").convert_alpha(), (50, 50)),
            "left": pygame.transform.scale(pygame.image.load("player_left.png").convert_alpha(), (50, 50)),
            "right": pygame.transform.scale(pygame.image.load("player.png").convert_alpha(), (50, 50))
        }

        self.mining_frames = [
            pygame.transform.scale(pygame.image.load(f"player_mine{i}.png").convert_alpha(), (50, 50))
            for i in range(1, 5)
        ]
        self.mining_index = 0
        self.mining_speed = 0.25
        self.is_mining = False

        self.image = self.images["idle"]
        hitbox_size = self.rect.size
        image_size = self.image.get_size()
        self.image_offset = (
            (hitbox_size[0] - image_size[0]) // 2,
            (hitbox_size[1] - image_size[1]) // 2
        )

    def update(self, walls, blocks):
        original_x, original_y = self.rect.x, self.rect.y
        keys = pygame.key.get_pressed()
        moving_x = False

        if self.is_mining:
            self.animate_mining()
            return

        if keys[pygame.K_a]:
            self.rect.x -= self.speed
            self.image = self.images["left"]
            moving_x = True
        if keys[pygame.K_d]:
            self.rect.x += self.speed
            self.image = self.images["right"]
            moving_x = True

        if not moving_x:
            self.image = self.images["idle"]

        for obj in list(walls) + list(blocks):
            if self.rect.colliderect(obj.rect):
                if self.rect.x < original_x:
                    self.rect.left = obj.rect.right
                elif self.rect.x > original_x:
                    self.rect.right = obj.rect.left

        if keys[pygame.K_w]:
            self.rect.y -= self.speed
        if keys[pygame.K_s]:
            self.rect.y += self.speed

        for obj in list(walls) + list(blocks):
            if self.rect.colliderect(obj.rect):
                if self.rect.y < original_y:
                    self.rect.top = obj.rect.bottom
                elif self.rect.y > original_y:
                    self.rect.bottom = obj.rect.top

    def animate_mining(self):
        self.mining_index += self.mining_speed
        if self.mining_index >= len(self.mining_frames):
            self.mining_index = 0
        self.image = self.mining_frames[int(self.mining_index)]

    def draw(self, surface, camera_x, camera_y):
        surface.blit(self.image, (
            self.rect.x - camera_x + self.image_offset[0],
            self.rect.y - camera_y + self.image_offset[1]
        ))


# -------------------------------
# Стіни
# -------------------------------
class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))


# -------------------------------
# Клас блоку (руда / дерево)
# -------------------------------
class ColoredBlock(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path, broken_path=None):
        super().__init__()
        self.image_path = image_path
        self.is_tree = "tree" in image_path
        self.width = 50
        self.height = 100 if self.is_tree else 50

        self.image_normal = pygame.transform.scale(
            pygame.image.load(image_path).convert_alpha(),
            (self.width, self.height)
        )

        if self.is_tree:
            self.rect = pygame.Rect(x, y + 50, 50, 40)
        else:
            self.rect = self.image_normal.get_rect(topleft=(x, y))

        if broken_path:
            try:
                self.image_broken = pygame.transform.scale(
                    pygame.image.load(broken_path).convert_alpha(), (self.width, self.height)
                )
            except FileNotFoundError:
                self.image_broken = self.make_darker(self.image_normal)
        else:
            self.image_broken = self.make_darker(self.image_normal)

        if "coal" in image_path:
            prefix = "coal"
            self.has_animation = True
        elif "gold" in image_path:
            prefix = "gold"
            self.has_animation = True
        elif "iron" in image_path:
            prefix = "iron"
            self.has_animation = True
        elif "tree" in image_path:
            prefix = "tree"
            self.has_animation = True
        else:
            prefix = None
            self.has_animation = False

        if self.has_animation:
            self.frames = [
                pygame.transform.scale(
                    pygame.image.load(f"{prefix}{i}.png").convert_alpha(),
                    (self.width, self.height)
                )
                for i in range(1, 5)
            ]
            self.frame_index = 0
            self.frame_speed = 0.2
            self.animating = False

        self.image = self.image_normal
        self.is_broken = False
        self.destroy_timer = None

    def make_darker(self, image):
        dark = image.copy()
        dark.fill((0, 0, 0, 120), special_flags=pygame.BLEND_RGBA_SUB)
        return dark

    def break_block(self):
        if self.has_animation and not self.is_broken:
            self.animating = True
            self.frame_index = 0
        elif not self.has_animation and not self.is_broken:
            self.image = self.image_broken
            self.is_broken = True
            self.destroy_timer = pygame.time.get_ticks()

    def update(self):
        if self.has_animation and self.animating:
            self.frame_index += self.frame_speed
            if self.frame_index >= len(self.frames):
                self.frame_index = 0
                self.animating = False
                self.is_broken = True
                self.image = self.image_broken
                self.destroy_timer = pygame.time.get_ticks() + 1500
            else:
                self.image = self.frames[int(self.frame_index)]

    def draw(self, surface, camera_x, camera_y):
        if self.is_tree:
            surface.blit(self.image, (self.rect.x - camera_x, self.rect.y - camera_y - 50))
        else:
            surface.blit(self.image, (self.rect.x - camera_x, self.rect.y - camera_y))


# -------------------------------
# Створення стін
# -------------------------------
walls = pygame.sprite.Group()
wall_width = 10
frame_margin = 10
walls.add(
    Wall(frame_margin, frame_margin, WORLD_WIDTH - 2 * frame_margin, wall_width, RED),
    Wall(frame_margin, WORLD_HEIGHT - frame_margin - wall_width, WORLD_WIDTH - 2 * frame_margin, wall_width, RED),
    Wall(frame_margin, frame_margin, wall_width, WORLD_HEIGHT - 2 * frame_margin, RED),
    Wall(WORLD_WIDTH - frame_margin - wall_width, frame_margin, wall_width, WORLD_HEIGHT - 2 * frame_margin, RED),
    Wall(333, 333, 333, 10, LIGHT_BLUE),
    Wall(333, 666, 333, 10, YELLOW),
    Wall(333, 333, 10, 343, LIGHT_BLUE),
    Wall(666, 343, 10, 333, YELLOW)
)

# -------------------------------
# Групи спрайтів
# -------------------------------
colored_blocks = pygame.sprite.Group()
player = Player()
all_sprites = pygame.sprite.Group(walls, player)

# Камера
camera_x, camera_y = 0, 0

# Межі для спавну блоків
inner_x_min = 333 + 20
inner_y_min = 333 + 20
inner_x_max = 666 - 70
inner_y_max = 666 - 70

# -------------------------------
# Функції
# -------------------------------
def spawn_block():
    if random.choice([True, False]):
        ores = [
            ("iron.png", "iron_broken.png"),
            ("gold.png", "gold_broken.png"),
            ("coal.png", "coal_broken.png"),
        ]
        image_path, broken_path = random.choice(ores)
    else:
        image_path, broken_path = ("tree.png", "tree_broken.png")

    for _ in range(8):
        x = random.randint(inner_x_min, inner_x_max)
        y = random.randint(inner_y_min, inner_y_max)
        new_block = ColoredBlock(x, y, image_path, broken_path)
        overlap = (
            any(new_block.rect.colliderect(b.rect) for b in colored_blocks)
            or new_block.rect.colliderect(player.rect)
        )
        if not overlap:
            colored_blocks.add(new_block)
            all_sprites.add(new_block)
            break


def draw_progress_bar(surface, x, y, width, height, progress, color=(0, 255, 0)):
    pygame.draw.rect(surface, (50, 50, 50), (x, y, width, height))
    pygame.draw.rect(surface, color, (x, y, width * progress, height))
    pygame.draw.rect(surface, (0, 0, 0), (x, y, width, height), 2)


def draw_pause_menu(surface):
    surface.fill((0, 0, 0))
    font = pygame.font.Font(None, 50)
    title = font.render("ПАУЗА", True, (255, 255, 255))
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))

    button_font = pygame.font.Font(None, 40)
    buttons = [
        ("Продовжити", (WIDTH // 2 - 100, 250, 200, 50)),
        ("Меню", (WIDTH // 2 - 100, 320, 200, 50)),
        ("Вийти", (WIDTH // 2 - 100, 390, 200, 50))
    ]

    mouse_pos = pygame.mouse.get_pos()
    clicked = pygame.mouse.get_pressed()[0]
    result = None

    for text, rect in buttons:
        color = (200, 200, 200)
        if pygame.Rect(rect).collidepoint(mouse_pos):
            color = (255, 255, 0)
            if clicked:
                result = text
        pygame.draw.rect(surface, color, rect, border_radius=10)
        txt = button_font.render(text, True, (0, 0, 0))
        surface.blit(txt, (rect[0] + 30, rect[1] + 10))

    return result


def draw_menu(surface):
    surface.fill((0, 0, 0))
    font = pygame.font.Font(None, 50)
    title = font.render("MENU", True, (255, 255, 255))
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))

    button_font = pygame.font.Font(None, 40)
    buttons = [
        ("Почати гру", (WIDTH // 2 - 100, 250, 200, 50)),
        ("Вийти", (WIDTH // 2 - 100, 320, 200, 50))
    ]

    mouse_pos = pygame.mouse.get_pos()
    clicked = pygame.mouse.get_pressed()[0]
    result = None

    for text, rect in buttons:
        color = (200, 200, 200)
        if pygame.Rect(rect).collidepoint(mouse_pos):
            color = (255, 255, 0)
            if clicked:
                result = text
        pygame.draw.rect(surface, color, rect, border_radius=10)
        txt = button_font.render(text, True, (0, 0, 0))
        surface.blit(txt, (rect[0] + 30, rect[1] + 10))

    return result


# -------------------------------
# Основний цикл гри
# -------------------------------
SPAWN_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(SPAWN_EVENT, 6000)

paused = False
in_menu = True
mining_start_time = None
mining_target = None
MINING_DURATION = 3000

xp_progress = 0.0
xp_value = 0
xp_per_block = 0.5
a = 10
lvl = 0
first_lvl = second_lvl = third_lvl = fourth_lvl = fifth_lvl = True

def reset_game_state():
    global colored_blocks, all_sprites, xp_progress, xp_value, lvl, mining_target
    # видаляємо всі блоки зі спрайтів
    all_sprites.remove(*colored_blocks)
    colored_blocks.empty()
    # додаємо гравця і стіни
    all_sprites = pygame.sprite.Group()
    all_sprites.add(player)
    all_sprites.add(*walls)
    # скидаємо прогрес
    xp_progress = 0
    xp_value = 0
    lvl = 0
    # скидаємо стан гравця
    player.is_mining = False
    mining_target = None

# -------------------------------
# Основний цикл гри
# -------------------------------
SPAWN_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(SPAWN_EVENT, 6000)

paused = False
in_menu = True
mining_start_time = None
mining_target = None
MINING_DURATION = 3000

xp_progress = 0.0
xp_value = 0
xp_per_block = 0.5
a = 10
lvl = 0
first_lvl = second_lvl = third_lvl = fourth_lvl = fifth_lvl = True

while True:
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            paused = not paused
        elif event.type == SPAWN_EVENT and not paused and not in_menu:
            spawn_block()
        elif not paused and not in_menu:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for block in colored_blocks:
                    if block and player.rect.colliderect(block.rect.inflate(20, 20)):
                        mining_start_time = pygame.time.get_ticks()
                        mining_target = block
                        player.is_mining = True
                        break
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                player.is_mining = False
                mining_start_time = None
                mining_target = None

    # --- Меню ---
    if in_menu:
        mining_target = None
        player.is_mining = False
        result = draw_menu(screen)
        if result == "Почати гру":
            in_menu = False
            reset_game_state()
        elif result == "Вийти":
            pygame.quit()
            sys.exit()
        pygame.display.flip()
        clock.tick(60)
        continue

    # --- Пауза ---
    if paused:
        result = draw_pause_menu(screen)
        if result == "Продовжити":
            paused = False
        elif result == "Меню":
            in_menu = True
            paused = False
            reset_game_state()
        elif result == "Вийти":
            pygame.quit()
            sys.exit()
        pygame.display.flip()
        clock.tick(60)
        continue

    # --- Гра --- логіка ---
    player.update(walls, colored_blocks)

    if mining_target and player.is_mining:
        elapsed = pygame.time.get_ticks() - mining_start_time
        if elapsed >= MINING_DURATION:
            mining_target.break_block()
            player.is_mining = False
            mining_target = None
            progress = 0
            xp_value += 5
            xp_progress += xp_per_block
            if xp_progress > 1:
                xp_progress = 0
        else:
            progress = elapsed / MINING_DURATION
    else:
        progress = 0

    for block in list(colored_blocks):
        block.update()
        if block.is_broken and block.destroy_timer and pygame.time.get_ticks() >= block.destroy_timer:
            colored_blocks.remove(block)
            all_sprites.remove(block)

    # Камера
    camera_x = player.rect.centerx - WIDTH // 2
    camera_y = player.rect.centery - HEIGHT // 2
    camera_x = max(0, min(camera_x, WORLD_WIDTH - WIDTH))
    camera_y = max(0, min(camera_y, WORLD_HEIGHT - HEIGHT))

    # --- Рендер гри ---
    screen.fill(LIGHT_BLUE)
    pygame.draw.rect(screen, GREEN, (333 - camera_x, 333 - camera_y, 333, 333))

    for sprite in all_sprites:
        if isinstance(sprite, Player):
            sprite.draw(screen, camera_x, camera_y)
        elif isinstance(sprite, ColoredBlock):
            sprite.draw(screen, camera_x, camera_y)
        else:
            screen.blit(sprite.image, (sprite.rect.x - camera_x, sprite.rect.y - camera_y))

    if player.is_mining and progress > 0:
        draw_progress_bar(screen, WIDTH // 2 - 100, 50, 200, 20, progress, (0, 255, 0))

    draw_progress_bar(screen, 150, 20, 300, 20, xp_progress, (0, 128, 255))

    font = pygame.font.Font(None, 30)
    xp_text = font.render(f"XP: {xp_value} / {a}", True, (0, 0, 0))
    lvl_render = font.render(f'LVL:{lvl}', True, (0, 0, 0))
    screen.blit(xp_text, (460, 18))
    screen.blit(lvl_render, (60, 18))

    pygame.display.flip()
    clock.tick(60)