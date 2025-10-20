import pygame
import random
import heapq
import numpy as np
from collections import defaultdict

# 初始化Pygame
pygame.init()

# 游戏常量
WIDTH, HEIGHT = 800, 600
GRID_SIZE = 20
GRID_WIDTH = WIDTH // GRID_SIZE
GRID_HEIGHT = HEIGHT // GRID_SIZE
FPS = 240

# 颜色定义
COLORS = {
    "background": (30, 30, 30),
    "player": (0, 255, 0),
    "hunter": (255, 0, 0),
    "wall": (100, 100, 100),
    "exit": (0, 0, 255)
}

class QLearningAI:
    def __init__(self, alpha=0.1, gamma=0.9, epsilon=0.1):
        self.q_table = defaultdict(lambda: np.zeros(4))
        self.alpha = alpha  # 学习率
        self.gamma = gamma  # 折扣因子
        self.epsilon = epsilon  # 探索率

    def choose_action(self, state):
        if random.uniform(0, 1) < self.epsilon:
            return random.randint(0, 3)
        else:
            return np.argmax(self.q_table[state])

    def learn(self, state, action, reward, next_state):
        old_value = self.q_table[state][action]
        next_max = np.max(self.q_table[next_state])
        new_value = (1 - self.alpha) * old_value + self.alpha * (reward + self.gamma * next_max)
        self.q_table[state][action] = new_value


class HunterAI:
    def __init__(self, q_learning):
        self.q_learning = q_learning
        self.path = []
        self.update_interval = 10  # 每10帧更新一次路径
        self.frame_count = 0

    def update(self, start, target, walls):
        self.frame_count += 1
        if self.frame_count >= self.update_interval or not self.path:
            self.frame_count = 0
            self.a_star_path(start, target, walls)

    def a_star_path(self, start, target, walls):
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: heuristic(start, target)}

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == target:
                self.path = reconstruct_path(came_from, current)
                return

            for neighbor in get_neighbors(current, walls):
                tentative_g = g_score[current] + 1
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, target)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        self.path = []


def move_pos(pos, action):
    moves = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    dx, dy = moves[action]
    return pos[0] + dx, pos[1] + dy


