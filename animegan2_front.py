# animegan2_front.py
import torch
import cv2
import numpy as np
import os

from animegan2_model import Generator

class AnimeGANv2Front:
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
            # 去掉可能的 DataParallel 前缀
            key = k.replace("module.", "")
            # net. -> model.
            key = key.replace("net.", "model.")
            # block -> conv_block（针对那些 block 层）
            key = key.replace(".block", ".conv_block")
            mapped[key] = v

        # 6. 加载到模型
        missing, unexpected = self.model.load_state_dict(mapped, strict=False)
        if missing or unexpected:
            raise RuntimeError(
                f"加载权重时出现问题，缺少 keys: {missing}, 多余 keys: {unexpected}"
            )

        self.model.eval()

    def stylize_foreground(self, img_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        # 确保 mask 是单通道二值
        if mask.ndim == 3:
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
        _, mask_bin = cv2.threshold(mask, 128, 255, cv2.THRESH_BINARY)

        # 裁切前景并转 RGB
        fg = cv2.bitwise_and(img_bgr, img_bgr, mask=mask_bin)
        fg_rgb = cv2.cvtColor(fg, cv2.COLOR_BGR2RGB)
        h, w = fg_rgb.shape[:2]
        # Resize 到训练时的输入尺寸
        fg_resized = cv2.resize(fg_rgb, (256, 256), interpolation=cv2.INTER_CUBIC)

        # 转 tensor，归一化到 [-1,1]
        inp = torch.from_numpy(fg_resized).float().div(127.5).sub(1.0)
        inp = inp.permute(2, 0, 1).unsqueeze(0).to(self.device)

        # 推理
        with torch.no_grad():
            out = self.model(inp)[0].cpu()

        # 恢复到图像
        out_np = out.permute(1, 2, 0).numpy()
        out_np = ((out_np + 1.0) * 127.5).clip(0, 255).astype(np.uint8)
        stylized_rgb = cv2.resize(out_np, (w, h), interpolation=cv2.INTER_CUBIC)
        stylized_bgr = cv2.cvtColor(stylized_rgb, cv2.COLOR_RGB2BGR)

        # 拼回原图
        inv_mask = cv2.bitwise_not(mask_bin)
        background = cv2.bitwise_and(img_bgr, img_bgr, mask=inv_mask)
        return cv2.add(background, stylized_bgr)
