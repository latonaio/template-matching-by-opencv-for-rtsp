#!/usr/bin/env python3
import json
import logging
from multiprocessing import Process
from os import environ

import redis

logger = logging.getLogger(__name__)

IS_DEBUG = environ.get("IS_DEBUG",0)

REDIS_HOST = environ.get('REDIS_HOST', 'redis-cluster')
REDIS_PORT = environ.get('REDIS_PORT', 6379)
REDIS_DB = environ.get('REDIS_DB', 1)
RESULT_PREFIX = 'matching'
EXPIRE = 10


class RedisProcess:
    process = None
    rtsp = None

    def __init__(self, queue, process_num, kafka_queue=None):
        self.rtsp = Redis(queue, process_num)
        self.queue = queue
        self.kafka_queue = kafka_queue

        self.process = Process(
            target=self.rtsp.loop_of_put_result,
            args=(kafka_queue,))
        self.process.start()

    def stop(self):
        logger.info("stop request to gst process from main process")
        if self.process is not None:
            self.process.terminate()
            self.process.join()
        self.queue.put(None)


class Redis:
    queue = None

    def __init__(self, queue, process_num):
        self.queue = queue
        self.process_num = process_num
        self.kafka_queue = None

    def loop_of_put_result(self, kafka_queue=None):
        self.kafka_queue = kafka_queue
        with redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB) as connection:
            while True:
                result = self.queue.get()

                if result is None:
                    return

                if environ.get('MATCHING_RESULT_MODE') == 'LATEST':
                    # 旧バージョンとの互換性保持のため
                    name = 'matching-result:%s' % self.process_num

                    connection.set(name=name, value=str(result))
                    connection.expire(name, EXPIRE)
                    if self.kafka_queue is not None:
                        self.kafka_queue.put(result)
                else:
                    for key, val in result.items():
                        if key == "fitness":
                            val = json.dumps(val)
                        result[key] = str(val)

                    redis_key = '%s:%s:%s' % (RESULT_PREFIX, self.process_num, result.get('timestamp'))

                    connection.hmset(redis_key, result)
                    connection.expire(redis_key, EXPIRE)
                    if self.kafka_queue is not None:
                        self.kafka_queue.put(result)
                    redis_key_list_key = 'key-list:%s' % self.process_num

                    # set key_list
                    connection.zadd(redis_key_list_key, {redis_key: result.get('unix_time')})

                    # logger.info('set results to %s' % redis_key)
