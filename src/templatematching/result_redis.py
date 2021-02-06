#!/usr/bin/env python3
from multiprocessing import Process
from os import environ
import redis
from aion.logger import lprint

import json

REDIS_HOST = environ.get('REDIS_HOST', 'redis-cluster')
REDIS_PORT = environ.get('REDIS_PORT', 6379)
REDIS_DB = environ.get('REDIS_DB', 1)
RESULT_PREFIX = 'matching'
EXPIRE = 10


class RedisProcess:
    process = None
    rtsp = None

    def __init__(self, queue, process_num):
        self.rtsp = Redis(queue, process_num)
        self.queue = queue

        self.process = Process(
            target=self.rtsp.loop_of_put_result,
            args=())
        self.process.start()

    def stop(self):
        lprint("stop request to gst process from main process")
        if self.process is not None:
            self.process.terminate()
            self.process.join()
        self.queue.put(None)


class Redis:
    queue = None

    def __init__(self, queue, process_num):
        self.queue = queue
        self.process_num = process_num

    def loop_of_put_result(self):
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
                else:
                    for key, val in result.items():
                        if key == "fitness":
                            val = json.dumps(val)
                        result[key] = str(val)

                    redis_key = '%s:%s:%s' % (RESULT_PREFIX, self.process_num, result.get('timestamp'))

                    connection.hmset(redis_key, result)
                    connection.expire(redis_key, EXPIRE)

                    redis_key_list_key = 'key-list:%s' % self.process_num

                    # set key_list
                    connection.zadd(redis_key_list_key, {redis_key: result.get('unix_time')})

                    lprint('set results to %s' % redis_key)
