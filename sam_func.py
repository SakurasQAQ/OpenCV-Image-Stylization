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
        #model_type = "vit_b"


        checkpoint_dir = os.path.join(os.getcwd(), "checkpoints")
        os.makedirs(checkpoint_dir, exist_ok=True)
        checkpoint_path = os.path.join(checkpoint_dir, "sam_vit_b_01ec64.pth")


        if not os.path.exists(checkpoint_path):
            url = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
            print(f"Downloading model to {checkpoint_path} ...")
            torch.hub.download_url_to_file(url, checkpoint_path)
            print("Download complete.")

        self.model = sam_model_registry[model_type](checkpoint=None)
        state_dict = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.predictor = SamPredictor(self.model)
    

    def load_image(self, image_path):
        image = cv2.imread(image_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        self.original_image = image.copy()
        self.original_size = (image.shape[1], image.shape[0])

        self.predictor.set_image(image)
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


    def segment_with_box_and_points(self, box, points=None, labels=None, multimask=True):

        box_np = np.array([box]) 

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
        h, w = self.original_image.shape[:2]
        mask_rs = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
        alpha = (mask_rs * 255).astype(np.uint8)
        rgba = np.dstack((self.original_image, alpha))
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        Image.fromarray(rgba).save(save_path)
        return save_path



    def export_foreground_black_bg(self, mask, save_path="output/foreground_black.jpg"):
        h, w = self.original_image.shape[:2]
        mask_rs = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
        mask_bool = mask_rs.astype(bool)
        fg = self.original_image.copy()
        fg[~mask_bool] = 0
        bgr = cv2.cvtColor(fg, cv2.COLOR_RGB2BGR)
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
            h, w = self.original_image.shape[:2]
            resized_mask = cv2.resize(
                mask.astype(np.uint8),
                (w, h),
                interpolation=cv2.INTER_NEAREST
            )
            alpha = (resized_mask * 255).astype(np.uint8)


            mask_path = os.path.join(base_path, f"{prefix}_{i}_mask.png")
            cv2.imwrite(mask_path, alpha)
            saved_paths.append(mask_path)

            rgba = np.dstack((self.original_image, alpha))
            rgba_path = os.path.join(base_path, f"{prefix}_{i}.png")
            os.makedirs(os.path.dirname(rgba_path), exist_ok=True)
            Image.fromarray(rgba).save(rgba_path)
            saved_paths.append(rgba_path)

        return saved_paths

    
