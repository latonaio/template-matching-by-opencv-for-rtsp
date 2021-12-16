#!/usr/bin/env python3
import asyncio
import logging
import os
from multiprocessing import Queue
import threading

from gi.repository import GLib  # isort:skip

from custom_logger import init_logger
from rabbitmq_client import RabbitmqClient

from . import streaming_matching, gst, rtsp_server, result_redis, output_for_kafka

logger = logging.getLogger(__name__)

SERVICE_NAME = os.environ.get("SERVICE", "template-matching-by-opencv-for-rtsp")
DEVICE_NAME = os.environ.get("DEVICE_NAME", "")
CAMERA_SERVICE = os.environ.get("CAMERA_SERVICE", "stream-usb-video-by-rtsp")
KAFKA_MODE = os.environ.get("KAFKA_MODE", False)

NUM_OF_MAX_DATA = 10
DEFAULT_HOST = "template-matching-by-opencv-for-rtsp"
DEFAULT_WIDTH = 864
DEFAULT_HEIGHT = 480

INIT_IMAGE_PATH = os.path.join("/var/lib/aion/Data/template-matching-by-opencv-for-rtsp", "dummy.jpg")
PROCESS_NUM = os.environ.get('PROCESS_NUM', 0)
SERVICE_NAME = SERVICE_NAME + '-' + str(PROCESS_NUM) if PROCESS_NUM != 0 else SERVICE_NAME

STREAM_URL = CAMERA_SERVICE + '-' + str(PROCESS_NUM) + '-001-srv'
IS_DEBUG = int(os.environ.get("IS_DEBUG",0))

RABBITMQ_URL = os.environ.get("RABBITMQ_URL")
QUEUE_ORIGIN = os.environ.get("QUEUE_ORIGIN")


# TODO template_imageとimageを統合
INIT_TEMPLATE_DATA = [
    {
        "template_image": {
            "path": INIT_IMAGE_PATH,
            "trim_points": [[0, 0], [355, 254]],
        },
        "image": {
            "trim_points": [[0, 0], [355, 254]],
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


async def main():
    init_logger()

    logger.info('service name: %s', SERVICE_NAME)

    client = await RabbitmqClient.create(
        RABBITMQ_URL,
        [QUEUE_ORIGIN],
        []
    )

    get_image = None
    matching = None
    rs = None
    rr = None
    ofk = None
    if IS_DEBUG==0:
        source_url = f"rtsp://{STREAM_URL}:{8554 + int(PROCESS_NUM)}/usb"
    else:
        source_url = f"rtsp://127.0.0.1:8554/test"

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
            source_url, DEFAULT_WIDTH, DEFAULT_HEIGHT, request_queue, IS_DEBUG)

        # start fitness matching
        matching = streaming_matching.MatchingFromStreamingProcess(
            request_queue, template_queue, fitness_queue, image_queue, wait_queue,
            INIT_IMAGE_PATH, INIT_TEMPLATE_DATA, INIT_TEMPLATE_TIMESTAMP, IS_DEBUG)

        server_port = DEFAULT_SERVER_PORT + int(PROCESS_NUM)
        # start rtp server
        # 結果送信用のstream
        rs = rtsp_server.GstRtspSrvProcess(
            image_queue, server_port, DEFAULT_WIDTH, DEFAULT_HEIGHT, IS_DEBUG)

        # write to redis
        rr = result_redis.RedisProcess(fitness_queue, PROCESS_NUM, kafka_queue)
        lock = threading.Lock()
        # write fitness info to kanban for kafka
        if KAFKA_MODE:
            ofk = output_for_kafka.OutputKafkaProcess(
                client, kafka_queue, SERVICE_NAME, PROCESS_NUM, lock
            )

        logger.info("start read kanban")

        # start get_kanban_itr
        # template更新処理
        async for message in client.iterator():
            async with message.process():
                logger.info("=" * 10 + 'received kanban' + "=" * 10)

                payload = message.data

                templates = payload.get('template')
                template_timestamp = payload.get('template_timestamp')

                if templates is not None and template_timestamp is not None:
                    templates = list(map(recursive_cast_to_int, templates))
                    req = streaming_matching.RequestContainer().set_template_data(templates, template_timestamp)
                    await asyncio.to_thread(template_queue.put, req)
                    result = await asyncio.to_thread(wait_queue.get, block=True, timeout=WAIT_FITNESS_TIMEOUT)
                else:
                    result = None

                if not KAFKA_MODE:
                    # TODO: RabbitMQ: 宛先 default が存在しない？
                    # await asyncio.to_thread(lock.acquire)
                    # conn.output_kanban(metadata=result, device_name=DEVICE_NAME)
                    # lock.release()
                    pass

    except Exception as e:
        logging.error(e)

    finally:
        if get_image is not None:
            await asyncio.to_thread(get_image.stop)
        if matching is not None:
            await asyncio.to_thread(matching.stop)
        if rs is not None:
            await asyncio.to_thread(rs.stop)
        if rr is not None:
            await asyncio.to_thread(rr.stop)
        if ofk is not None:
            await asyncio.to_thread(ofk.stop)

