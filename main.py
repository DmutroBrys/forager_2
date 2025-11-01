import pygame
import sys
import random
import os
import math

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
# Екран і годинник
# -------------------------------
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Forager-like Game')
clock = pygame.time.Clock()

# -------------------------------
# Шрифти та зображення (один раз)
# -------------------------------
font_big = pygame.font.Font(None, 50)
font_med = pygame.font.Font(None, 40)
font_small = pygame.font.Font(None, 30)

b_image = pygame.transform.scale(pygame.image.load("hurd.png").convert_alpha(), (40, 40)) if os.path.exists("hurd.png") else pygame.Surface((40,40))
b_image.fill((255,0,0))
a_image = pygame.transform.scale(pygame.image.load("hungry.png").convert_alpha(), (30,30)) if os.path.exists("hungry.png") else pygame.Surface((30,30))
a_image.fill((255,255,0))

# -------------------------------
# Допоміжні функції
# -------------------------------
def load_image(path, size):
    if os.path.exists(path):
        return pygame.transform.scale(pygame.image.load(path).convert_alpha(), size)
    else:
        surf = pygame.Surface(size)
        surf.fill((255, 0, 255))
        return surf

def draw_progress_bar(surface, x, y, width, height, progress, color=(0, 255, 0)):
    pygame.draw.rect(surface, (50, 50, 50), (x, y, width, height))
    pygame.draw.rect(surface, color, (x, y, width * progress, height))
    pygame.draw.rect(surface, (0, 0, 0), (x, y, width, height), 2)

# -------------------------------
# Класи
# -------------------------------
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.rect = pygame.Rect(0, 0, 30, 30)
        self.rect.center = (WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
        self.speed = 5
        self.images = {
            "idle": load_image("player.png", (50, 50)),
            "left": load_image("player_left.png", (50, 50)),
            "right": load_image("player.png", (50, 50))
        }
        self.mining_frames = [load_image(f"player_mine{i}.png", (50, 50)) for i in range(1, 5)]
        self.mining_index = 0
        self.mining_speed = 0.25
        self.is_mining = False
        self.image = self.images["idle"]
        hitbox_size = self.rect.size
        image_size = self.image.get_size()
        self.image_offset = ((hitbox_size[0]-image_size[0])//2, (hitbox_size[1]-image_size[1])//2)

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
        for obj in list(walls)+list(blocks):
            if self.rect.colliderect(obj.rect):
                if self.rect.x < original_x:
                    self.rect.left = obj.rect.right
                elif self.rect.x > original_x:
                    self.rect.right = obj.rect.left
        if keys[pygame.K_w]:
            self.rect.y -= self.speed
        if keys[pygame.K_s]:
            self.rect.y += self.speed
        for obj in list(walls)+list(blocks):
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
        surface.blit(self.image, (self.rect.x - camera_x + self.image_offset[0], self.rect.y - camera_y + self.image_offset[1]))

class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color):
        super().__init__()
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))

class ColoredBlock(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path, broken_path=None):
        super().__init__()
        self.is_tree = "tree" in image_path
        self.width = 50
        self.height = 100 if self.is_tree else 50
        self.image_normal = load_image(image_path, (self.width, self.height))
        self.rect = pygame.Rect(x, y + 50, 50, 40) if self.is_tree else self.image_normal.get_rect(topleft=(x, y))
        self.image_broken = load_image(broken_path, (self.width, self.height)) if broken_path else self.make_darker(self.image_normal)
        self.has_animation = any(name in image_path for name in ["coal","gold","iron","tree"])
        if self.has_animation:
            prefix = [name for name in ["coal","gold","iron","tree"] if name in image_path][0]
            self.frames = [load_image(f"{prefix}{i}.png",(self.width,self.height)) for i in range(1,5)]
            self.frame_index = 0
            self.frame_speed = 0.2
            self.animating = False
        self.image = self.image_normal
        self.is_broken = False
        self.destroy_timer = None

    def make_darker(self, image):
        dark = image.copy()
        dark.fill((0,0,0,120), special_flags=pygame.BLEND_RGBA_SUB)
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
                self.destroy_timer = pygame.time.get_ticks()+1500
            else:
                self.image = self.frames[int(self.frame_index)]

    def draw(self, surface, camera_x, camera_y):
        if self.is_tree:
            surface.blit(self.image, (self.rect.x-camera_x, self.rect.y-camera_y-50))
        else:
            surface.blit(self.image, (self.rect.x-camera_x, self.rect.y-camera_y))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((30, 30))
        self.image.fill(RED)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.speed = 2

    def update(self, player, walls, blocks):
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist > 0:
            dx /= dist
            dy /= dist
        new_rect = self.rect.move(dx * self.speed, dy * self.speed)
        collided = False
        for obj in list(walls)+list(blocks):
            if new_rect.colliderect(obj.rect):
                collided = True
                break
        if not collided:
            self.rect = new_rect
        else:
            side_rect = self.rect.move(-dy * self.speed, dx * self.speed)
            if not any(side_rect.colliderect(o.rect) for o in list(walls)+list(blocks)):
                self.rect = side_rect

