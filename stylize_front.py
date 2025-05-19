import cv2
import numpy as np
import torch
from PIL import Image
import sys
import os


sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'CartoonGAN_Test')
))
from CartoonGAN_Test.network.Transformer import Transformer

_model_cache = {}  

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



def cartoonize_foreground(img_bgr, mask, style="Hayao"):


    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    _, mask_bin = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)


    fg = cv2.bitwise_and(img_bgr, img_bgr, mask=mask_bin)

    fg_rgb = cv2.cvtColor(fg, cv2.COLOR_BGR2RGB)
    h, w = fg_rgb.shape[:2]
    fg_resized = cv2.resize(fg_rgb, (256, 256))

    input_tensor = (torch.from_numpy(fg_resized).permute(2, 0, 1).float() / 127.5) - 1.0
    input_tensor = input_tensor.unsqueeze(0)

    model = load_cartoon_model(style)
    with torch.no_grad():
        out = model(input_tensor)[0]  
    out = (out + 1) / 2.0  
    out_np = out.permute(1, 2, 0).cpu().numpy()
    out_np = (out_np * 255).astype(np.uint8)
    stylized_rgb = cv2.resize(out_np, (w, h))

    stylized_bgr = cv2.cvtColor(stylized_rgb, cv2.COLOR_RGB2BGR)
    inv_mask = cv2.bitwise_not(mask_bin)
    background = cv2.bitwise_and(img_bgr, img_bgr, mask=inv_mask)
    result = cv2.add(background, stylized_bgr)

    return result
