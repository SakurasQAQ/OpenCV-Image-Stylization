import cv2
import numpy as np
import torch
from PIL import Image
import sys
import os

# 加载 CartoonGAN 模型
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


def cartoonize_foreground(img_bgr, mask):
    """
    仅对 mask 为前景的区域进行风格化，其他区域保持原样
    """
    # 确保 mask 是二值单通道 (0 or 255)
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask_bin = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)

    # 将前景区域提取出来
    fg = cv2.bitwise_and(img_bgr, img_bgr, mask=mask_bin)

    # cartoonGAN 输入必须是 RGB，resize 为 256x256
    fg_rgb = cv2.cvtColor(fg, cv2.COLOR_BGR2RGB)
    h, w = fg_rgb.shape[:2]
    fg_resized = cv2.resize(fg_rgb, (256, 256))

    # 归一化为 [-1, 1]
    input_tensor = (torch.from_numpy(fg_resized).permute(2, 0, 1).float() / 127.5) - 1.0
    input_tensor = input_tensor.unsqueeze(0)

    model = load_cartoon_model()
    with torch.no_grad():
        out = model(input_tensor)[0]  # [3, 256, 256]
    out = (out + 1) / 2.0  # [0, 1]
    out_np = out.permute(1, 2, 0).cpu().numpy()
    out_np = (out_np * 255).astype(np.uint8)
    stylized_rgb = cv2.resize(out_np, (w, h))

    # 合并前景（风格化） + 背景（原图）
    stylized_bgr = cv2.cvtColor(stylized_rgb, cv2.COLOR_RGB2BGR)
    inv_mask = cv2.bitwise_not(mask_bin)
    background = cv2.bitwise_and(img_bgr, img_bgr, mask=inv_mask)
    result = cv2.add(background, stylized_bgr)

    return result
