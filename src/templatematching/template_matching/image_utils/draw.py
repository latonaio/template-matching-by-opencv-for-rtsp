import cv2

BLUE = (255, 0, 0)
RED = (0, 0, 255)


def rectangle(image, points, color):
    x1 = points['x'] + points['w']
    y1 = points['y'] + points['h']
    cv2.rectangle(
        image,
        (points['x'], points['y']),
        (x1, y1),
        color,
        2)
    return image


def text(image, text, points, color):
    cv2.putText(
        image,
        text,
        (points['x'], points['y']),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        3,
        cv2.LINE_AA
    )
    return image
