import logging

from .cv2_image import initialize_cv2_image
from .cv2_template_matching import initialize_cv2_template_matching
from .errors import TemplateMatchingException
from .image_utils import draw
from .matcher_settings import MatcherSettings
from os import environ

logger = logging.getLogger(__name__)


class Template:
    def __init__(self, template_data,IS_DEBUG):
        self.IS_DEBUG = IS_DEBUG
        self.cv2_img = initialize_cv2_image()
        self.settings = None
        self.set_template(template_data)

    def set_template(self, template_data):
        self.settings = MatcherSettings(template_data)

        self.cv2_img.load_image(self.settings.template_image.path)

        width, height = self.cv2_img.width, self.cv2_img.height
        trim_points = self.settings.template_image.calc_trim_points(width, height)
        self.cv2_img.set_trim_image(trim=trim_points)

        self.cv2_img.setup_for_template_matching()
        return


def get_img_with_fitness(results, image):
    for result in results:
        if result['matching_rate'] > result['pass_threshold']:
            color = draw.BLUE
        else:
            color = draw.RED
        draw.rectangle(image, result['matching_points'], color)
        text = f"{result['matching_rate']:.5f}"
        draw.text(image, text, result['matching_points'], color)

    return image


class Matcher:
    def __init__(self, templates, image_path, template_timestamp,IS_DEBUG):
        self.IS_DEBUG=IS_DEBUG
        self.cv2_img = initialize_cv2_image()
        self.cv2_temp_match = initialize_cv2_template_matching()

        self.templates = []
        self.template_timestamp = None
        self.set_templates(templates, template_timestamp)

        self._load_image(image_path)
        for template in self.templates:
            self._set_trim_image(template)

    def set_templates(self, templates, template_timestamp):
        new_templates = []
        self.templates = []
        self.template_timestamp = None

        try:
            for template_data in templates:
                logger.info(templates)
                template = Template(template_data,self.IS_DEBUG)
                new_templates.append(template)
        except Exception as e:
            logger.info('Template().set_templates() is faild.')
            raise e

        del self.templates
        self.templates = new_templates
        self.template_timestamp = template_timestamp
        return True

    def _set_trim_image(self, template):
        # 検出対象範囲に合わせてトリミングする
        width, height = self.cv2_img.width, self.cv2_img.height
        trim_points = template.settings.image.calc_trim_points(width, height)
        self.cv2_img.set_trim_image(trim=trim_points)

        self.cv2_img.setup_for_template_matching()
        return

    def _set_image(self, image):
        self.cv2_img.set_image(image)
        return

    def _load_image(self, image_path):
        self.cv2_img.load_image(image_path)
        return

    def _validate_image_size(self, template):
        # Assert that template image size is not larger than image size
        ti_height, ti_width = template.cv2_img.trim_image_height, template.cv2_img.trim_image_width
        i_height, i_width = self.cv2_img.trim_image_height, self.cv2_img.trim_image_width
        if ti_height > i_height or ti_width > i_width:
            msg = f"""
            Template image size is larger than image.
            Template image shape is {(ti_width, ti_height)}.
            Image shape is {(i_width, i_height)}.
            """
            logger.info(msg)
            raise TemplateMatchingException(msg)
        return

    def _run_template_matching(self, template):
        # trim_xy is coordinate on trimming image
        matching_rate, trim_xy = self.cv2_temp_match.run(self.cv2_img.gpu_mat, template.cv2_img.gpu_mat)

        x = template.settings.image.new_trim_points[0][0] + trim_xy[0]
        y = template.settings.image.new_trim_points[0][1] + trim_xy[1]
        w = template.cv2_img.trim_image_width
        h = template.cv2_img.trim_image_height
        return matching_rate, (x, y, w, h)

    def get_multiple_fitness(self, image):
        if not self.templates:
            TemplateMatchingException('There are no templates because Template().set_templates() was faild.')

        results = []
        self._set_image(image)

        for template in self.templates:
            self._set_trim_image(template)
            self._validate_image_size(template)
            matching_rate, (x, y, w, h) = self._run_template_matching(template)

            result = {
                'matching_rate': matching_rate,
                'matching_points': {'x': x, 'y': y, 'w': w, 'h': h},
                'is_pass': matching_rate >= template.settings.metadata.get('pass_threshold'),
            }

            for key, value in template.settings.metadata.items():
                # TODO intへキャストする条件を考慮
                if key.endswith('_id') or key.endswith('_index'):
                    result[key] = int(value)
                else:
                    result[key] = value

            results.append(result)

        # print(results)
        result_image = get_img_with_fitness(results, image)

        return results, result_image, self.template_timestamp


if __name__ == "__main__":
    from pprint import pprint

    templates_data = [
        {
            "template_image": {
                "path": "file/data/Example_Full_HD.jpg",
                "trim_points": [[400, 100], [1680, 820]]
            },
            "image": {
                "trim_points": [[390, 90], [1690, 830]],
                "trim_points_ratio": 0.5
            },
            "metadata": {
                "template_id": 1,
                "work_id": 1
            }
        },
        {
            "template_image": {
                "path": "file/data/Example_Full_HD.jpg",
                "trim_points": [[300, 0], [1580, 720]]
            },
            "image": {
                "trim_points": [[400, 100], [1680, 820]],
                "trim_points_ratio": 0.5
            },
            "metadata": {
                "template_id": 2,
                "work_id": 2
            }
        }
    ]

    image_path = 'file/data/Example_Full_HD.jpg'
    matcher = Matcher(templates_data, image_path)
    matcher.set_templates(templates_data)
    matching_data = matcher.run(image_path)
    pprint(matching_data)
