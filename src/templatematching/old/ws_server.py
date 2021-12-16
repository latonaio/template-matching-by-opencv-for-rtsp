#!/usr/bin/env python3

from multiprocessing import Process

from aion.websocket_server import (BaseServerClass, ServerFunctionFailedException)

from src.templatematching import streaming_matching

MAX_RETRY = 100


# TODO get_kanban_itrに置き換えるのでws serverが不要
class ServerProcess:
    p = None

    def __init__(self, uri, host, port, queue, template_queue):
        self.p = Process(
            target=Server.init_server,
            args=(uri, host, port, queue, template_queue))
        self.p.start()

    def stop(self):
        if self.p is not None:
            self.p.terminate()
            self.p.join()


class Server(BaseServerClass):
    p = None
    queue = None
    template_queue = None

    @log.function_log
    async def set_templates(self, _, data):
        if self.template_queue is None:
            return ServerFunctionFailedException("template_queue is not set")
        templates = data.get("templates")

        if templates is None:
            raise ServerFunctionFailedException(
                "invalid params templates:{}".format(templates))
        req = streaming_matching.RequestContainer().set_template_data(templates)
        self.put_queue_with_retry(req, MAX_RETRY)

        return

    def put_queue_with_retry(self, request, retry_count):
        while retry_count > 0:
            if not self.template_queue.full():
                self.template_queue.put(request)
                return
            retry_count = retry_count - 1
            log.print("failed to put request to template_queue(retry left: %s)" % retry_count)
        raise ServerFunctionFailedException(
            "request template_queue is full")

    @classmethod
    def init_server(cls, uri, host, port, queue, template_queue):
        cls.queue = queue
        cls.template_queue = template_queue
        cls.register_namespace(uri, host, port)

    @classmethod
    def stop(cls):
        if cls.p is not None:
            cls.p.terminate()
            cls.p.join()
