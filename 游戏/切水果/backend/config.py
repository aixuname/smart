# -*- coding: utf-8 -*-
"""
全局配置：端口 / 摄像头 / 平滑参数等
所有可调参数集中于此，方便展台现场微调。
"""
import os

# ---------------- 目录 ---------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # backend/
PROJECT_DIR = os.path.dirname(BASE_DIR)                        # 项目根目录
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")           # 前端静态目录
MODELS_DIR = os.path.join(BASE_DIR, "models")                  # MediaPipe .task 模型目录

# ---------------- 服务 ---------------
PORT = 8000                                                    # 服务端口（HTTP + WebSocket 同一端口）
CAMERA_ID = 0                                                  # 摄像头索引，0=默认摄像头
TARGET_FPS = 30                                                # 目标采样/推流帧率
STATUS_FPS = 2                                                 # 状态心跳频率（Hz）

# ---------------- 摄像头画面参数 ----------------
CAP_WIDTH = 640
CAP_HEIGHT = 480

# ---------------- MediaPipe Hands 手势引擎 ---------------
# 一站式手检测 + 21 关键点（不依赖肤色分割，对光线/背景鲁棒）
MP_MAX_HANDS = 1               # 同时跟踪的手数量（单人游戏 1 即可）
MP_MIN_DETECTION = 0.35        # 手掌检测阈值；兼顾较小/镜像手部，页面可调
MP_MIN_TRACKING = 0.5          # 帧间手框重叠阈值；失效触发重新检测，不能简单调低替代恢复
# -1 = 手掌中心（腕与四个指根的均值），8 = 食指尖，12 = 中指尖，0 = 腕
BLADE_POINT_INDEX = -1

# ---------------- 坐标平滑 ---------------
SMOOTH_ALPHA = 0.5            # EMA 指数平滑系数，越小越平滑但延迟越高
# 检测丢失立即结束出刀；前端在 300ms 未收到坐标时也会停刀。