class Game:
    def __init__(self):
        self.move_interval = 1
        self.level = 0
        self.base_move_interval = 50  # 初始基础移动间隔
        self.speed_increment = 1  # 每关速度提升量（帧数减少）
        self.hunter_ai = None
        self.q_learning = None
        self.score = None
        self.exit_pos = None
        self.walls = None
        self.hunters = None
        self.player = None
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.reset_game()
        self.player_move_interval = 15
        self.player_frame_count = 0

    def reset_game(self):
        self.player = (GRID_WIDTH // 2, GRID_HEIGHT // 2)
        self.hunters = []
        self.walls = self.generate_maze()
        self.exit_pos = self.generate_exit()
        self.score = 0
        self.q_learning = QLearningAI(epsilon=0.2)
        self.hunter_ai = HunterAI(self.q_learning)
        self.spawn_hunter()
        # 防止移动间隔过小（不低于5帧）
        self.move_interval = max(5, self.move_interval)
        # 最大敌人数量限制（例如不超过10）
        self.level = min(self.level, 10)

        # 动态调整敌人移动速度
        self.move_interval = max(3, self.base_move_interval - self.level * 2)

        # 每关敌人数量=关卡数
        for _ in range(self.level):
            self.spawn_hunter()

        # 动态计算移动间隔：每关减少2帧（速度变快）
        self.move_interval = max(5, self.base_move_interval - self.speed_increment * (self.level - 1))

    def check_collisions(self):
        if self.player == self.exit_pos:
            self.level += 1  # 过关后增加关卡数
            self.reset_game()
        if self.player in self.hunters:
            self.running = False

    def generate_maze(self):
        walls = set()
        # 初始化所有单元格为墙壁
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                walls.add((x, y))

        # 动态参数（根据关卡变化）
        branch_prob = max(0.1, 0.4 - self.level * 0.03)  # 分支概率随关卡降低
        connect_prob = 0.25 + self.level * 0.02  # 连接通道概率增加
        wall_density = 0.05 + self.level * 0.007  # 随机墙壁密度增加

        # 改进DFS生成算法
        start = self.player
        stack = [(start, None)]
        visited = set()
        visited.add(start)
        walls.discard(start)

        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        while stack:
            current, parent = stack.pop()

            # 创建分支（概率随关卡降低）
            if parent and random.random() < branch_prob:
                branch_dir = random.choice(directions)
                nx, ny = current[0] + branch_dir[0], current[1] + branch_dir[1]
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and (nx, ny) not in visited:
                    walls.discard((nx, ny))
                    visited.add((nx, ny))
                    stack.append(((nx, ny), current))
                    # 延伸分支路径（长度随关卡增加）
                    for _ in range(1 + self.level // 3):
                        nx += branch_dir[0]
                        ny += branch_dir[1]
                        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                            walls.discard((nx, ny))
                            visited.add((nx, ny))

            # 主路径生成（增加曲折度）
            random.shuffle(directions)
            for dx, dy in directions:
                nx, ny = current[0] + dx * (1 + self.level // 5), current[1] + dy * (1 + self.level // 5)
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT and (nx, ny) not in visited:
                    walls.discard((nx, ny))
                    visited.add((nx, ny))
                    stack.append(((nx, ny), current))

        # 动态连接通道生成
        for x in range(1, GRID_WIDTH - 1):
            for y in range(1, GRID_HEIGHT - 1):
                if (x, y) in walls:
                    # 根据关卡增加连接条件
                    if random.random() < connect_prob:
                        if {(x + 1, y), (x - 1, y)}.issubset(visited) or {(x, y + 1), (x, y - 1)}.issubset(visited):
                            walls.discard((x, y))

        # 渐进式增加随机墙壁
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                if (x, y) != self.player and (x, y) != self.exit_pos:
                    if random.random() < wall_density:
                        walls.add((x, y))
                    # 第5关后增加对角线墙壁
                    if self.level > 4 and random.random() < 0.03:
                        walls.add((x + 1, y))
                        walls.add((x, y + 1))

        return walls

    def generate_exit(self):
        # 选择四个角落中最远可达的位置
        candidates = [(0, 0), (GRID_WIDTH - 1, 0), (0, GRID_HEIGHT - 1), (GRID_WIDTH - 1, GRID_HEIGHT - 1)]
        exit_pos = max(candidates, key=lambda p: heuristic(self.player, p))

        # 确保至少两个角落可达
        reachable = self.find_reachable_positions()
        valid_exits = [p for p in candidates if p in reachable]
        return valid_exits[0] if valid_exits else self.player

    def spawn_hunter(self):
        """生成追捕者，确保不会与现有追捕者重叠"""
        from collections import deque

        # 获取所有可达位置（排除墙壁）
        visited = self.find_reachable_positions()

        # 生成追捕者的最大尝试次数
        max_attempts = 100
        attempts = 0

        while attempts < max_attempts:
            # 从可达位置中排除以下位置：
            # - 玩家位置
            # - 出口位置
            # - 现有追捕者位置
            valid_positions = list(visited - {self.player, self.exit_pos} - set(self.hunters))

            if not valid_positions:
                # 如果没有有效位置，尝试扩大搜索范围
                visited = self.find_reachable_positions(include_hunters=True)
                valid_positions = list(visited - {self.player, self.exit_pos} - set(self.hunters))

            if valid_positions:
                # 选择距离其他追捕者至少2格的位置
                if self.hunters:
                    # 计算所有现有追捕者的坐标
                    hunter_positions = set(self.hunters)
                    # 筛选最小距离>=2的位置
                    valid_positions = [
                        pos for pos in valid_positions
                        if all(heuristic(pos, h) >= 2 for h in hunter_positions)
                    ]

                if valid_positions:
                    hunter_pos = random.choice(valid_positions)
                    self.hunters.append(hunter_pos)
                    return  # 成功生成后退出

            attempts += 1

        # 保底生成逻辑（强制生成在玩家右侧两格）
        self.hunters.append((self.player[0] + 2, self.player[1]))

    def find_reachable_positions(self, include_hunters=False):
        """通过BFS查找所有可达位置"""
        from collections import deque
        visited = set()
        q = deque([self.player])
        visited.add(self.player)

        while q:
            x, y = q.popleft()
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                    # 是否考虑追捕者为障碍物
                    if not include_hunters and (nx, ny) in self.hunters:
                        continue
                    if (nx, ny) not in visited and (nx, ny) not in self.walls:
                        visited.add((nx, ny))
                        q.append((nx, ny))
        return visited

    def handle_input(self):
        self.player_frame_count += 1
        if self.player_frame_count % self.player_move_interval != 0:
            return

        keys = pygame.key.get_pressed()
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_DOWN]:
            dy += 1

        new_pos = (self.player[0] + dx, self.player[1] + dy)
        if self.is_valid_pos(new_pos):
            self.player = new_pos

    def is_valid_pos(self, pos):
        x, y = pos
        return 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT and pos not in self.walls

    def update_hunters(self):
        for i, hunter in enumerate(self.hunters):
            if self.score % self.move_interval == 0:
                state = self.get_state(hunter)
                action = self.q_learning.choose_action(state)
                new_pos = move_pos(hunter, action)

                if self.is_valid_pos(new_pos):
                    reward = self.calculate_reward(hunter, new_pos)
                    next_state = self.get_state(new_pos)
                    self.q_learning.learn(state, action, reward, next_state)
                    self.hunters[i] = new_pos

                # A*路径追踪
                self.hunter_ai.update(hunter, self.player, self.walls)
                if self.hunter_ai.path:
                    next_step = self.hunter_ai.path[0]
                    self.hunters[i] = next_step
                    del self.hunter_ai.path[0]

    def get_state(self, pos):
        dx = self.player[0] - pos[0]
        dy = self.player[1] - pos[1]
        return dx // 2, dy // 2  # 简化的状态空间

    def calculate_reward(self, hunter, new_pos):
        if new_pos == self.player:
            return 100  # 捕获玩家的奖励
        distance = heuristic(hunter, self.player)
        new_distance = heuristic(new_pos, self.player)
        return (distance - new_distance) * 10  # 根据距离变化给予奖励


    def draw_grid(self):
        self.screen.fill(COLORS["background"])
        for x in range(GRID_WIDTH):
            for y in range(GRID_HEIGHT):
                rect = pygame.Rect(x * GRID_SIZE, y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
                if (x, y) in self.walls:
                    pygame.draw.rect(self.screen, COLORS["wall"], rect)
                elif (x, y) == self.exit_pos:
                    pygame.draw.rect(self.screen, COLORS["exit"], rect)

        # 绘制玩家
        pygame.draw.circle(self.screen, COLORS["player"],
                           (int((self.player[0] + 0.5) * GRID_SIZE),
                            int((self.player[1] + 0.5) * GRID_SIZE)),
                           GRID_SIZE // 3)

        # 绘制追捕者
        for hunter in self.hunters:
            pygame.draw.polygon(self.screen, COLORS["hunter"], [
                (hunter[0] * GRID_SIZE, (hunter[1] + 0.5) * GRID_SIZE),
                ((hunter[0] + 0.5) * GRID_SIZE, hunter[1] * GRID_SIZE),
                ((hunter[0] + 1) * GRID_SIZE, (hunter[1] + 0.5) * GRID_SIZE),
                ((hunter[0] + 0.5) * GRID_SIZE, (hunter[1] + 1) * GRID_SIZE)
            ])

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.handle_input()
            self.update_hunters()
            self.check_collisions()
            self.draw_grid()

            pygame.display.flip()
            self.clock.tick(FPS)
            self.score += 1

            # 每30秒增加难度
            if self.score % 1800 == 0:
                self.spawn_hunter()
                self.q_learning.epsilon = max(0.01, self.q_learning.epsilon * 0.9)
        # 游戏结束后的显示循环
        self.show_game_over()
        pygame.quit()

    def show_game_over(self):
        font = pygame.font.Font(None, 74)
        small_font = pygame.font.Font(None, 36)

        while True:
            self.screen.fill(COLORS["background"])

            # 显示"Game Over"
            text = font.render("GAME OVER", True, (255, 0, 0))
            text_rect = text.get_rect(center=(WIDTH / 2, HEIGHT / 2 - 50))
            self.screen.blit(text, text_rect)

            # 显示通关关数
            level_text = small_font.render(f"Reached Level: {self.level}", True, (255, 255, 255))
            level_rect = level_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 30))
            self.screen.blit(level_text, level_rect)

            # 显示提示信息
            info_text = small_font.render("Press SPACE to restart / ESC to quit", True, (200, 200, 200))
            info_rect = info_text.get_rect(center=(WIDTH / 2, HEIGHT / 2 + 80))
            self.screen.blit(info_text, info_rect)

            pygame.display.flip()

            # 处理输入事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return
                    if event.key == pygame.K_SPACE:
                        self.__init__()
                        self.run()
                        return


def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_neighbors(pos, walls):
    neighbors = []
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        new_pos = (pos[0] + dx, pos[1] + dy)
        if new_pos not in walls and 0 <= new_pos[0] < GRID_WIDTH and 0 <= new_pos[1] < GRID_HEIGHT:
            neighbors.append(new_pos)
    return neighbors


def reconstruct_path(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    return path[::-1]


if __name__ == "__main__":
    game = Game()
    game.run()
