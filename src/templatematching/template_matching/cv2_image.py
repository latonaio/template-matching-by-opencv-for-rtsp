from pathlib import Path

import cv2
import numpy as np
from aion.logger import lprint

from .errors import TemplateMatchingException


class OpenCVImage:
    def __init__(self):
        self.color_img = None
        self.width = None
        self.height = None
        self.trim_image = None

    def set_image(self, image):
        # ストリーミングから取り込む場合
        self.color_img = image
        self.height, self.width, _ = self.color_img.shape
        return

    def load_image(self, image_path):
        # 画像をファイルから読み込む場合
        path = Path(image_path)

        if not path.exists():
            lprint(f"{image_path} does not exists")
            raise FileNotFoundError(f"{image_path} does not exists")

        if path.suffix == ".npy":
            color_img = np.load(str(image_path))
        elif path.suffix == ".jpg":
            color_img = cv2.imread(str(image_path))
        else:
            lprint(f"{image_path} does not load as image")
            raise TemplateMatchingException(f"{image_path} does not load as image")

        self.color_img = color_img
        self.height, self.width, _ = self.color_img.shape

        return color_img

    def set_trim_image(self, trim):
        assert (
                trim[0][0] <= trim[1][0]
                and trim[0][1] <= trim[1][1]
                and trim[0][0] < self.color_img.shape[1]
                and trim[1][0] <= self.color_img.shape[1]
                and trim[0][1] < self.color_img.shape[0]
                and trim[1][1] <= self.color_img.shape[0]
        )

        self.trim_image = self.color_img[trim[0][1]:trim[1][1], trim[0][0]:trim[1][0]]
        self.trim_image_height, self.trim_image_width, _ = self.trim_image.shape
        return


class OpenCVImageInCuda(OpenCVImage):
    def __init__(self):
        super().__init__()
        self.gpu_mat = cv2.cuda_GpuMat()

    def setup_for_template_matching(self):
        self.gpu_mat.upload(self.trim_image)
        self.gpu_mat = cv2.cuda.cvtColor(self.gpu_mat, cv2.COLOR_RGB2GRAY)
        return


def initialize_cv2_image():
    assert cv2.cuda.getCudaEnabledDeviceCount()
    return OpenCVImageInCuda()


if __name__ == "__main__":
    cv2_img = initialize_cv2_image()

    trim = [[400, 100], [1680, 820]]
    gpu_mat = cv2_img.setup_image(trim)
    print(gpu_mat.download().shape)
