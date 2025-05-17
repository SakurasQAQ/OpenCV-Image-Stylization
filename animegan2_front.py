# animegan2_front.py
import torch
import cv2
import numpy as np
import os

from animegan2_model import Generator

class AnimeGANv2Front:
    def __init__(self, model_path: str = None, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = Generator().to(self.device)
        if model_path is None:
            model_path = os.path.join("checkpoints", "AnimeGANv2_epoch49.pth")
        state_dict = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.eval()


    def stylize_foreground(self, img_bgr, mask):
        if len(mask.shape) == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        _, mask_bin = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)

        fg = cv2.bitwise_and(img_bgr, img_bgr, mask=mask_bin)
        fg_rgb = cv2.cvtColor(fg, cv2.COLOR_BGR2RGB)
        h, w = fg_rgb.shape[:2]
        fg_resized = cv2.resize(fg_rgb, (256, 256))

        input_tensor = torch.from_numpy(fg_resized).float().div(127.5).sub(1.0)
        input_tensor = input_tensor.permute(2, 0, 1).unsqueeze(0).to(self.device)

        with torch.no_grad():
            out = self.model(input_tensor)[0].cpu()

        out = out.permute(1, 2, 0).numpy()
        out = ((out + 1.0) * 127.5).clip(0, 255).astype(np.uint8)
        stylized_rgb = cv2.resize(out, (w, h))
        stylized_bgr = cv2.cvtColor(stylized_rgb, cv2.COLOR_RGB2BGR)

        inv_mask = cv2.bitwise_not(mask_bin)
        background = cv2.bitwise_and(img_bgr, img_bgr, mask=inv_mask)
        result = cv2.add(background, stylized_bgr)
        return result
