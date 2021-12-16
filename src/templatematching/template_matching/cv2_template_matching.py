import logging

import cv2

logger = logging.getLogger(__name__)


class OpencvTemplateMatching():
    def __init__(self):
        assert cv2.cuda.getCudaEnabledDeviceCount()

        self.cv2_template_matching = cv2.cuda.createTemplateMatching(cv2.CV_8UC1, cv2.TM_CCOEFF_NORMED)

    def run(self, gpu_mat, template_gpu_mat):
        res = self.cv2_template_matching.match(gpu_mat, template_gpu_mat)
        res_download = res.download()
        _, val, _, loc = cv2.minMaxLoc(res_download)
        return val, loc


class OpencvTemplateMatchingOnCPU():
    def run(self, image, template_image):
        res = cv2.matchTemplate(image, template_image, cv2.TM_CCOEFF_NORMED)
        _, val, _, loc = cv2.minMaxLoc(res)
        return val, loc


def initialize_cv2_template_matching():
    if cv2.cuda.getCudaEnabledDeviceCount():
        return OpencvTemplateMatching()

    logger.warning('cannot use cuda, fallback to OpencvTemplateMatchingOnCPU')
    return OpencvTemplateMatchingOnCPU()
