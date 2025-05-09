# sam_func.py
# SAM image segmentation method

import torch
import numpy as np
import cv2
from segment_anything import sam_model_registry, SamPredictor
from PIL import Image
import os


class SAMSegmentor:
    def __init__(self,
                 model_type="vit_b",
                 checkpoint_path="resource/sam_vit_b_01ec64.pth",
                 device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = sam_model_registry[model_type](checkpoint=checkpoint_path)
        self.model.to(self.device)
        self.predictor = SamPredictor(self.model)

    def load_image(self, image_path):
        # load & set image
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Can not load image: {image_path}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.predictor.set_image(image)
        self.image = image
        return image

    def segment_with_points(self, points, labels, multimask=True):
        """
        get points and labels
        :param points: [[x1, y1], [x2, y2], ...]
        :param labels: [1, 0, ...]  # 1=front, 0=back
        :return: best mask, all scores
        """
        input_points = np.array(points)
        input_labels = np.array(labels)

        masks, scores, logits = self.predictor.predict(
            point_coords=input_points,
            point_labels=input_labels,
            multimask_output=multimask
        )
        best_idx = scores.argmax()
        return masks[best_idx], scores

    def export_foreground_with_alpha(self, mask, save_path="output/foreground.png"):
        # Apply the mask to the original image and save it as a PNG with a transparent channel
        if not hasattr(self, 'image'):
            raise RuntimeError("please first call load_image()")

        # use png to aoviding 
        if not save_path.lower().endswith(".png"):
            save_path = os.path.splitext(save_path)[0] + ".png"

        alpha = (mask * 255).astype(np.uint8)
        rgba = np.dstack((self.image, alpha))
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        Image.fromarray(rgba).save(save_path)
        return save_path




    def export_foreground_black_bg(self, mask, save_path="output/foreground_black.jpg"):
        # Set the non-mask area to black and save
        foreground = self.image.copy()
        foreground[~mask] = 0
        bgr = cv2.cvtColor(foreground, cv2.COLOR_RGB2BGR)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        cv2.imwrite(save_path, bgr)
        return save_path



    def segment_all_masks(self, points, labels, multimask=True):
        """
        :param points: [[x1, y1], [x2, y2], ...]
        :param labels: [1, 0, ...]
        :return: masks, scores
        """
        input_points = np.array(points)
        input_labels = np.array(labels)

        masks, scores, logits = self.predictor.predict(
            point_coords=input_points,
            point_labels=input_labels,
            multimask_output=multimask
        )
        return masks, scores



    def export_multiple_masks(self, masks, base_path="output", prefix="result"):
        """
        将多个 mask 导出为透明前景图像：base_path/prefix_0.png, prefix_1.png, ...
        :param masks: List of masks
        :return: List of saved file paths
        """
        if not hasattr(self, 'image'):
            raise RuntimeError("please first call load_image()")

        os.makedirs(base_path, exist_ok=True)
        saved_paths = []

        for i, mask in enumerate(masks):
            alpha = (mask * 255).astype(np.uint8)
            rgba = np.dstack((self.image, alpha))
            save_path = os.path.join(base_path, f"{prefix}_{i}.png")
            Image.fromarray(rgba).save(save_path)
            saved_paths.append(save_path)

        return saved_paths

