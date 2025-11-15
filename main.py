import pygame
import sys
import random
import os
import math

# -------------------------------
# Ініціалізація
# -------------------------------
pygame.init()

# -------------------------------
# Константи
# -------------------------------
WIDTH, HEIGHT = 600, 600
WORLD_WIDTH, WORLD_HEIGHT = 1000, 1000
LIGHT_BLUE = (135, 206, 250)
GREEN = (34, 139, 34)
RED = (255, 0, 0)
YELLOW = (255, 215, 0)
FPS = 60

# -------------------------------
# Вікно і годинник
# -------------------------------
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Forager-like Game')
clock = pygame.time.Clock()

# -------------------------------
# Шрифти
# -------------------------------
font_big = pygame.font.Font(None, 50)
font_med = pygame.font.Font(None, 40)
font_small = pygame.font.Font(None, 30)

# -------------------------------
# Допоміжні функції для безпечного завантаження
# -------------------------------
def safe_load_image(path, size=None, fill_color=(255, 0, 255)):
    """Повертає Surface: якщо файл існує — завантажує, інакше створює підкладку."""
    if path and os.path.exists(path):
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    else:
        size = size or (32, 32)
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill(fill_color)
        return surf

def draw_progress_bar(surface, x, y, width, height, progress, color=(0, 255, 0)):
    pygame.draw.rect(surface, (50, 50, 50), (x, y, width, height))
    inner_w = max(0, min(width * progress, width))
    pygame.draw.rect(surface, color, (x, y, inner_w, height))
    pygame.draw.rect(surface, (0, 0, 0), (x, y, width, height), 2)

# -------------------------------
# Передзавантаження поширених зображень (резерв)
# -------------------------------
# Маленькі іконки (праворуч)
b_image = safe_load_image("hurd.png", (40, 40), fill_color=(200, 50, 50))
a_image = safe_load_image("hungry.png", (30, 30), fill_color=(200, 200, 50))

# Функція підвантаження анімаційних фреймів (якщо існують)
def load_animation(prefix, count, size):
    frames = []
    for i in range(1, count + 1):
        path = f"{prefix}{i}.png"
        frames.append(safe_load_image(path, size))
    return frames

