class ImageSettings:
    def __init__(self, data):
        self.data = data
        self.path = data.get('path')
        self.trim_points = data.get('trim_points')
        self.trim_points_ratio = data.get('trim_points_ratio')
        self.new_trim_points = None

    def calc_trim_points(self, image_width, image_height):
        if self.trim_points is None:
            self.new_trim_points = [[0, 0], [image_width, image_height]]

        elif self.trim_points_ratio is None:
            self.new_trim_points = self.trim_points

        else:
            ex_width = int(image_width * self.trim_points_ratio)
            ex_height = int(image_height * self.trim_points_ratio)
            x0 = max(0, self.trim_points[0][0] - ex_width)
            y0 = max(0, self.trim_points[0][1] - ex_height)
            x1 = min(image_width, self.trim_points[1][0] + ex_width)
            y1 = min(image_height, self.trim_points[1][1] + ex_height)
            self.new_trim_points = [[x0, y0], [x1, y1]]

        return self.new_trim_points


class MatcherSettings:
    def __init__(self, template_data):
        self.template_image = ImageSettings(template_data['template_image'])
        self.image = ImageSettings(template_data['image'])
        self.metadata = template_data['metadata']
