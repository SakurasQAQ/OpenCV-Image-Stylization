# sam_func.py
#SAM image segmentation method

import torch
import numpy as np
import cv2
from segment_anything import sam_model_registry, SamPredictor
from PIL import Image
import os

from torch.hub import load_state_dict_from_url


class SAMSegmentor:
    def __init__(self, model_type="vit_b", device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        model_type = "vit_b"

        # 自定义保存目录
        checkpoint_dir = os.path.join(os.getcwd(), "checkpoints")
        os.makedirs(checkpoint_dir, exist_ok=True)
        checkpoint_path = os.path.join(checkpoint_dir, "sam_vit_b_01ec64.pth")

        # 如果本地不存在则下载
        if not os.path.exists(checkpoint_path):
            url = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
            print(f"Downloading model to {checkpoint_path} ...")
            torch.hub.download_url_to_file(url, checkpoint_path)
            print("Download complete.")

        # 加载模型
        self.model = sam_model_registry[model_type](checkpoint=None)
        state_dict = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)

        # 初始化 Predictor
        self.predictor = SamPredictor(self.model)
    

    def load_image(self, image_path):
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Can not load image: {image_path}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # 保留原始图像尺寸和图像内容
        self.original_size = (image.shape[1], image.shape[0])  # (width, height)
        self.original_image = image.copy()  # << 这是关键

        # Resize to 1024x1024 for SAM
        image_resized = cv2.resize(image, (1024, 1024), interpolation=cv2.INTER_LINEAR)
        self.predictor.set_image(image_resized)

        self.image = image_resized  # 给 SAM 用的图像
        return image_resized

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


    def segment_with_box_and_points(self, box, points=None, labels=None, multimask=True):

        box_np = np.array([box])  # SAM 需要 batch 形式

        kwargs = {
            "box": box_np,
            "multimask_output": multimask
        }

        if points is not None and labels is not None and len(points) > 0:
            kwargs["point_coords"] = np.array(points)
            kwargs["point_labels"] = np.array(labels)

        masks, scores, logits = self.predictor.predict(**kwargs)
        return masks, scores


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
        if not hasattr(self, 'original_image'):
            raise RuntimeError("please first call load_image()")

        os.makedirs(base_path, exist_ok=True)
        saved_paths = []

        for i, mask in enumerate(masks):
            # Resize mask to original image size
            resized_mask = cv2.resize(mask.astype(np.uint8), self.original_image.shape[1::-1], interpolation=cv2.INTER_NEAREST)
            alpha = (resized_mask * 255).astype(np.uint8)

            # Ensure shapes match
            assert alpha.shape[:2] == self.original_image.shape[:2]

            # Combine with original image
            rgba = np.dstack((self.original_image, alpha))

            save_path = os.path.join(base_path, f"{prefix}_{i}.png")
            Image.fromarray(rgba).save(save_path)
            saved_paths.append(save_path)


            # get background part
            inverted = 1 - resized_mask  
            alpha_inv = (inverted * 255).astype(np.uint8)
            rgba_inv = np.dstack((self.original_image, alpha_inv))
            inv_path = os.path.join(base_path, f"{prefix}_{i}_inverted.png")
            Image.fromarray(rgba_inv).save(inv_path)
            saved_paths.append(inv_path)

        return saved_paths