# -------------------------------
# Створення стін і спрайтів
# -------------------------------
walls = pygame.sprite.Group(
    Wall(10,10,WORLD_WIDTH-20,10,RED),
    Wall(10,WORLD_HEIGHT-20,WORLD_WIDTH-20,10,RED),
    Wall(10,10,10,WORLD_HEIGHT-20,RED),
    Wall(WORLD_WIDTH-20,10,10,WORLD_HEIGHT-20,RED),
    Wall(333,333,333,10,LIGHT_BLUE),
    Wall(333,666,333,10,YELLOW),
    Wall(333,333,10,343,LIGHT_BLUE),
    Wall(666,343,10,333,YELLOW)
)
colored_blocks = pygame.sprite.Group()
enemies = pygame.sprite.Group()
player = Player()

inner_x_min, inner_y_min = 353, 353
inner_x_max, inner_y_max = 596, 596

# -------------------------------
# Функції спавну
# -------------------------------
def spawn_block():
    if random.choice([True, False]):
        ores = [("iron.png","iron_broken.png"),("gold.png","gold_broken.png"),("coal.png","coal_broken.png")]
        image_path, broken_path = random.choice(ores)
    else:
        image_path, broken_path = "tree.png","tree_broken.png"
    for _ in range(8):
        x = random.randint(inner_x_min, inner_x_max)
        y = random.randint(inner_y_min, inner_y_max)
        new_block = ColoredBlock(x,y,image_path,broken_path)
        if not any(new_block.rect.colliderect(b.rect) for b in colored_blocks) and not new_block.rect.colliderect(player.rect):
            colored_blocks.add(new_block)
            break

def spawn_enemy():
    for _ in range(20):
        x = random.randint(inner_x_min, inner_x_max-30)
        y = random.randint(inner_y_min, inner_y_max-30)
        enemy_rect = pygame.Rect(x, y, 30, 30)
        if not any(enemy_rect.colliderect(e.rect) for e in enemies) and not any(enemy_rect.colliderect(b.rect) for b in colored_blocks):
            enemy = Enemy(x, y)
            enemies.add(enemy)
            break

