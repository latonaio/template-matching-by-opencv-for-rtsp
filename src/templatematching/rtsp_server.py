#!/usr/bin/env python3
import logging
from multiprocessing import Process
from os import environ
from threading import Thread

import gi
import numpy as np

gi.require_version('Gst', '1.0')  # noqa
gi.require_version('GstRtspServer', '1.0')  # noqa
from gi.repository import Gst, GLib, GstRtspServer  # isort:skip

# initialize gstreamer library
Gst.init(None)
Gst.debug_set_active(True)
Gst.debug_set_default_threshold(3)


logger = logging.getLogger(__name__)


def get_pipe(width, height):
    return f"""
        appsrc format=time name=source ! 
        video/x-raw,width={width},height={height},format=BGRx,framerate=(fraction)10/1,depth=32,bpp=32 ! 
        nvvidconv ! video/x-raw(memory:NVMM) ! nvvidconv ! videorate ! 
        video/x-raw,framerate=30/1,format=I420 ! nvjpegenc ! queue ! rtpjpegpay name=pay0 pt=96 
        """
def get_pipe_test(width, height):
    return f"""
        appsrc format=time name=source ! video/x-raw,width={width},height={height},format=BGRx,framerate=(fraction)10/1 ! video/x-raw, format=I420 ! videoconvert ! jpegenc ! queue ! rtpjpegpay name=pay0 pt=96
        """


class GstRtspSrvProcess:
    process = None
    rtsp = None

    def __init__(self, input_queue, port, width, height,IS_DEBUG):
        self.rtsp = GstRtspSrv(port, width, height,IS_DEBUG)
        self.queue = input_queue
        self.IS_DEBUG=IS_DEBUG

        self.process = Process(
            target=self.rtsp.start,
            args=(input_queue,))
        self.process.start()

    def stop(self):
        logger.info("stop request to gst process from main process")
        if self.process is not None:
            self.process.terminate()
            self.process.join()
        self.queue.put(None)


class GstRtspSrv:
    pipe = None
    appsrc = None

    def __init__(self, port, width, height,IS_DEBUG):
        port_str = str(port)
        self.is_push_buffer_allowed = False
        self.port = port
        self.url = f"http://127.0.0.1:{port}/fitness"
        self.pipe = None
        self.IS_DEBUG=IS_DEBUG
        self.server = GstRtspServer.RTSPServer().new()
        self.server.set_service(port_str)
        self.server.connect("client-connected", self.client_connected)

        self.f = GstRtspServer.RTSPMediaFactory().new()
        self.f.set_eos_shutdown(True)
        if self.IS_DEBUG==0:
            self.f.set_launch(get_pipe(width, height))
        else:
            self.f.set_launch(get_pipe_test(width, height))

        self.f.set_shared(True)
        self.f.connect("media-constructed", self.on_media_constructed)

        m = self.server.get_mount_points()
        m.add_factory("/fitness", self.f)
        self.server.attach(None)

        logger.info(f"[RTSP] ready at {self.url}")

    def client_connected(self, arg1, arg2):
        logger.info('[RTSP] next service is connected')

    def on_media_constructed(self, factory, media):
        logger.info('[RTSP] media is constructed')
        # get element state and check state
        self.pipe = media.get_element()
        # get jpeg image by appsink
        self.appsrc = self.pipe.get_by_name('source')
        self.appsrc.connect('need-data', self.start_feed)
        self.appsrc.connect('enough-data', self.stop_feed)

        self.pipe.set_state(Gst.State.PLAYING)
        ret, _, _ = self.pipe.get_state(Gst.CLOCK_TIME_NONE)

    def start(self, queue):
        # start rtp server
        logger.info(f"[rtp server] start rtp server : {self.url}")
        loop = GLib.MainLoop()
        t = Thread(target=self.loop_of_put_buffer, args=(queue,))
        t.start()
        loop.run()

    def stop(self):
        logger.info("[rtp server] stop")
        if self.appsrc is not None:
            self.appsrc.emit("end-of-stream")
        if self.pipe is not None:
            self.pipe.send_event(Gst.Event.new_eos())

    def start_feed(self, src, length):
        self.is_push_buffer_allowed = True

    def stop_feed(self, src):
        logger.info("==========stop_feed========")
        self.is_push_buffer_allowed = False

    def loop_of_put_buffer(self, queue):
        duration = 10 ** 9 / 10
        n_frame = 1
        while True:
            array = queue.get()
            if not self.is_push_buffer_allowed:
                continue
            if array is None:
                self.stop()
                break
            # create buffer data
            bgrx = np.concatenate(
                [array, np.full([array.shape[0], array.shape[1], 1], 255, dtype=np.uint8)], axis=2)
            data = bgrx.tobytes()
            buffer = Gst.Buffer.new_wrapped(data)
            # TODO: timestamp overflow
            buffer.duration = duration
            timestamp = n_frame * duration
            buffer.pts = timestamp
            buffer.dts = timestamp
            buffer.offset = n_frame
            # Allocate GstBuffer
            ret = self.appsrc.emit("push-buffer", buffer)
            if ret != Gst.FlowReturn.OK:
                print('[rtp server] media is closed')
                n_frame = 1
                self.pipe.set_state(Gst.State.NULL)
                self.is_push_buffer_allowed = False
                continue
            n_frame = n_frame + 1
