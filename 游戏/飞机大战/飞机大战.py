import pygame
import random
import math
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 全局声音变量
shoot_sound = None
explosion_sound = None
powerup_sound = None
hit_sound = None

# 初始化 Pygame
pygame.init()

# 加载背景音乐和音效
pygame.mixer.music.load("游戏\飞机大战\music\ground.mp3")
pygame.mixer.music.play(-1) # 循环播放

# 尝试加载音效（如果音效文件存在）
try:
    shoot_sound = pygame.mixer.Sound("游戏\飞机大战\music\shoot.wav")
    explosion_sound = pygame.mixer.Sound("游戏\飞机大战\music\explosion.wav")
    powerup_sound = pygame.mixer.Sound("游戏\飞机大战\music\powerup.wav")
    hit_sound = pygame.mixer.Sound("游戏\飞机大战\music\hit.wav")
except:
    # 如果音效文件不存在，则保持None值
    pass

# 游戏窗口设置
WIDTH, HEIGHT = 400,600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("太空防御者")

HIGH_SCORE = 'high_score.txt'
#读取最高分
def read_high_score():
    try:
        with open(HIGH_SCORE,'r') as file:
            return int(file.read())
    except (FileNotFoundError, ValueError):
        return 0

# 保存最高分
def save_high_score(score):
    with open(HIGH_SCORE, 'w') as file:
        file.write(str(score))

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 120, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)

# 粒子效果类
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.size = random.randint(2, 5)
        self.speed_x = random.uniform(-3, 3)
        self.speed_y = random.uniform(-3, 3)
        self.life = random.randint(20, 40)
        
    def update(self):
        self.x += self.speed_x
        self.y += self.speed_y
        self.life -= 1
        self.size = max(0, self.size - 0.1)
        
    def draw(self):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), int(self.size))
        
    def is_dead(self):
        return self.life <= 0

