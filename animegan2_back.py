# animegan2_back.py
import torch
import cv2
import numpy as np
import os
from animegan2_model import Generator

class AnimeGANv2Back:
    def __init__(self, model_path: str = None, device=None):
        # 1. 选择设备
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        # 2. 实例化模型并移动到设备
        self.model = Generator().to(self.device)

        # 3. 确定权重文件路径
        if model_path is None:
            model_path = os.path.join("checkpoints", "AnimeGANv2_best.pth")
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"找不到权重：{model_path}")

        # 4. 加载 checkpoint
        ckpt = torch.load(model_path, map_location=self.device)
        state_dict = ckpt.get("state_dict", ckpt)

        # 5. 统一 key 前缀、子模块名称映射：
        mapped = {}
        for k, v in state_dict.items():
            key = k.replace("module.", "")           # 去掉 DataParallel 前缀
            key = key.replace("net.", "model.")      # net. -> model.
            key = key.replace(".block", ".conv_block")  # block -> conv_block
            mapped[key] = v

        # 6. 加载权重，不严格匹配并检查缺失/多余
        missing, unexpected = self.model.load_state_dict(mapped, strict=False)
        if missing or unexpected:
            raise RuntimeError(
                f"加载权重时出现问题，缺少 keys: {missing}, 多余 keys: {unexpected}"
            )
        self.model.eval()

    def stylize_background(self, img_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        只对背景区域做风格化，并保留原图前景。
        img_bgr: 输入 BGR 图像
        mask: 单通道或三通道二值掩码（255 表示前景）
        """
        # —— 1. 生成全图风格化结果 —— 
        # BGR -> RGB
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        h, w = img_rgb.shape[:2]
        # Resize 到网络输入大小
        resized = cv2.resize(img_rgb, (256, 256), interpolation=cv2.INTER_CUBIC)

        # 转为 tensor，归一化到 [-1,1]
        inp = torch.from_numpy(resized).float().div(127.5).sub(1.0)
        inp = inp.permute(2, 0, 1).unsqueeze(0).to(self.device)

        with torch.no_grad():
            out = self.model(inp)[0].cpu()
        out_np = out.permute(1, 2, 0).numpy()
        out_np = ((out_np + 1.0) * 127.5).clip(0, 255).astype(np.uint8)
        stylized_rgb = cv2.resize(out_np, (w, h), interpolation=cv2.INTER_CUBIC)
        stylized_bgr = cv2.cvtColor(stylized_rgb, cv2.COLOR_RGB2BGR)

        # —— 2. 准备掩码 —— 
        if mask.ndim == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        _, mask_bin = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)
        inv_mask = cv2.bitwise_not(mask_bin)

        # —— 3. 合成：前景保原图，背景用 stylized —— 
        fg = cv2.bitwise_and(img_bgr, img_bgr, mask=mask_bin)
        bg = cv2.bitwise_and(stylized_bgr, stylized_bgr, mask=inv_mask)
        result = cv2.add(fg, bg)

        return result
