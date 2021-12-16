#!/usr/bin/env python3

import asyncio
import logging
import threading
from . import core

logger = logging.getLogger(__name__)

SERVICE_NAME = None

class OutputKafkaProcess:
    queue = None
    process = None
    lock = None

    def __init__(self, client, queue, service_name, process_num, lock):
        self.queue = queue
        self.client = client
        self.service_name = service_name
        self.process_num = process_num
        self.lock = lock
        self.thread = threading.Thread(
            target=loop_of_put_result_to_kanban,
            args=(client, queue, service_name, process_num, lock)
        )
        self.thread.start()

    def stop(self):
        logger.info("stop output to kanban for kafka process from main process")
        if self.thread is not None:
            self.thread.join()
        self.queue.put(None)


def loop_of_put_result_to_kanban(*args, **kwargs):
    asyncio.run(loop_of_put_result_to_kanban_impl(*args, **kwargs))


async def loop_of_put_result_to_kanban_impl(client, queue, service_name, process_num, lock):
    while True:
        result = await asyncio.to_thread(queue.get)
        if result is None:
            return
        logger.info("\n got result by every frame \n")
        logger.info("%s", result)
        await asyncio.to_thread(lock.acquire)
        # TODO: RabbitMQ: kafka のキュー名
        await client.send('kafka', {
            "topic": "template-matching",
            "key": service_name + ":" + str(process_num),
            "content": result
        })
        lock.release()
