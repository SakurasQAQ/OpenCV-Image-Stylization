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

_model_cache = {}  # 替代 _cartoon_model，全局缓存多个模型

def load_cartoon_model(style="Hayao"):
    if style in _model_cache:
        return _model_cache[style]

    model_path = os.path.join(
        os.path.dirname(__file__),
        f"CartoonGAN_Test/pretrained_model/{style}_net_G_float.pth"
    )
    model = Transformer()
    state = torch.load(model_path, map_location="cpu")
    model.load_state_dict(state)
    model.eval()
    _model_cache[style] = model
    return model



def apply_histogram_smoothing(img_bgr):
    yuv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YUV)
    yuv[..., 0] = cv2.equalizeHist(yuv[..., 0])
    result = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
    return cv2.GaussianBlur(result, (3, 3), 0)

def enhance_structure(img_bgr):
    return cv2.edgePreservingFilter(img_bgr, flags=1, sigma_s=60, sigma_r=0.4)

def cartoon_effect(img_bgr, mask=None, style="Hayao"):
    enhanced = enhance_structure(img_bgr)

    rgb = cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    L, a, b = cv2.split(lab)

    L_norm = (L.astype(np.float32) / 255.0) * 2.0 - 1.0

    tensor_L = torch.from_numpy(L_norm).unsqueeze(0).unsqueeze(0) 
    input_tensor = tensor_L.repeat(1, 3, 1, 1)                     

    model = load_cartoon_model(style)
    with torch.no_grad():
        out = model(input_tensor)       
        out = out.squeeze(0).cpu()      
        out = (out + 1.0) / 2.0         

    stylized_L = out.mean(dim=0).numpy()        
    stylized_L = (stylized_L * 255.0).clip(0,255).astype(np.uint8)


    stylized_L = cv2.resize(
        stylized_L,
        (a.shape[1], a.shape[0]),
        interpolation=cv2.INTER_LINEAR
    )

    stylized_L = stylized_L.astype(a.dtype)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))


    L_clahe = clahe.apply(L)  


    dark_mask = L < 50       


    alpha = 0.3                       
    beta  = 1.0 - alpha
 
    stylized_L[dark_mask] = (
        (alpha * L_clahe[dark_mask] + beta * stylized_L[dark_mask])
        .clip(0,255)
        .astype(np.uint8)
    )

    lab_stylized = cv2.merge([stylized_L, a, b])

    rgb_stylized = cv2.cvtColor(lab_stylized, cv2.COLOR_LAB2RGB)
    stylized_bgr = cv2.cvtColor(rgb_stylized, cv2.COLOR_RGB2BGR)


    stylized_bgr = apply_histogram_smoothing(stylized_bgr)


    if mask is not None:

        if len(mask.shape) == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)


        mask = cv2.bitwise_not(mask)

        _, mask_bin = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)

        result = img_bgr.copy()
        result[mask_bin == 255] = stylized_bgr[mask_bin == 255]
        return result


    return stylized_bgr


