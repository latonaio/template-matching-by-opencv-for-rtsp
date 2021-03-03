#!/usr/bin/env python3

import threading
from aion.microservice import main_decorator, Options
from aion.logger import lprint
from . import core

SERVICE_NAME = None


class OutputKafkaProcess:
    queue = None
    process = None
    lock = None

    def __init__(self, kanban_con, queue, service_name, process_num, lock):
        self.queue = queue
        self.kanban_con = kanban_con
        self.service_name = service_name
        self.process_num = process_num
        self.lock = lock
        self.thread = threading.Thread(
            target=loop_of_put_result_to_kanban,
            args=(kanban_con, queue, service_name, process_num, lock)
        )
        self.thread.start()

    def stop(self):
        lprint("stop output to kanban for kafka process from main process")
        if self.thread is not None:
            self.thread.join()
        self.queue.put(None)


def loop_of_put_result_to_kanban(kanban_con, queue, service_name, process_num, lock):
    while True:
        result = queue.get()
        if result is None:
            return
        lprint("\n got result by every frame \n")
        lprint(result)
        lock.acquire()
        kanban_con.output_kanban(
            process_number=process_num,
            connection_key="kafka",
            result=True,
            metadata={
                "topic": "template-matching",
                "key": service_name + ":" + str(process_num),
                "content": result
            })
        lock.release()