# -------------------------------
# Класи
# -------------------------------
class Player(pygame.sprite.Sprite):
    def __init__(self, x=None, y=None):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 30, 30)
        self.rect.center = ((x if x is not None else WORLD_WIDTH // 2),
                            (y if y is not None else WORLD_HEIGHT // 2))
        self.speed = 5

        # картинки (без падіння якщо немає файлів)
        self.images = {
            "idle": safe_load_image("player.png", (50, 50), (100, 100, 255)),
            "left": safe_load_image("player_left.png", (50, 50), (120, 100, 255)),
            "right": safe_load_image("player.png", (50, 50), (100, 100, 255))
        }

        # mining frames (можуть бути відсутні)
        self.mining_frames = load_animation("player_mine", 4, (50, 50))
        if not any(frame for frame in self.mining_frames):
            # якщо немає рамок — ставимо idle як єдиний кадр
            self.mining_frames = [self.images["idle"]]

        self.mining_index = 0.0
        self.mining_speed = 0.25
        self.is_mining = False

        self.image = self.images["idle"]
        hitbox_size = self.rect.size
        image_size = self.image.get_size()
        self.image_offset = ((hitbox_size[0] - image_size[0]) // 2,
                             (hitbox_size[1] - image_size[1]) // 2)

    def update(self, walls_group, blocks_group):
        # зчитуємо клавіші і рухаємось; якщо копає — анімація тільки
        original_x, original_y = self.rect.x, self.rect.y
        keys = pygame.key.get_pressed()

        if self.is_mining:
            self.animate_mining()
            return

        moving_x = False
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

        # перевірка горизонтальних колізій — оптимізовано: ітеруємо групи
        for obj in walls_group:
            if self.rect.colliderect(obj.rect):
                if self.rect.x < original_x:
                    self.rect.left = obj.rect.right
                elif self.rect.x > original_x:
                    self.rect.right = obj.rect.left
        for obj in blocks_group:
            if self.rect.colliderect(obj.rect):
                if self.rect.x < original_x:
                    self.rect.left = obj.rect.right
                elif self.rect.x > original_x:
                    self.rect.right = obj.rect.left

        # вертикальний рух
        if keys[pygame.K_w]:
            self.rect.y -= self.speed
        if keys[pygame.K_s]:
            self.rect.y += self.speed

        for obj in walls_group:
            if self.rect.colliderect(obj.rect):
                if self.rect.y < original_y:
                    self.rect.top = obj.rect.bottom
                elif self.rect.y > original_y:
                    self.rect.bottom = obj.rect.top
        for obj in blocks_group:
            if self.rect.colliderect(obj.rect):
                if self.rect.y < original_y:
                    self.rect.top = obj.rect.bottom
                elif self.rect.y > original_y:
                    self.rect.bottom = obj.rect.top

    def animate_mining(self):
        self.mining_index += self.mining_speed
        if self.mining_index >= len(self.mining_frames):
            self.mining_index = 0.0
        self.image = self.mining_frames[int(self.mining_index)]

    def draw(self, surface, camera_x, camera_y):
        surface.blit(self.image, (self.rect.x - camera_x + self.image_offset[0],
                                  self.rect.y - camera_y + self.image_offset[1]))


class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))


class ColoredBlock(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path, broken_path=None):
        super().__init__()
        self.image_path = image_path
        self.is_tree = "tree" in (image_path or "")
        self.width = 50
        self.height = 100 if self.is_tree else 50

        # нормальний вигляд
        self.image_normal = safe_load_image(image_path, (self.width, self.height))
        # прямокутна хитбокс для дерев (створюємо невелику хитбокс-частину)
        if self.is_tree:
            self.rect = pygame.Rect(x, y + 50, 50, 40)
        else:
            self.rect = self.image_normal.get_rect(topleft=(x, y))

        # зламаний вигляд (або темніший/вицвівший)
        if broken_path:
            self.image_broken = safe_load_image(broken_path, (self.width, self.height))
        else:
            self.image_broken = self.make_faded(self.image_normal)

        # Анімація для певних префіксів
        prefixes = ["coal", "gold", "iron", "tree"]
        found_prefix = None
        for p in prefixes:
            if p in (image_path or ""):
                found_prefix = p
                break

        self.has_animation = bool(found_prefix)
        self.frames = []
        if self.has_animation:
            self.frames = load_animation(found_prefix, 4, (self.width, self.height))
            if not any(self.frames):
                self.has_animation = False

        self.frame_index = 0.0
        self.frame_speed = 0.2
        self.animating = False

        self.image = self.image_normal
        self.is_broken = False
        # destroy_timer залишив як None — після поломки блок лишається вицвілим
        self.destroy_timer = None

    def make_darker(self, image):
        dark = image.copy()
        dark.fill((0, 0, 0, 120), special_flags=pygame.BLEND_RGBA_SUB)
        return dark

    def make_faded(self, image):
        """Повертає менш яскраву/вицвілу версію (зниження насиченості/яскравості)."""
        faded = image.copy()
        # помножимо RGB на 0.6 (BLEND_RGBA_MULT з (153,153,153,255) ~ 0.6)
        faded.fill((153, 153, 153, 255), special_flags=pygame.BLEND_RGBA_MULT)
        # додатково зробимо трохи прозорішим (але лишимо видимим)
        try:
            faded.set_alpha(230)
        except Exception:
            pass
        return faded

    def break_block(self):
        if self.is_broken:
            return
        if self.has_animation:
            self.animating = True
            self.frame_index = 0.0
        else:
            # Невід’ємна зміна — просто ставимо вицвілу картинку і не видаляємо
            self.image = self.image_broken
            self.is_broken = True
            self.destroy_timer = None  # залишаємо блок, але вицвілим

    def update(self):
        if self.has_animation and self.animating:
            self.frame_index += self.frame_speed
            if self.frame_index >= len(self.frames):
                # закінчилась анімація — показати вицвілу картинку та позначити зламаним
                self.frame_index = 0.0
                self.animating = False
                self.is_broken = True
                # якщо є окремий broken image — використаємо його, інакше зробимо вицвілу копію
                self.image = self.image_broken if self.image_broken else self.make_faded(self.frames[-1])
                self.destroy_timer = None
            else:
                self.image = self.frames[int(self.frame_index)]

    def draw(self, surface, camera_x, camera_y):
        if self.is_tree:
            surface.blit(self.image, (self.rect.x - camera_x, self.rect.y - camera_y - 50))
        else:
            surface.blit(self.image, (self.rect.x - camera_x, self.rect.y - camera_y))


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((30, 30))
        self.image.fill(RED)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.speed = 2.0

    def update(self, player, walls_group, blocks_group):
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            dx /= dist
            dy /= dist

        new_rect = self.rect.move(dx * self.speed, dy * self.speed)

        # перевіряємо колізії з перешкодами
        collided = False
        for o in walls_group:
            if new_rect.colliderect(o.rect):
                collided = True
                break
        if not collided:
            for b in blocks_group:
                if new_rect.colliderect(b.rect):
                    collided = True
                    break

        if not collided:
            self.rect = new_rect
        else:
            # спроба оточного обходу
            side_rect = self.rect.move(-dy * self.speed, dx * self.speed)
            blocked = any(side_rect.colliderect(o.rect) for o in walls_group) or any(side_rect.colliderect(b.rect) for b in blocks_group)
            if not blocked:
                self.rect = side_rect

# -------------------------------
# Створення стін і груп
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

colored_blocks = pygame.sprite.Group()
enemies = pygame.sprite.Group()
all_sprites = pygame.sprite.Group()
player = Player()
all_sprites.add(player)
for w in walls:
    all_sprites.add(w)

# межі для спавну (взято з обох частин, узгоджено)
inner_x_min, inner_y_min = 353, 353
inner_x_max, inner_y_max = 596, 596

# -------------------------------
# Функції спавну (оптимізовано)
# -------------------------------
def spawn_block(attempts=8):
    """Спроба створити блок в межах inner_x.., уникаючи колізій."""
    if random.choice([True, False]):
        ores = [("iron.png", "iron_broken.png"), ("gold.png", "gold_broken.png"), ("coal.png", "coal_broken.png")]
        image_path, broken_path = random.choice(ores)
    else:
        image_path, broken_path = ("tree.png", "tree_broken.png")

    for _ in range(attempts):
        x = random.randint(inner_x_min, inner_x_max)
        y = random.randint(inner_y_min, inner_y_max)
        new_block = ColoredBlock(x, y, image_path, broken_path)
        overlap = any(new_block.rect.colliderect(b.rect) for b in colored_blocks) or new_block.rect.colliderect(player.rect)
        if not overlap:
            colored_blocks.add(new_block)
            all_sprites.add(new_block)
            return True
    return False

def spawn_enemy(attempts=20):
    for _ in range(attempts):
        x = random.randint(inner_x_min, inner_x_max - 30)
        y = random.randint(inner_y_min, inner_y_max - 30)
        enemy_rect = pygame.Rect(x, y, 30, 30)
        if not any(enemy_rect.colliderect(e.rect) for e in enemies) and not any(enemy_rect.colliderect(b.rect) for b in colored_blocks):
            enemy = Enemy(x, y)
            enemies.add(enemy)
            all_sprites.add(enemy)
            return True
    return False

# -------------------------------
# Меню та пауза (витяговані функції)
# -------------------------------
def draw_buttons(surface, buttons, title_text=None):
    """Універсальна функція для меню — повертає текст натиснутої кнопки або None."""
    surface.fill((0, 0, 0))
    if title_text:
        title = font_big.render(title_text, True, (255, 255, 255))
        surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))

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
        surface.blit(font_med.render(text, True, (0, 0, 0)), (rect[0] + 30, rect[1] + 10))
    return result

