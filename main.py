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

        # Звичайні зображення
        self.images = {
            "idle": pygame.transform.scale(pygame.image.load("player.png").convert_alpha(), (50, 50)),
            "left": pygame.transform.scale(pygame.image.load("player_left.png").convert_alpha(), (50, 50)),
            "right": pygame.transform.scale(pygame.image.load("player.png").convert_alpha(), (50, 50))
        }

        # Анімація копання
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

        # Якщо копає — не рухається
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
# Клас блоку (руда)
# -------------------------------
class ColoredBlock(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path, broken_path=None):
        super().__init__()
        self.image_path = image_path
        self.image_normal = pygame.transform.scale(pygame.image.load(image_path).convert_alpha(), (50, 50))
        self.rect = self.image_normal.get_rect(topleft=(x, y))

        # Якщо немає broken-текстури — створюємо затемнену копію
        if broken_path:
            try:
                self.image_broken = pygame.transform.scale(
                    pygame.image.load(broken_path).convert_alpha(), (50, 50)
                )
            except FileNotFoundError:
                self.image_broken = self.make_darker(self.image_normal)
        else:
            self.image_broken = self.make_darker(self.image_normal)

        # Анімація тільки для золота та вугілля
        if "coal" in image_path:
            prefix = "coal"
            self.has_animation = True
        elif "gold" in image_path:
            prefix = "gold"
            self.has_animation = True
        else:
            prefix = None
            self.has_animation = False

        # Якщо є анімація — завантажуємо кадри
        if self.has_animation:
            self.frames = [
                pygame.transform.scale(pygame.image.load(f"{prefix}{i}.png").convert_alpha(), (50, 50))
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
        """Змінює текстуру або запускає анімацію для золота/вугілля"""
        if self.has_animation and not self.is_broken:
            self.animating = True
            self.frame_index = 0
        elif not self.has_animation and not self.is_broken:
            self.image = self.image_broken
            self.is_broken = True
            self.destroy_timer = pygame.time.get_ticks()

    def update(self):
        """Оновлення анімації (для золота та вугілля)"""
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
# Функція спавну руди
# -------------------------------
def spawn_block():
    ores = [
        ("iron.png", "iron_broken.png"),
        ("gold.png", "gold_broken.png"),
        ("coal.png", "coal_broken.png"),
    ]
    image_path, broken_path = random.choice(ores)
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


# -------------------------------
# Основний цикл гри
# -------------------------------
SPAWN_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(SPAWN_EVENT, 2500)

mining_start_time = None
mining_target = None
MINING_DURATION = 3000

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == SPAWN_EVENT:
            spawn_block()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for block in colored_blocks:
                if player.rect.colliderect(block.rect.inflate(20, 20)):
                    mining_start_time = pygame.time.get_ticks()
                    mining_target = block
                    player.is_mining = True
                    break
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            player.is_mining = False
            mining_start_time = None
            mining_target = None

    # Оновлення
    player.update(walls, colored_blocks)

    # Копання
    if mining_target and player.is_mining:
        elapsed = pygame.time.get_ticks() - mining_start_time
        if elapsed >= MINING_DURATION:
            mining_target.break_block()
            player.is_mining = False
            mining_target = None

    # Оновлення руд
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

    # Малювання
    screen.fill(LIGHT_BLUE)
    pygame.draw.rect(screen, GREEN, (333 - camera_x, 333 - camera_y, 333, 333))

    for sprite in all_sprites:
        if isinstance(sprite, Player):
            sprite.draw(screen, camera_x, camera_y)
        else:
            screen.blit(sprite.image, (sprite.rect.x - camera_x, sprite.rect.y - camera_y))

    pygame.display.flip()
    clock.tick(60)
