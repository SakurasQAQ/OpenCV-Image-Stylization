import cv2
import numpy as np
import torch
from PIL import Image
import sys
import os

# 添加 CartoonGAN 路径
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'CartoonGAN_Test')
))
from CartoonGAN_Test.network.Transformer import Transformer

_cartoon_model = None
def load_cartoon_model():
    global _cartoon_model
    if _cartoon_model is None:
        _cartoon_model = Transformer()
        model_path = os.path.join(
            os.path.dirname(__file__),
            "CartoonGAN_Test/pretrained_model/Hayao_net_G_float.pth"
        )
        state = torch.load(model_path, map_location="cpu")
        _cartoon_model.load_state_dict(state)
        _cartoon_model.eval()
    return _cartoon_model

def apply_histogram_smoothing(img_bgr):
    yuv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YUV)
    yuv[..., 0] = cv2.equalizeHist(yuv[..., 0])
    result = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
    return cv2.GaussianBlur(result, (3, 3), 0)

def enhance_structure(img_bgr):
    return cv2.edgePreservingFilter(img_bgr, flags=1, sigma_s=60, sigma_r=0.4)

def cartoon_effect(img_bgr, mask=None):
    # 1. 结构增强
    enhanced = enhance_structure(img_bgr)

    # 2. BGR→RGB→LAB，拆出 L,a,b
    rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    L, a, b = cv2.split(lab)

    # 3. 归一化 L 到 [-1,1]
    L_norm = (L.astype(np.float32) / 255.0) * 2.0 - 1.0

    # 4. 构造 3 通道输入，shape [1,3,H,W]
    tensor_L = torch.from_numpy(L_norm).unsqueeze(0).unsqueeze(0)  # [1,1,H,W]
    input_tensor = tensor_L.repeat(1, 3, 1, 1)                     # [1,3,H,W]

    # 5. 网络推理
    model = load_cartoon_model()
    with torch.no_grad():
        out = model(input_tensor)       # [1,3,256,256]
        out = out.squeeze(0).cpu()      # [3,256,256]
        out = (out + 1.0) / 2.0         # 映射到 [0,1]

    # 6. 三通道平均，反归一化回 [0,255]
    stylized_L = out.mean(dim=0).numpy()         # [256,256]
    stylized_L = (stylized_L * 255.0).clip(0,255).astype(np.uint8)

    # 7. 合并原始 a,b 通道，转回 BGR
    # 1) 让 stylized_L 和 a、b 尺寸一致
    stylized_L = cv2.resize(
        stylized_L,
        (a.shape[1], a.shape[0]),
        interpolation=cv2.INTER_LINEAR
    )
    # 2) 确保都是 uint8
    stylized_L = stylized_L.astype(a.dtype)
    # --- 在 stylized_L 已经是 uint8、和原 L 同尺寸之后，做 CLAHE 暗部增强 ---
    # 1）构造 CLAHE 对象
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

    # 2）只对原始 L 通道的暗部（L < 阈值）做自适应均衡
    #    先生成一个 CLAHE 增强版本的原始 L 通道
    L_clahe = clahe.apply(L)  # uint8

    #    定义“暗部”阈值，比如 L<50
    dark_mask = L < 50        # bool 数组

    # 3）在暗部区域，用 L_clahe 和 stylized_L 做线性叠加，避免过曝
    alpha = 0.3                       # CLAHE 成分比例（可调小一些）
    beta  = 1.0 - alpha
    # 只在暗部像素上，替换 stylized_L
    stylized_L[dark_mask] = (
        (alpha * L_clahe[dark_mask] + beta * stylized_L[dark_mask])
        .clip(0,255)
        .astype(np.uint8)
    )
    # 3) 合并
    lab_stylized = cv2.merge([stylized_L, a, b])

    rgb_stylized = cv2.cvtColor(lab_stylized, cv2.COLOR_LAB2RGB)
    stylized_bgr = cv2.cvtColor(rgb_stylized, cv2.COLOR_RGB2BGR)

    # 8. 后处理
    stylized_bgr = apply_histogram_smoothing(stylized_bgr)

    # 9. 可选的 mask 应用
    if mask is not None:
    # 1) 保证 mask 是灰度单通道
        if len(mask.shape) == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)

    # 2) 把黑白颠倒 —— 这样 255 就是前景
        mask = cv2.bitwise_not(mask)

    # 3) 二值化，确保只有 0/255
        _, mask_bin = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)

    # 4) 应用到前景
        result = img_bgr.copy()
        result[mask_bin == 255] = stylized_bgr[mask_bin == 255]
        return result


    return stylized_bgr