def draw_menu(surface):
    buttons = [("Почати гру", (WIDTH // 2 - 100, 250, 200, 50)), ("Вийти", (WIDTH // 2 - 100, 320, 200, 50))]
    return draw_buttons(surface, buttons, "MENU")

def draw_pause_menu(surface):
    buttons = [
        ("Продовжити", (WIDTH // 2 - 100, 250, 200, 50)),
        ("Меню", (WIDTH // 2 - 100, 320, 200, 50)),
        ("Вийти", (WIDTH // 2 - 100, 390, 200, 50))
    ]
    return draw_buttons(surface, buttons, "ПАУЗА")

# -------------------------------
# Стан гри і таймери
# -------------------------------
SPAWN_EVENT = pygame.USEREVENT + 1
ENEMY_SPAWN = pygame.USEREVENT + 2
pygame.time.set_timer(SPAWN_EVENT, 6000)
pygame.time.set_timer(ENEMY_SPAWN, 8000)

paused = False
in_menu = True
mining_target = None
mining_start_time = None
MINING_DURATION = 3000  # мс

# -------------------------------
# XP / Level / HP система
# -------------------------------
xp = 0                # поточний XP
level = 1             # стартовий рівень
xp_needed = 10        # скільки потрібно для LEVEL UP (зростає)
hp_max = 3
hp = hp_max

# -------------------------------
# Скидання стану гри
# -------------------------------
def reset_game_state():
    global colored_blocks, enemies, all_sprites, xp, level, xp_needed, mining_target, hp
    # Забираємо блоки та ворогів із груп і all_sprites
    for b in list(colored_blocks):
        all_sprites.remove(b)
    colored_blocks.empty()

    for e in list(enemies):
        all_sprites.remove(e)
    enemies.empty()

    # Переконаємось, що гравець та стіни в групі
    all_sprites.empty()
    all_sprites.add(player)
    for w in walls:
        all_sprites.add(w)

    xp = 0
    level = 1
    xp_needed = 10
    mining_target = None
    player.is_mining = False
    hp = hp_max
    # центр гравця
    player.rect.center = (WORLD_WIDTH // 2, WORLD_HEIGHT // 2)

# -------------------------------
# Основний цикл
# -------------------------------
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
        elif event.type == ENEMY_SPAWN and not paused and not in_menu:
            spawn_enemy()
        elif not paused and not in_menu:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Клацання — початок майнінгу якщо гравець поруч з блоком
                for block in colored_blocks:
                    # inflate дає невеликий радіус взаємодії
                    if player.rect.colliderect(block.rect.inflate(20, 20)):
                        mining_start_time = pygame.time.get_ticks()
                        mining_target = block
                        player.is_mining = True
                        break
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                # скидаємо майнінг при відпусканні
                player.is_mining = False
                mining_target = None
                mining_start_time = None

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
        clock.tick(FPS)
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
        clock.tick(FPS)
        continue

    # --- Логіка гри ---
    player.update(walls, colored_blocks)

    # Оновлюємо ворогів
    for enemy in enemies:
        enemy.update(player, walls, colored_blocks)

    # Обробка майнінгу
    progress = 0.0
    if mining_target and player.is_mining:
        # захист: якщо блок вже був видалений
        if mining_target not in colored_blocks:
            player.is_mining = False
            mining_target = None
            mining_start_time = None
        else:
            elapsed = pygame.time.get_ticks() - mining_start_time
            if elapsed >= MINING_DURATION:
                # розбили блок
                mining_target.break_block()
                player.is_mining = False
                mining_target = None
                mining_start_time = None

                # Додаємо XP (ціла кількість)
                xp += 5

                # Level up — може бути одразу кілька рівнів, якщо XP велике
                while xp >= xp_needed:
                    xp -= xp_needed
                    level += 1
                    xp_needed += 10  # кожен рівень дорожчий на 10 XP

            else:
                progress = elapsed / MINING_DURATION

    # Оновлення блоків (анімовані та таймери знищення)
    for block in list(colored_blocks):
        block.update()
        # тут ми не видаляємо вцілілі зламані блоки — вони лишаються вицвілими
        if block.is_broken and block.destroy_timer and pygame.time.get_ticks() >= block.destroy_timer:
            colored_blocks.remove(block)
            if block in all_sprites:
                all_sprites.remove(block)

    # Камера (обмежена світом)
    camera_x = player.rect.centerx - WIDTH // 2
    camera_y = player.rect.centery - HEIGHT // 2
    camera_x = max(0, min(camera_x, WORLD_WIDTH - WIDTH))
    camera_y = max(0, min(camera_y, WORLD_HEIGHT - HEIGHT))

    # --- Рендер ---
    screen.fill(LIGHT_BLUE)
    # зелена зона
    pygame.draw.rect(screen, GREEN, (333 - camera_x, 333 - camera_y, 333, 333))

    # Малюємо інші спрайти: стіни, блоки, вороги, гравець
    # Використовуємо all_sprites для ефективності; але деякі спрайти (ColoredBlock) мають власний draw
    for sprite in all_sprites:
        # Player має свій draw з оффсетом
        if isinstance(sprite, Player):
            sprite.draw(screen, camera_x, camera_y)
        elif isinstance(sprite, ColoredBlock):
            sprite.draw(screen, camera_x, camera_y)
        else:
            screen.blit(sprite.image, (sprite.rect.x - camera_x, sprite.rect.y - camera_y))

    # Вороги, які могли не бути в all_sprites (переконуємось намалювати)
    for e in enemies:
        screen.blit(e.image, (e.rect.x - camera_x, e.rect.y - camera_y))

    # HUD: порядок зліва направо — LEVEL -> XP BAR -> HP
    # Рівень (ліворуч)
    level_text = font_small.render(f"LVL: {level}", True, (0, 0, 0))
    screen.blit(level_text, (10, 15))

    # XP бар (трохи правіше)
    xp_progress = xp / xp_needed if xp_needed > 0 else 0.0
    draw_progress_bar(screen, 90, 18, 220, 18, xp_progress, (0, 128, 255))
    xp_text = font_small.render(f"{int(xp)}/{int(xp_needed)} XP", True, (0, 0, 0))
    screen.blit(xp_text, (320, 15))

    # HP (серця) — правіше від шкали XP
    hearts_text = "♥" * hp + " " * (hp_max - hp)
    hearts_render = font_small.render(hearts_text, True, (200, 0, 0))
    screen.blit(hearts_render, (420, 15))

    # Праві іконки (не чіпаємо)
    screen.blit(a_image, (565, 10))
    screen.blit(a_image, (565, 50))
    screen.blit(a_image, (565, 90))
    screen.blit(a_image, (535, 10))
    screen.blit(a_image, (535, 50))
    screen.blit(a_image, (535, 90))

    # Майнінг прогрес бар (по центру)
    if player.is_mining and progress > 0:
        draw_progress_bar(screen, WIDTH // 2 - 100, 50, 200, 20, progress, (0, 255, 0))

    pygame.display.flip()
    clock.tick(FPS)
