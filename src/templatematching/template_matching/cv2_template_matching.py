import cv2


class OpencvTemplateMatching():
    def __init__(self):
        assert cv2.cuda.getCudaEnabledDeviceCount()

        self.cv2_template_matching = cv2.cuda.createTemplateMatching(cv2.CV_8UC1, cv2.TM_CCOEFF_NORMED)

    def run(self, gpu_mat, template_gpu_mat):
        res = self.cv2_template_matching.match(gpu_mat, template_gpu_mat)
        res_download = res.download()
        _, val, _, loc = cv2.minMaxLoc(res_download)
        return val, loc