# -------------------------------
# Меню та пауза
# -------------------------------
def draw_menu(surface):
    surface.fill((0,0,0))
    title = font_big.render("MENU",True,(255,255,255))
    surface.blit(title,(WIDTH//2-title.get_width()//2,150))
    buttons = [("Почати гру",(WIDTH//2-100,250,200,50)),("Вийти",(WIDTH//2-100,320,200,50))]
    mouse_pos = pygame.mouse.get_pos()
    clicked = pygame.mouse.get_pressed()[0]
    result = None
    for text, rect in buttons:
        color = (200,200,200)
        if pygame.Rect(rect).collidepoint(mouse_pos):
            color = (255,255,0)
            if clicked:
                result = text
        pygame.draw.rect(surface,color,rect,border_radius=10)
        surface.blit(font_med.render(text,True,(0,0,0)),(rect[0]+30,rect[1]+10))
    return result

def draw_pause_menu(surface):
    surface.fill((0,0,0))
    title = font_big.render("ПАУЗА",True,(255,255,255))
    surface.blit(title,(WIDTH//2-title.get_width()//2,150))
    buttons = [("Продовжити",(WIDTH//2-100,250,200,50)),("Меню",(WIDTH//2-100,320,200,50)),("Вийти",(WIDTH//2-100,390,200,50))]
    mouse_pos = pygame.mouse.get_pos()
    clicked = pygame.mouse.get_pressed()[0]
    result = None
    for text, rect in buttons:
        color = (200,200,200)
        if pygame.Rect(rect).collidepoint(mouse_pos):
            color = (255,255,0)
            if clicked:
                result = text
        pygame.draw.rect(surface,color,rect,border_radius=10)
        surface.blit(font_med.render(text,True,(0,0,0)),(rect[0]+30,rect[1]+10))
    return result

# -------------------------------
# Основний цикл
# -------------------------------
SPAWN_EVENT = pygame.USEREVENT+1
ENEMY_SPAWN = pygame.USEREVENT+2
pygame.time.set_timer(SPAWN_EVENT,6000)
pygame.time.set_timer(ENEMY_SPAWN,8000)

paused = False
in_menu = True
mining_target = None
mining_start_time = None
MINING_DURATION = 3000
xp_progress = 0
xp_value = 0
xp_per_block = 0.5
lvl = 0
a = 10

while True:
    events = pygame.event.get()
    for event in events:
        if event.type==pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
            paused = not paused
        elif event.type==SPAWN_EVENT and not paused and not in_menu:
            spawn_block()
        elif event.type==ENEMY_SPAWN and not paused and not in_menu:
            spawn_enemy()
        elif not paused and not in_menu:
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                for block in colored_blocks:
                    if player.rect.colliderect(block.rect.inflate(20,20)):
                        mining_start_time = pygame.time.get_ticks()
                        mining_target = block
                        player.is_mining = True
                        break
            elif event.type==pygame.MOUSEBUTTONUP and event.button==1:
                player.is_mining = False
                mining_target = None
                mining_start_time = None

    # --- Меню ---
    if in_menu:
        mining_target=None
        player.is_mining=False
        result=draw_menu(screen)
        if result=="Почати гру":
            in_menu=False
            colored_blocks.empty()
            enemies.empty()
            xp_progress=0
            xp_value=0
            lvl=0
        elif result=="Вийти":
            pygame.quit()
            sys.exit()
        pygame.display.flip()
        clock.tick(FPS)
        continue

    # --- Пауза ---
    if paused:
        result=draw_pause_menu(screen)
        if result=="Продовжити":
            paused=False
        elif result=="Меню":
            in_menu=True
            paused=False
            mining_target=None
            player.is_mining=False
            colored_blocks.empty()
            enemies.empty()
            xp_progress=0
            xp_value=0
            lvl=0
        elif result=="Вийти":
            pygame.quit()
            sys.exit()
        pygame.display.flip()
        clock.tick(FPS)
        continue

    # --- Логіка гри ---
    player.update(walls, colored_blocks)
    for enemy in enemies:
        enemy.update(player, walls, colored_blocks)

    progress=0
    if mining_target and player.is_mining:
        elapsed=pygame.time.get_ticks()-mining_start_time
        if elapsed>=MINING_DURATION:
            mining_target.break_block()
            player.is_mining=False
            mining_target=None
            xp_value+=5
            xp_progress+=xp_per_block
            if xp_progress>1:
                xp_progress=0
        else:
            progress=elapsed/MINING_DURATION

    for block in list(colored_blocks):
        block.update()
        if block.is_broken and block.destroy_timer and pygame.time.get_ticks()>=block.destroy_timer:
            colored_blocks.remove(block)

    camera_x=max(0,min(player.rect.centerx-WIDTH//2,WORLD_WIDTH-WIDTH))
    camera_y=max(0,min(player.rect.centery-HEIGHT//2,WORLD_HEIGHT-HEIGHT))

    # --- Рендер ---
    screen.fill(LIGHT_BLUE)
    pygame.draw.rect(screen,GREEN,(333-camera_x,333-camera_y,333,333))

    player.draw(screen,camera_x,camera_y)
    for block in colored_blocks:
        block.draw(screen,camera_x,camera_y)
    for enemy in enemies:
        screen.blit(enemy.image,(enemy.rect.x-camera_x,enemy.rect.y-camera_y))

    if player.is_mining and progress>0:
        draw_progress_bar(screen,WIDTH//2-100,50,200,20,progress,(0,255,0))
    draw_progress_bar(screen,120,20,300,20,xp_progress,(0,128,255))

    screen.blit(font_small.render(f"XP: {xp_value} / {a}",True,(0,0,0)),(430,18))
    screen.blit(font_small.render(f"COIN:",True,(0,0,0)),(410,48))
    screen.blit(font_small.render(f"LVL:{lvl}",True,(0,0,0)),(60,18))
    screen.blit(b_image, (5, 10))
    screen.blit(b_image, (5, 50))
    screen.blit(b_image, (5, 90))
    screen.blit(a_image, (565, 10))
    screen.blit(a_image, (565, 50))
    screen.blit(a_image, (565, 90))
    screen.blit(a_image, (535, 10))
    screen.blit(a_image, (535, 50))
    screen.blit(a_image, (535, 90))

    pygame.display.flip()
    clock.tick(FPS)
