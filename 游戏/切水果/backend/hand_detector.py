# -*- coding: utf-8 -*-
"""
手部 bbox 检测器。

handpose_x 只做关键点回归，需要外部提供手部区域。本模块提供
基于 YCrCb 肤色分割 + 最大连通域的轻量检测实现（无额外依赖），
输出正方形 bbox（边长取宽高较大者，并放大 1.1 倍，与 handpose_x
官方预处理一致），供关键点模型裁剪输入。

接口抽象为 Detector，便于后续替换为 MediaPipe 等更鲁棒的检测器。
"""
import cv2
import numpy as np


class Detector:
    """手部检测器接口。detect() 返回 (cx, cy, size) 或 None。"""

    def detect(self, frame_bgr):
        raise NotImplementedError


class OpenCVSkinDetector(Detector):
    """YCrCb 肤色分割 + 运动感知的手部检测。

    候选肤色连通域按以下优先级选择，避免背景固定肤色物体（人脸/桌面/
    海报）抢到手部位置：
      1. 画面存在运动候选时（手部在动），优先选运动重合度高的肤色块；
      2. 画面静止时，优先选上一帧手部位置附近的肤色块（保持跟踪）；
      3. 首帧/丢失后无上下文时，退回面积最大者。
    """

    def __init__(self, min_area_ratio=0.008, max_area_ratio=0.35,
                 expand_ratio=1.1, edge_margin=12,
                 motion_thresh=18, motion_ratio_thresh=0.12,
                 motion_weight=3.0):
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.expand_ratio = expand_ratio
        self.edge_margin = edge_margin  # 避免 bbox 贴边的安全边距(px)
        self.motion_thresh = motion_thresh  # 帧差阈值
        self.motion_ratio_thresh = motion_ratio_thresh  # 判定"在动"的运动像素占比
        self.motion_weight = motion_weight  # 运动候选排序时的运动占比权重
        self._prev_gray = None
        self._last_box = None  # (cx, cy, size) 上一帧选中位置

    def _skin_mask(self, frame_bgr):
        """返回二值肤色掩码(0/255)。"""
        ycrcb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2YCrCb)
        Y, Cr, Cb = ycrcb[:, :, 0].astype(np.float32), \
                    ycrcb[:, :, 1].astype(np.float32), \
                    ycrcb[:, :, 2].astype(np.float32)

        # 基础肤色范围（YCrCb）
        mask = (Y > 60) & (Y < 250) & (Cr > 133) & (Cr < 173) & (Cb > 77) & (Cb < 127)

        # 亮度自适应：环境过暗时放宽 Cr 下界，避免漏检
        mean_y = float(np.mean(Y))
        if mean_y < 100:
            mask |= (Y > 50) & (Cr > 125) & (Cr < 178) & (Cb > 70) & (Cb < 130)

        mask = (mask.astype(np.uint8)) * 255

        # 形态学：开运算去噪 + 膨胀连接手指区域
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=3)
        return mask

    def detect(self, frame_bgr):
        """返回 (cx, cy, size)：手部中心与正方形边长；检测不到返回 None。"""
        h, w = frame_bgr.shape[:2]
        mask = self._skin_mask(frame_bgr)
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        # 运动掩码：与上一帧灰度差分（手在动时 bbox 内出现大块运动像素）
        motion = np.zeros((h, w), np.uint8)
        if self._prev_gray is not None:
            diff = cv2.absdiff(gray, self._prev_gray)
            motion = (diff > self.motion_thresh).astype(np.uint8) * 255
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            motion = cv2.morphologyEx(motion, cv2.MORPH_CLOSE, kernel, iterations=2)
        self._prev_gray = gray.copy()

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            self._last_box = None
            return None

        # 候选区域：过滤过小/过大连通域
        candidates = []
        frame_area = h * w
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < frame_area * self.min_area_ratio:
                continue
            if area > frame_area * self.max_area_ratio:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            # 该连通域内运动像素占比
            if bw * bh > 0:
                mr = float(cv2.countNonZero(motion[y:y + bh, x:x + bw])) / (bw * bh)
            else:
                mr = 0.0
            candidates.append((area, x, y, bw, bh, mr))

        if not candidates:
            self._last_box = None
            return None

        # 选择策略
        moving = [c for c in candidates if c[5] > self.motion_ratio_thresh]
        if moving:
            # 手在动：运动候选内按 面积*(1+运动权重*占比) 排序
            pick = max(moving, key=lambda c: c[0] * (1.0 + self.motion_weight * c[5]))
        elif self._last_box is not None:
            # 画面静止但有历史位置：选离上一帧手部最近的候选（保持跟踪）
            lx, ly = self._last_box[0], self._last_box[1]
            pick = min(candidates, key=lambda c: (c[1] + c[3] / 2.0 - lx) ** 2 +
                       (c[2] + c[4] / 2.0 - ly) ** 2)
        else:
            # 无上下文：退回面积最大（手靠近镜头时通常最大）
            pick = max(candidates, key=lambda c: c[0])

        _, x, y, bw, bh, _ = pick

        # 转正方形：以手部中心为基准，边长取宽高较大值并放大 expand_ratio
        cx = x + bw / 2.0
        cy = y + bh / 2.0
        size = max(bw, bh) * self.expand_ratio

        # 安全边距与边界裁剪
        size = min(size, min(w, h) - self.edge_margin)
        if size <= 0:
            self._last_box = None
            return None
        cx = float(np.clip(cx, 0, w))
        cy = float(np.clip(cy, 0, h))
        self._last_box = (cx, cy, size)
        return cx, cy, size

    def crop(self, frame_bgr, box):
        """按 (cx, cy, size) 正方形裁剪并返回 (裁剪图, 左上角偏移, 边长)。"""
        h, w = frame_bgr.shape[:2]
        cx, cy, size = box
        half = size / 2.0
        x0 = int(max(0, cx - half))
        y0 = int(max(0, cy - half))
        x1 = int(min(w, cx + half))
        y1 = int(min(h, cy + half))
        crop = frame_bgr[y0:y1, x0:x1]
        return crop, (x0, y0), size
