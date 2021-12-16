#!/usr/bin/env python3
from datetime import datetime
import logging
from multiprocessing import Process
from time import sleep

import gi
import numpy as np

from . import streaming_matching

gi.require_version('Gst', '1.0')  # noqa
from gi.repository import Gst, GLib  # isort:skip

# initialize gstreamer library
Gst.init(None)
# Gst.debug_set_active(True)
# Gst.debug_set_default_threshold(4)

logger = logging.getLogger(__name__)


# connection retry interval (sec)
retry_interval = 1

def get_now_datetime_string():
    return datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]

def get_pipe(source_url, width, height):
    gst_query = f"""
        rtspsrc location={source_url} name=rtsp latency=0 !
        application/x-rtp, encoding-name=JPEG,payload=96 ! queue name=q !
        rtpjpegdepay ! nvjpegdec ! video/x-raw ! nvvidconv !
        video/x-raw(memory:NVMM), format=I420 ! nvvidconv !
        video/x-raw, format=BGRx, width={width}, height={height} !
        appsink sync=false max-buffers=2 drop=true name=sink emit-signals=true
    """
    return gst_query

def get_pipe_test(source_url, width, height):
    gst_query = f"""
        rtspsrc location={source_url} name=rtsp latency=0 !
        application/x-rtp, encoding-name=JPEG,payload=96 ! queue name=q !
        rtph264depay ! avdec_h264 ! videoconvert ! decodebin ! appsink sync=false max-buffers=2 drop=true name=sink emit-signals=true
    """
    return gst_query

class GstRtspProcess:
    process = None
    rtsp = None

    def __init__(self, source_url, width, height, input_queue,IS_DEBUG):
        self.rtsp = GstRtsp(source_url, width, height, IS_DEBUG)

        self.process = Process(
            target=self.rtsp.start,
            args=(input_queue,))
        self.process.start()

    def stop(self):
        logger.info("stop request to gst process from main process")
        if self.process is not None:
            self.process.terminate()
            self.process.join()


class GstRtsp:
    pipe = None
    sink = None
    underrun_timeout_id = None
    queue = None
    template_queue = None
    loop = None

    def __init__(self, source_url, width, height, IS_DEBUG):
        self.source_url = source_url
        self.width = width
        self.height = height
        self.IS_DEBUG = IS_DEBUG

    def __del__(self):
        self.stop()

    def reset_timeout(self):
        self.unset_timeout()
        self.set_timeout()

    def unset_timeout(self):
        if self.underrun_timeout_id:
            GLib.source_remove(self.underrun_timeout_id)
            self.underrun_timeout_id = None

    def set_timeout(self):
        self.underrun_timeout_id = GLib.timeout_add(1000, self.timeout)

    def timeout(self):
        logger.info("[rtsp connection] timeout")
        self.retry_to_connect()

    def start(self, queue):
        self.queue = queue
        # start gnome loop
        self.try_to_connect()
        self.loop = GLib.MainLoop()
        self.loop.run()
        self.stop()

    def try_to_connect(self):
        # set pipline
        if self.IS_DEBUG==0:
            self.pipe = Gst.parse_launch(get_pipe(self.source_url, self.width, self.height))
        else:
            self.pipe = Gst.parse_launch(get_pipe_test(self.source_url, self.width, self.height))

        print(self.pipe)
        # get jpeg image by appsink
        self.sink = self.pipe.get_by_name('sink')
        self.sink.connect("new-sample", self.on_array_data, self.sink)

        bus = self.pipe.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        # start gst pipeline
        while True:
            self.pipe.set_state(Gst.State.PLAYING)
            ret, state, _ = self.pipe.get_state(Gst.CLOCK_TIME_NONE)
            # if cant connect by rtsp
            if ret == Gst.StateChangeReturn.SUCCESS:
                logger.info("[rtsp connection] success to connect: " + self.source_url)
                break
            else:
                logger.info("[rtsp connection] failed to connect to rtsp server: " + self.source_url)
                self.pipe.set_state(Gst.State.NULL)
                sleep(retry_interval)

    def retry_to_connect(self):
        self.unset_timeout()
        self.pipe.set_state(Gst.State.NULL)
        self.try_to_connect()

    def stop(self):
        logger.info("[rtsp connection] stop")
        if self.pipe is not None:
            self.pipe.send_event(Gst.Event.new_eos())
        if self.queue is not None:
            self.queue.put(None)
        if self.loop is not None and self.loop.is_running():
            self.loop.quit()

    def on_array_data(self, sink, data):
        # set timeout
        self.reset_timeout()

        sample = self.sink.emit('pull-sample')
        if sample is None:
            return Gst.FlowReturn.ERROR
        buf = sample.get_buffer()

        data = buf.extract_dup(0, buf.get_size())
        array = np.ndarray(
            (self.height, self.width, 4),
            buffer=data,
            dtype=np.uint8)
        rgb, x = np.split(array, [3], axis=2)
        req = streaming_matching.RequestContainer().set_array_data(rgb)
        # logger.info("%s", self.queue)
        if self.queue is not None and not self.queue.full():
            self.queue.put(req)
        return Gst.FlowReturn.OK

    def on_message(self, bus, message):
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.info(("Error received from element %s: %s" % (
                message.src.get_name(), err)))
            logger.info(("Debugging information: %s" % debug))
            self.retry_to_connect()
        elif message.type == Gst.MessageType.EOS:
            logger.info("End-Of-Stream reached.")
            self.retry_to_connect()
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if isinstance(message.src, Gst.Pipeline):
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.info(("Pipeline state changed from %s to %s." %
                        (old_state.value_nick, new_state.value_nick)))

