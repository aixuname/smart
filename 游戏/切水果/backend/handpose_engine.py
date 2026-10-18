# -*- coding: utf-8 -*-
"""
handpose_x 手部关键点推理引擎。

从 backend/handpose_x/（自动 clone 的官方仓库）加载模型定义，
加载用户下载的预训练权重，对裁剪出的手部图像做 21 关键点回归。
输出关键点的全图像素坐标。

推理流程与官方 inference.py 保持一致：
    裁剪手部图 -> resize(256,256) -> (img-128)/256 -> CHW -> 模型前向
    -> 输出 42 维 [21 个 (x,y) 归一化坐标] -> 还原到裁剪图 -> 加 bbox 偏移
"""
import os
import sys

import cv2
import numpy as np
import torch

from config import (MODELS_DIR, HAND_X_DIR, MODEL_TYPE, MODEL_PATH,
                    NUM_CLASSES, IMG_SIZE, BLADE_POINT_INDEX, USE_CUDA)

# ---------------------------------------------------------------------------
# 模型构造函数映射：与 handpose_x 的 model2onnx.py / train.py 保持一致
# ---------------------------------------------------------------------------
def _build_model(model_type, num_classes):
    hand_x_dir = HAND_X_DIR
    if not os.path.isdir(hand_x_dir):
        raise FileNotFoundError(
            "未找到 handpose_x 源码目录，请运行 main.py 自动拉取，"
            "或手动执行: git clone https://github.com/XIAN-HHappy/handpose_x.git %s"
            % hand_x_dir
        )
    if hand_x_dir not in sys.path:
        sys.path.insert(0, hand_x_dir)

    img_size = IMG_SIZE

    if model_type == "resnet_18":
        from models.resnet import resnet18
        return resnet18(num_classes=num_classes, img_size=img_size)
    if model_type == "resnet_34":
        from models.resnet import resnet34
        return resnet34(num_classes=num_classes, img_size=img_size)
    if model_type == "resnet_50":
        from models.resnet import resnet50
        return resnet50(num_classes=num_classes, img_size=img_size)
    if model_type == "resnet_101":
        from models.resnet import resnet101
        return resnet101(num_classes=num_classes, img_size=img_size)
    if model_type == "squeezenet1_0":
        from models.squeezenet import squeezenet1_0
        return squeezenet1_0(num_classes=num_classes)
    if model_type == "squeezenet1_1":
        from models.squeezenet import squeezenet1_1
        return squeezenet1_1(num_classes=num_classes)
    if model_type == "shufflenetv2":
        from models.shufflenetv2 import ShuffleNetV2
        return ShuffleNetV2(ratio=1.0, num_classes=num_classes)
    if model_type == "shufflenet":
        from models.shufflenet import ShuffleNet
        return ShuffleNet(num_blocks=[2, 4, 2], num_classes=num_classes, groups=3)
    if model_type == "mobilenetv2":
        from models.mobilenetv2 import MobileNetV2
        return MobileNetV2(num_classes=num_classes)
    if model_type == "rexnetv1":
        from models.rexnetv1 import ReXNetV1
        return ReXNetV1(num_classes=num_classes)
    if model_type.startswith("shufflenet_v2_x"):
        from torchvision.models import (shufflenet_v2_x1_5, shufflenet_v2_x1_0,
                                        shufflenet_v2_x2_0)
        builders = {
            "shufflenet_v2_x1_5": shufflenet_v2_x1_5,
            "shufflenet_v2_x1_0": shufflenet_v2_x1_0,
            "shufflenet_v2_x2_0": shufflenet_v2_x2_0,
        }
        return builders[model_type](pretrained=False, num_classes=num_classes)
    raise ValueError("未知模型类型: %s" % model_type)


def _auto_find_model_path():
    """在 models 目录下自动查找第一个 *.pth 权重文件。"""
    if not os.path.isdir(MODELS_DIR):
        return ""
    for name in sorted(os.listdir(MODELS_DIR)):
        if name.lower().endswith((".pth", ".pt")):
            return os.path.join(MODELS_DIR, name)
    return ""


class HandposeModelMissing(Exception):
    """模型权重缺失时抛出，上层捕获后向前端广播 model_missing 状态。"""


class HandposeEngine:
    def __init__(self, model_type=MODEL_TYPE, model_path=MODEL_PATH,
                 num_classes=NUM_CLASSES, img_size=IMG_SIZE,
                 blade_point_index=BLADE_POINT_INDEX, use_cuda=USE_CUDA):
        self.model_type = model_type
        self.num_classes = num_classes
        self.img_size = img_size
        self.blade_point_index = blade_point_index

        # 解析权重路径
        self.model_path = model_path or _auto_find_model_path()
        if not self.model_path or not os.path.isfile(self.model_path):
            raise HandposeModelMissing(
                "未找到 handpose_x 预训练权重，请将模型放入 %s 目录"
                "（下载地址见 README，百度网盘提取码 99f3）" % MODELS_DIR
            )

        # 设备
        self.use_cuda = use_cuda and torch.cuda.is_available()
        self.device = torch.device("cuda:0" if self.use_cuda else "cpu")

        # 构建模型 + 加载权重
        self.model = _build_model(model_type, num_classes)
        chkpt = torch.load(self.model_path, map_location=self.device,
                           weights_only=False)
        self.model.load_state_dict(chkpt)
        self.model = self.model.to(self.device)
        self.model.eval()

        print("[HandposeEngine] 模型加载成功: %s (%s)"
              % (self.model_type, self.model_path))
        print("[HandposeEngine] 推理设备: %s" % self.device)

    @torch.no_grad()
    def infer(self, crop_bgr, offset):
        """
        对手部裁剪图做关键点回归。
        crop_bgr: BGR 裁剪图（正方形）
        offset:   (x0, y0) 裁剪图在全图中的左上角偏移
        返回: 21 个关键点的全图像素坐标 [[x, y], ...] 或 None
        """
        if crop_bgr is None or crop_bgr.size == 0:
            return None
        h, w = crop_bgr.shape[:2]
        if h <= 0 or w <= 0:
            return None

        # 预处理（与官方一致）
        img_ = cv2.resize(crop_bgr, (self.img_size, self.img_size))
        img_ = (img_.astype(np.float32) - 128.0) / 256.0
        img_ = img_.transpose(2, 0, 1)              # HWC -> CHW
        img_ = torch.from_numpy(img_).unsqueeze_(0)  # 加 batch 维

        if self.use_cuda:
            img_ = img_.cuda()
        img_ = img_.float()

        output = self.model(img_)
        output = output.cpu().detach().numpy()
        output = np.squeeze(output)  # (42,)

        # 归一化坐标 -> 裁剪图像素 -> 全图像素
        x0, y0 = offset
        pts = []
        n = output.shape[0] // 2
        for i in range(n):
            x = output[i * 2 + 0] * float(w) + x0
            y = output[i * 2 + 1] * float(h) + y0
            pts.append([float(x), float(y)])
        return np.array(pts)

    def blade_point(self, pts):
        """从关键点中取出刀锋点 (x, y)（默认食指指尖）。"""
        if pts is None or len(pts) <= self.blade_point_index:
            return None
        p = pts[self.blade_point_index]
        return float(p[0]), float(p[1])
