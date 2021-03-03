#!/usr/bin/env python3
import os
from multiprocessing import Queue
import threading
from aion.logger import lprint, initialize_logger
from aion.microservice import main_decorator, Options
from gi.repository import GLib  # isort:skip

from . import streaming_matching, gst, rtsp_server, result_redis, output_for_kafka

SERVICE_NAME = os.environ.get("SERVICE", "template-matching-by-opencv-for-rtsp")
DEVICE_NAME = os.environ.get("DEVICE_NAME", "")
CAMERA_SERVICE = os.environ.get("CAMERA_SERVICE", "stream-usb-video-by-rtsp")
KAFKA_MODE = os.environ.get("KAFKA_MODE", False)
initialize_logger(SERVICE_NAME)

NUM_OF_MAX_DATA = 10
DEFAULT_HOST = "template-matching-by-opencv-for-rtsp"
DEFAULT_WIDTH = 864
DEFAULT_HEIGHT = 480

INIT_IMAGE_PATH = os.path.join("/var/lib/aion/Data/template-matching-by-opencv-for-rtsp", "dummy.jpg")
PROCESS_NUM = os.environ.get('PROCESS_NUM', 0)
SERVICE_NAME = SERVICE_NAME + '-' + str(PROCESS_NUM) if PROCESS_NUM != 0 else SERVICE_NAME
lprint(SERVICE_NAME)

STREAM_URL = CAMERA_SERVICE + '-' + str(PROCESS_NUM) + '-001-srv'

# TODO template_imageとimageを統合
INIT_TEMPLATE_DATA = [
    {
        "template_image": {
            "path": INIT_IMAGE_PATH,
            "trim_points": [[175, 83], [355, 254]],
        },
        "image": {
            "trim_points": [[175, 83], [355, 254]],
            "trim_points_ratio": 0.02,
        },
        "metadata": {
            "template_id": 1,
            "work_id": 1,
            "pass_threshold": 0.8,
        }
    },
]

INIT_TEMPLATE_TIMESTAMP = 0.0

QUEUE_LIMIT = 10
TEMPLATE_QUEUE_LIMIT = 10

# テンプレートマッチングの結果をコンテナないでストリーミングするポート番号
DEFAULT_SERVER_PORT = 4999

# テンプレートをセットしてから結果取得までの最大待ち時間
WAIT_FITNESS_TIMEOUT = 30

loop = GLib.MainLoop()


def recursive_cast_to_int(template):
    template['template_image']['trim_points'] = cast_trim_points_to_int(
        template.get('template_image').get('trim_points'))

    template['image']['trim_points'] = cast_trim_points_to_int(
        template.get('image').get('trim_points'))

    return template


def cast_trim_points_to_int(trim_points):
    return [
        [
            int(trim_points[0][0]),
            int(trim_points[0][1]),
        ],
        [
            int(trim_points[1][0]),
            int(trim_points[1][1]),
        ]
    ]


@main_decorator(SERVICE_NAME)
def main(opt: Options):
    # get cache kanban
    conn = opt.get_conn()
    num = opt.get_number()

    get_image = None
    matching = None
    rs = None
    rr = None
    ofk = None

    source_url = f"rtsp://{STREAM_URL}:{8554 + int(PROCESS_NUM)}/usb"

    try:
        # TODO request_queue->image_queue template_queue->request_queue
        request_queue = Queue(maxsize=QUEUE_LIMIT)
        template_queue = Queue(maxsize=TEMPLATE_QUEUE_LIMIT)
        image_queue = Queue()
        fitness_queue = Queue()
        wait_queue = Queue(maxsize=1)
        kafka_queue = None
        if KAFKA_MODE:
            kafka_queue = Queue()

        # start to get image from rtsp
        # 元データ取得用のstream
        get_image = gst.GstRtspProcess(
            source_url, DEFAULT_WIDTH, DEFAULT_HEIGHT, request_queue)

        # start fitness matching
        matching = streaming_matching.MatchingFromStreamingProcess(
            request_queue, template_queue, fitness_queue, image_queue, wait_queue,
            INIT_IMAGE_PATH, INIT_TEMPLATE_DATA, INIT_TEMPLATE_TIMESTAMP)

        server_port = DEFAULT_SERVER_PORT + int(PROCESS_NUM)
        # start rtp server
        # 結果送信用のstream
        rs = rtsp_server.GstRtspSrvProcess(
            image_queue, server_port, DEFAULT_WIDTH, DEFAULT_HEIGHT)

        # write to redis
        rr = result_redis.RedisProcess(fitness_queue, PROCESS_NUM, kafka_queue)

        lock = threading.Lock()
        # write fitness info to kanban for kafka
        if KAFKA_MODE:
            ofk = output_for_kafka.OutputKafkaProcess(
                conn, kafka_queue, SERVICE_NAME, PROCESS_NUM, lock
            )

        lprint("start read kanban")
        # start get_kanban_itr
        # template更新処理
        for kanban in conn.get_kanban_itr(SERVICE_NAME, num):
            lprint("=" * 10 + 'received kanban' + "=" * 10)

            metadata = kanban.get_metadata()

            connection_key = kanban.get_connection_key()
            if connection_key == f'template-{PROCESS_NUM}':
                templates = metadata.get('template')
                template_timestamp = metadata.get('template_timestamp')

                if templates is not None and template_timestamp is not None:
                    templates = list(map(recursive_cast_to_int, templates))
                    req = streaming_matching.RequestContainer().set_template_data(templates, template_timestamp)
                    template_queue.put(req)
                    result = wait_queue.get(block=True, timeout=WAIT_FITNESS_TIMEOUT)
                else:
                    result = None

                if not KAFKA_MODE:
                    lock.acquire()
                    conn.output_kanban(metadata=result, device_name=DEVICE_NAME)
                    lock.release()
    except Exception as e:
        lprint(e)

    finally:
        if get_image is not None:
            get_image.stop()
        if matching is not None:
            matching.stop()
        if rs is not None:
            rs.stop()
        if rr is not None:
            rr.stop()
        if ofk is not None:
            ofk.stop()