# 玩家飞船类
class Player:
    def __init__(self):
        self.width = 50
        self.height = 40
        self.x = WIDTH // 2 - self.width // 2
        self.y = HEIGHT - self.height - 20
        self.speed = 5
        self.color = GREEN
        self.health = 100
        self.score = 0
        self.level = 1
        self.shoot_cooldown = 0
        self.max_shoot_cooldown = 10  # 限制射击频率
        self.invincible = 0  # 无敌时间
        
    def draw(self):
        # 绘制飞船主体
        pygame.draw.polygon(screen, self.color, [
            (self.x + self.width // 2, self.y),
            (self.x, self.y + self.height),
            (self.x + self.width, self.y + self.height)
        ])
        
        # 绘制飞船引擎
        pygame.draw.rect(screen, YELLOW, 
                        (self.x + self.width // 2 - 5, self.y + self.height, 10, 15))
        
        # 绘制无敌状态效果
        if self.invincible > 0 and self.invincible % 6 < 3:  # 闪烁效果
            pygame.draw.circle(screen, WHITE, (self.x + self.width // 2, self.y + self.height // 2), 
                             max(self.width, self.height) // 2 + 5, 2)
        
    def move(self, direction):
        if direction == "left" and self.x > 0:
            self.x -= self.speed
        if direction == "right" and self.x < WIDTH - self.width:
            self.x += self.speed
        if direction == "up" and self.y > 0:
            self.y -= self.speed
        if direction == "down" and self.y < HEIGHT - self.width:
            self.y += self.speed
            
    def shoot(self):
        if self.shoot_cooldown <= 0:
            self.shoot_cooldown = self.max_shoot_cooldown
            if shoot_sound:
                shoot_sound.play()
            return Bullet(self.x + self.width // 2 - 2, self.y, -10, BLUE)
        return None
    
    def update(self):
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.invincible > 0:
            self.invincible -= 1
    
    def take_damage(self, amount):
        if self.invincible <= 0:
            self.health -= amount
            if self.health < 0:
                self.health = 0
            self.invincible = 30  # 0.5秒无敌时间
            if hit_sound:
                hit_sound.play()
            
    def increase_score(self, points):
        self.score += points
        # 每200分升一级
        if self.score // 200 + 1 > self.level:
            self.level = self.score // 200 + 1

# 子弹类
class Bullet:
    def __init__(self, x, y, speed, color):
        self.x = x
        self.y = y
        self.speed = speed
        self.color = color
        self.width = 4
        self.height = 10
        
    def update(self):
        self.y += self.speed
        
    def draw(self):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        # 添加子弹尾焰效果
        if self.speed < 0:  # 玩家子弹
            pygame.draw.rect(screen, YELLOW, (self.x, self.y + self.height, self.width, self.height * 2))
        else:  # 敌人子弹
            pygame.draw.rect(screen, RED, (self.x, self.y - self.height, self.width, self.height * 2))
        
    def is_off_screen(self):
        return self.y < 0 or self.y > HEIGHT

#血包类
class Medical:
    def __init__(self,level):
        self.width = 30
        self.height = 30
        self.recover = 10
        self.speed = random.uniform(1.0, 2.0 + level * 0.2)
        self.color = GREEN
        self.x = random.randint(0, WIDTH - self.width)
        self.y = random.randint(-100, -40)
    
    def update(self):
        self.y += self.speed

    def draw(self):
        # 绘制血包
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, WHITE, (self.x + self.width//2 - 2, self.y, 4, self.height))
        pygame.draw.rect(screen, WHITE, (self.x, self.y + self.height//2 - 2, self.width, 4))

    def is_off_screen(self):
        return self.y > HEIGHT

# 敌人类
class Enemy:
    def __init__(self, level):
        self.width = 30
        self.height = 30
        self.x = random.randint(0, WIDTH - self.width)
        self.y = random.randint(-100, -40)
        
        # 难度随等级提升
        self.speed = random.uniform(1.0, 2.0 + level * 0.2)
        self.health = 1 + level // 5  # 每5级增加1点生命值
        
        # 根据敌人类型设置颜色
        if self.health == 1:
            self.color = RED
        elif self.health == 2:
            self.color = ORANGE  # 橙色
        else:
            self.color = PURPLE  # 紫色
            
    def update(self):
        self.y += self.speed
        
    def draw(self):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        
        # 绘制敌人细节
        pygame.draw.rect(screen, BLACK, (self.x + 5, self.y + 5, 5, 5))
        pygame.draw.rect(screen, BLACK, (self.x + 20, self.y + 5, 5, 5))
        
        # 绘制生命值条
        if self.health > 1:
            bar_width = self.width
            bar_height = 5
            pygame.draw.rect(screen, RED, (self.x, self.y - 10, bar_width, bar_height))
            health_ratio = self.health / (1 + 0)  # 基础生命值需要动态计算
            pygame.draw.rect(screen, GREEN, (self.x, self.y - 10, bar_width * health_ratio, bar_height))
        
    def is_off_screen(self):
        return self.y > HEIGHT
    
    def shoot(self, player_x, player_y):
        # 高级敌人有概率射击
        if self.health > 1 and random.random() < 0.01:
            dx = player_x - self.x
            dy = player_y - self.y
            dist = max(1, math.sqrt(dx*dx + dy*dy))  # 避免除以零
            speed = 3
            return Bullet(self.x + self.width // 2, self.y, speed * dy/dist, YELLOW)
        return None

# 爆炸效果类
class Explosion:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 5
        self.max_radius = 30
        self.growing = True
        
    def update(self):
        if self.growing:
            self.radius += 2
            if self.radius >= self.max_radius:
                self.growing = False
        else:
            self.radius -= 2
            
    def draw(self):
        pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), max(0, self.radius - 5))
        
    def is_finished(self):
        return self.radius <= 0


# 游戏主函数
def main():
    clock = pygame.time.Clock()
    player = Player()
    bullets = []
    enemy_bullets = []
    enemies = []
    medicals = []
    explosions = []
    particles = []  # 粒子效果列表
    
    # 读取最高分
    high_score = read_high_score()
    new_high_score = False

    font = pygame.font.SysFont(None, 36)
    small_font = pygame.font.SysFont(None, 24)
    
    enemy_spawn_timer = 0
    enemy_spawn_delay = 60  # 初始敌人生成延迟（帧数）
    medical_spawn_timer = 0
    medical_spawn_delay = 300
    
    paused = False  # 暂停状态

    running = True
    game_over = False
    
    while running:
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and not game_over and not paused:
                    new_bullet = player.shoot()
                    if new_bullet:
                        bullets.append(new_bullet)
                elif event.key == pygame.K_r and game_over:
                    # 重新开始游戏
                    return main()
                elif event.key == pygame.K_p:  # 暂停/继续游戏
                    paused = not paused
        pygame.display.update()
        
        if not game_over and not paused:
            # 更新玩家
            player.update()
            
            # 玩家移动
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                player.move("left")
            if keys[pygame.K_RIGHT]:
                player.move("right")
            if keys[pygame.K_UP]:
                player.move("up")
            if keys[pygame.K_DOWN]:
                player.move("down")
                
            # 更新子弹
            for bullet in bullets[:]:
                bullet.update()
                if bullet.is_off_screen():
                    bullets.remove(bullet)
                    
            # 更新敌人子弹
            for bullet in enemy_bullets[:]:
                bullet.update()
                if bullet.is_off_screen():
                    enemy_bullets.remove(bullet)
                    
            # 生成敌人 - 难度随等级提升
            enemy_spawn_timer += 1
            if enemy_spawn_timer >= max(10, enemy_spawn_delay - player.level * 2):
                enemy_spawn_timer = 0
                enemies.append(Enemy(player.level))

            #生成血包
            medical_spawn_timer += 1
            if medical_spawn_timer >= max(10, medical_spawn_delay - player.level * 2):
                medical_spawn_timer = 0
                medicals.append(Medical(player.level))
            
            #更新血包
            for medical in medicals[:]:
                medical.update()

                #检查是否与玩家碰撞
                if (medical.y + medical.height > player.y and
                    medical.x < player.x + player.width and
                    medical.x + medical.width > player.x and
                    medical.y < player.y + player.height):
                    player.health = min(100, player.health + medical.recover)
                    medicals.remove(medical)
                    if powerup_sound:
                        powerup_sound.play()
                    # 添加粒子效果
                    for _ in range(30):
                        particles.append(Particle(medical.x + medical.width//2, 
                                                medical.y + medical.height//2, GREEN))
                    continue

                #检查是否飞出屏幕
                if medical.is_off_screen():
                    medicals.remove(medical)

            # 更新敌人
            for enemy in enemies[:]:
                enemy.update()
                
                # 敌人射击
                bullet = enemy.shoot(player.x + player.width // 2, player.y + player.height)
                if bullet:
                    enemy_bullets.append(bullet)
                
                # 检查敌人是否击中玩家
                if (enemy.y + enemy.height > player.y and
                    enemy.x < player.x + player.width and
                    enemy.x + enemy.width > player.x):
                    player.take_damage(5)
                    explosions.append(Explosion(enemy.x + enemy.width // 2, enemy.y + enemy.height // 2))
                    if explosion_sound:
                        explosion_sound.play()
                    # 添加粒子效果
                    for _ in range(50):
                        particles.append(Particle(enemy.x + enemy.width//2, 
                                                enemy.y + enemy.height//2, enemy.color))
                    enemies.remove(enemy)
                    continue
                
                # 检查敌人是否飞出屏幕
                if enemy.is_off_screen():
                    player.take_damage(5)
                    enemies.remove(enemy)
                    continue
                    
                # 检查子弹是否击中敌人
                for bullet in bullets[:]:
                    if (bullet.x < enemy.x + enemy.width and
                        bullet.x + bullet.width > enemy.x and
                        bullet.y < enemy.y + enemy.height and
                        bullet.y + bullet.height > enemy.y):
                        enemy.health -= 1
                        if enemy.health <= 0:
                            player.increase_score(10 * player.level)
                            explosions.append(Explosion(enemy.x + enemy.width // 2, enemy.y + enemy.height // 2))
                            if explosion_sound:
                                explosion_sound.play()
                            # 添加粒子效果
                            for _ in range(50):
                                particles.append(Particle(enemy.x + enemy.width//2, 
                                                        enemy.y + enemy.height//2, enemy.color))
                            enemies.remove(enemy)
                        if bullet in bullets:
                            bullets.remove(bullet)
                        break
                        
            # 检查敌人子弹是否击中玩家
            for bullet in enemy_bullets[:]:
                if (bullet.x < player.x + player.width and
                    bullet.x + bullet.width > player.x and
                    bullet.y < player.y + player.height and
                    bullet.y + bullet.height > player.y):
                    player.take_damage(1)
                    if bullet in enemy_bullets:
                        enemy_bullets.remove(bullet)
                    if hit_sound:
                        hit_sound.play()
 
            # 更新爆炸效果
            for explosion in explosions[:]:
                explosion.update()
                if explosion.is_finished():
                    explosions.remove(explosion)
                    
            # 更新粒子效果
            for particle in particles[:]:
                particle.update()
                if particle.is_dead():
                    particles.remove(particle)
                    
            # 检查游戏是否结束
            if player.health <= 0:
                game_over = True
                # 检查是否打破最高分
                if player.score > high_score:
                    high_score = player.score
                    save_high_score(high_score)
                    new_high_score = True
        
        # 绘制背景
        try:
            background_img = pygame.image.load("游戏\飞机大战\image\ground.jpg").convert()
            screen.blit(background_img, (0, 0))
        except:
            # 如果背景图片不存在，用纯色背景
            screen.fill(BLACK)
        
        # 绘制玩家
        player.draw()
        
        # 绘制子弹
        for bullet in bullets:
            bullet.draw()
            
        # 绘制敌人子弹
        for bullet in enemy_bullets:
            bullet.draw()
            
        # 绘制敌人
        for enemy in enemies:
            enemy.draw()
        
        #绘制血包
        for medical in medicals:
            medical.draw()

        # 绘制爆炸效果
        for explosion in explosions:
            explosion.draw()
            
        # 绘制粒子效果
        for particle in particles:
            particle.draw()
            
        # 绘制UI
        font = pygame.font.SysFont('simhei', 20)
        health_text = font.render(f"生命值: {player.health}", True, GREEN)
        score_text = font.render(f"分数: {player.score}", True, WHITE)
        level_text = font.render(f"等级: {player.level}", True, YELLOW)
        high_score_text = font.render(f"最高分: {high_score}", True, YELLOW)
        
        screen.blit(health_text, (10, 10))
        screen.blit(score_text, (10, 50))
        screen.blit(level_text, (10, 90))
        screen.blit(high_score_text, (10, 130))
        
        # 绘制暂停提示
        if paused:
            pause_font = pygame.font.SysFont('simhei', 36)
            pause_text = pause_font.render("游戏暂停", True, YELLOW)
            screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, HEIGHT//2 - 50))
            continue_text = font.render("按 P 键继续", True, WHITE)
            screen.blit(continue_text, (WIDTH//2 - continue_text.get_width()//2, HEIGHT//2 + 10))
        
        # 绘制游戏结束画面
        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))
            
            font = pygame.font.SysFont('simhei', 15)
            game_over_text = font.render("游戏结束!", True, RED)
            final_score_text = font.render(f"最终分数: {player.score}", True, WHITE)

            if new_high_score:
                new_high_text = font.render("新纪录! 恭喜!", True, YELLOW)
                screen.blit(new_high_text, (WIDTH // 2 - new_high_text.get_width() // 2, HEIGHT // 2 + 100))
            
            screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 2 - 50))
            screen.blit(final_score_text, (WIDTH // 2 - final_score_text.get_width() // 2, HEIGHT // 2))
            
            restart_text = font.render("按 R 键重新开始", True, GREEN)
            screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 50))

        # 绘制控制说明
        font = pygame.font.SysFont('simhei', 10)
        controls_text = font.render("方向键移动，空格键射击，P键暂停", True, WHITE)
        screen.blit(controls_text, (WIDTH - controls_text.get_width() - 10, HEIGHT - 30))
        
        pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()