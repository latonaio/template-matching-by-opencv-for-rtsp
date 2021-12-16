#!/usr/bin/env python3
from datetime import datetime
from enum import Enum, auto
import logging
from multiprocessing import Process

from .template_matching.matcher import Matcher

logger = logging.getLogger(__name__)


class RequestType(Enum):
    Array = auto()
    Template = auto()
    WaitFitness = auto()


class RequestContainer:
    def __init__(self):
        self.type = None
        self.templates = None
        self.template_timestamp = None
        self.array = None

        d = datetime.now()
        self.timestamp = d.isoformat()
        self.unix_time = int(round(d.timestamp() * 1000))

    def set_template_data(self, templates, template_timestamp):
        self.type = RequestType.Template
        self.templates = templates
        self.template_timestamp = template_timestamp
        return self

    def set_array_data(self, array):
        self.type = RequestType.Array
        self.array = array
        return self


class MatchingFromStreamingProcess:
    def __init__(self, input_queue, template_queue, fitness_out_q, image_out_q, wait_q,
                 init_image_path, init_template_data, init_template_timestamp,IS_DEBUG):
        self.fitness_out_q = fitness_out_q
        self.template_queue = template_queue
        self.image_out_q = image_out_q
        self.wait_q = wait_q
        self.process = None
        self.IS_DEBUG=IS_DEBUG

        ms = MatchingFromStreaming(init_image_path, init_template_data, init_template_timestamp,IS_DEBUG)
        self.process = Process(
            target=ms.convert_loop,
            args=(input_queue, template_queue, fitness_out_q, image_out_q, wait_q))
        self.process.start()

    def stop(self):
        if self.process is not None:
            self.process.terminate()
            self.process.join()
        if self.fitness_out_q is not None:
            self.fitness_out_q.put(None)
        if self.image_out_q is not None:
            self.image_out_q.put(None)


class MatchingFromStreaming:
    def __init__(self, init_image_path, init_template_data, init_template_timestamp,IS_DEBUG):
        self.input_q = None
        self.template_q = None
        self.fitness_out_q = None
        self.image_out_q = None
        self.wait_q = None
        self.init_image_path = init_image_path
        self.init_template_data = init_template_data
        self.init_template_timestamp = init_template_timestamp
        self.matcher = None
        self.wait_timestamp = None
        self.IS_DEBUG=IS_DEBUG

    def stop(self):
        if self.fitness_out_q is not None:
            self.fitness_out_q.put(None)
        if self.image_out_q is not None:
            self.image_out_q.put(None)

    def convert_loop(self, input_q, template_q, fitness_out_q, image_out_q, wait_q):
        self.input_q = input_q
        self.template_q = template_q
        self.fitness_out_q = fitness_out_q
        self.image_out_q = image_out_q
        self.wait_q = wait_q
        self.matcher = Matcher(self.init_template_data, self.init_image_path, self.init_template_timestamp,self.IS_DEBUG)

        while True:
            if not self.template_q.empty():
                rcv = self.template_q.get()
            else:
                rcv = self.input_q.get()

            if rcv is None:
                logger.info("[MatchingFromStreaming] get stop request")
                self.image_out_q.put(None)
                self.fitness_out_q.put(None)
                break
            if not isinstance(rcv, RequestContainer):
                continue

            rtype = rcv.type

            # branch of function
            # if get array from rtsp
            if rtype == RequestType.Array:
                fitness, image, template_timestamp = self.get_multiple_fitness(rcv.array)
                if fitness is not None:
                    output = {
                        "fitness": fitness,
                        "timestamp": rcv.timestamp,
                        "unix_time": rcv.unix_time,
                        "template_timestamp": template_timestamp,
                    }
                    self.fitness_out_q.put(output)

                    if self.wait_timestamp is not None and template_timestamp is not None:
                        if self.wait_timestamp == template_timestamp:
                            if not self.wait_q.empty():
                                self.wait_q.get_nowait()  # queueを空にする

                            self.wait_q.put(output)
                            self.unset_wait_timestamp()
                if image is not None:
                    self.image_out_q.put(image)

            # get new template data
            elif rtype == RequestType.Template:
                self.set_templates(rcv.templates, rcv.template_timestamp)
                self.set_wait_timestamp(rcv.template_timestamp)

    def get_multiple_fitness(self, array):
        res, res_array, timestamp = self.matcher.get_multiple_fitness(array)

        if res:
            pass
            # logger.info('get fitness is success: %d', 1)
        else:
            res = res_array = None
            logger.info("get fitness is failed: %d", 1)
        return res, res_array, timestamp

    def set_templates(self, templates, template_timestamp):
        res = self.matcher.set_templates(templates, template_timestamp)
        if not res:
            logger.info("set template is failed: %d", 1)
        else:
            logger.info("set template is success")
        return

    def set_wait_timestamp(self, timestamp):
        self.wait_timestamp = timestamp

    def unset_wait_timestamp(self):
        self.wait_timestamp = None
