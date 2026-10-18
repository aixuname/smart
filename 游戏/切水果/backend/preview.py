# -*- coding: utf-8 -*-
"""
手势识别效果预览窗口。

独立于主服务的调试/展示工具：打开摄像头，跑 MediaPipe HandLandmarker，
在 OpenCV 窗口实时绘制 21 关键点骨架 + 手掌中心（刀锋点）高亮。
适合展台现场直观展示"系统在识别我的手"，也便于调参。

用法：
    python backend/preview.py            # 默认摄像头 0，镜像显示
    python backend/preview.py --camera 1
    python backend/preview.py --no-mirror
按 q 或 Esc 退出。

说明：镜像开关仅影响「显示画面」是否左右翻转（玩家常觉得本人视角需要翻转），
识别本身不受影响；刀锋点与骨架始终同步到显示帧。
"""
import argparse
import os
import sys
import time

import cv2
import numpy as np

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

try:
    from mediapipe_engine import ensure_model, _MP_AVAILABLE
    from config import MODELS_DIR, MP_MIN_DETECTION, MP_MIN_TRACKING
    from gesture_tracking import blade_position
    from pathlib import Path
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
    from mediapipe import Image, ImageFormat
except Exception as e:  # pragma: no cover
    print("初始化失败：%s" % e)
    print("请先安装依赖: pip install -r requirements.txt")
    sys.exit(1)


# MediaPipe 21 关键点骨架连线（按 MediaPipe 标准顺序）
HAND_CONNECTIONS = [
    # 腕-拇指
    (0, 1), (1, 2), (2, 3), (3, 4),
    # 食指
    (0, 5), (5, 6), (6, 7), (7, 8),
    # 中指
    (0, 9), (9, 10), (10, 11), (11, 12),
    # 无名指
    (0, 13), (13, 14), (14, 15), (15, 16),
    # 小指
    (0, 17), (17, 18), (18, 19), (19, 20),
    # 指根间
    (5, 9), (9, 13), (13, 17),
]

# 每根手指用不同颜色区分（BGR）
FINGER_COLORS = {
    "thumb": (0, 215, 255),      # 橙黄
    "index": (255, 115, 55),     # 蓝
    "middle": (55, 255, 5),      # 绿
    "ring": (255, 15, 25),       # 蓝紫
    "pinky": (55, 25, 5),        # 红
    "palm": (180, 180, 180),     # 灰（掌根间）
}

_FINGER_OF_POINT = {}
for i in range(5):
    _FINGER_OF_POINT[i] = "thumb"
for i in range(5, 9):
    _FINGER_OF_POINT[i] = "index"
for i in range(9, 13):
    _FINGER_OF_POINT[i] = "middle"
for i in range(13, 17):
    _FINGER_OF_POINT[i] = "ring"
for i in range(17, 21):
    _FINGER_OF_POINT[i] = "pinky"


def draw_hand_landmarks(frame, landmarks, w, h):
    """在帧上绘制 21 关键点骨架连线 + 关键点圆点。
    landmarks: [(x_norm, y_norm), ...] 归一化坐标元组列表。"""
    pts = [(int(x * w), int(y * h)) for (x, y) in landmarks]

    # 连线
    for (a, b) in HAND_CONNECTIONS:
        # 掌根间连线用灰，其余按起点手指颜色
        if (a == 0 and b in (5, 9, 13, 17)) or (a in (5, 9, 13, 17) and b in (9, 13, 17)):
            color = FINGER_COLORS["palm"]
        else:
            color = FINGER_COLORS.get(_FINGER_OF_POINT.get(a, "palm"), FINGER_COLORS["palm"])
        cv2.line(frame, pts[a], pts[b], color, 2, cv2.LINE_AA)

    # 关键点圆点
    for i, (x, y) in enumerate(pts):
        color = FINGER_COLORS.get(_FINGER_OF_POINT.get(i, "palm"), FINGER_COLORS["palm"])
        cv2.circle(frame, (x, y), 5, color, -1)


def main():
    parser = argparse.ArgumentParser(description="手势识别效果预览窗口")
    parser.add_argument("--camera", type=int, default=0, help="摄像头索引")
    parser.add_argument("--width", type=int, default=640, help="采集宽度")
    parser.add_argument("--height", type=int, default=480, help="采集高度")
    parser.add_argument("--mirror", dest="mirror", action="store_true", default=True,
                        help="镜像显示（玩家视角，默认开）")
    parser.add_argument("--no-mirror", dest="mirror", action="store_false",
                        help="不镜像显示")
    parser.add_argument("--max-hands", type=int, default=1, help="跟踪手数量")
    args = parser.parse_args()

    if not _MP_AVAILABLE:
        print("未安装 mediapipe，无法预览")
        sys.exit(1)

    # 复用引擎的模型下载/缓存逻辑（ASCII 路径）
    model_path = ensure_model(MODELS_DIR)
    if not model_path:
        print("模型不可用，退出")
        sys.exit(1)

    base = mp_python.BaseOptions(model_asset_buffer=Path(model_path).read_bytes())
    opts = vision.HandLandmarkerOptions(
        base_options=base,
        running_mode=vision.RunningMode.VIDEO,
        num_hands=args.max_hands,
        min_hand_detection_confidence=MP_MIN_DETECTION,
        min_hand_presence_confidence=MP_MIN_TRACKING,
        min_tracking_confidence=MP_MIN_TRACKING,
    )
    landmarker = vision.HandLandmarker.create_from_options(opts)

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print("无法打开摄像头 %d" % args.camera)
        cap.release()
        landmarker.close()
        sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    ts = 0
    print("预览已启动，按 q 或 Esc 退出。")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue
            ts = max(ts + 1, int(time.monotonic() * 1000))
            h, w = frame.shape[:2]

            rgb = frame[:, :, ::-1].copy()
            mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)
            result = landmarker.detect_for_video(mp_image, ts)

            # 显示帧（镜像）
            disp = frame
            if args.mirror:
                disp = cv2.flip(frame, 1)

            if result.hand_landmarks:
                for hand in result.hand_landmarks:
                    # 骨架直接画在显示帧（镜像后坐标需翻转 x）
                    pts_norm = [(1.0 - lm.x, lm.y) if args.mirror else (lm.x, lm.y) for lm in hand]
                    draw_hand_landmarks(disp, pts_norm, w, h)
                    # 默认以手掌中心控制刀片，与游戏默认值保持一致。
                    palm = blade_position(pts_norm)
                    tx = int(palm[0] * w)
                    ty = int(palm[1] * h)
                    cv2.circle(disp, (tx, ty), 12, (0, 255, 255), -1)
                    cv2.circle(disp, (tx, ty), 18, (0, 255, 255), 2, cv2.LINE_AA)
            else:
                cv2.putText(disp, "No hand detected", (16, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

            cv2.putText(disp, "q/Esc: quit   blade=palm center(yellow)",
                        (16, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (255, 255, 255), 1, cv2.LINE_AA)

            cv2.imshow("Gesture Recognition Preview", disp)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
    finally:
        cap.release()
        landmarker.close()
        cv2.destroyAllWindows()
        print("预览已退出")


if __name__ == "__main__":
    main()
