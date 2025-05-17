# animegan2_back.py
import torch
import cv2
import numpy as np
import os
from animegan2_model import Generator

class AnimeGANv2Back:
    def __init__(self, model_path: str = None, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = Generator().to(self.device)
        if model_path is None:
            model_path = os.path.join("checkpoints", "AnimeGANv2_epoch49.pth")
        state_dict = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.eval()


    def stylize_background(self, img_bgr, mask):
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]
        resized = cv2.resize(img_rgb, (256, 256))

        input_tensor = torch.from_numpy(resized).float().div(127.5).sub(1.0)
        input_tensor = input_tensor.permute(2, 0, 1).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(input_tensor)[0].cpu()

        output = output.permute(1, 2, 0).numpy()
        output = ((output + 1.0) * 127.5).clip(0, 255).astype(np.uint8)
        output_resized = cv2.resize(output, (w, h))
        stylized_bgr = cv2.cvtColor(output_resized, cv2.COLOR_RGB2BGR)

        if len(mask.shape) == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        _, mask_bin = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)
        inv_mask = cv2.bitwise_not(mask_bin)

        fg = cv2.bitwise_and(img_bgr, img_bgr, mask=mask_bin)
        bg = cv2.bitwise_and(stylized_bgr, stylized_bgr, mask=inv_mask)
        result = cv2.add(fg, bg)
        return result
