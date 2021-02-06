import pytest
from threading import Thread
import queue
from src.templatematching import gst, streaming_matching
import multiprocessing

uri = "usb"
port = 8554
width = 864
height = 480
ADDRESS_RANGE = "224.3.0."
url = "rtsp://127.0.0.1:" + str(port) + "/" + uri
invalid_url = "test"

@pytest.fixture()
def stream_video():
    q = multiprocessing.Queue()
    video = gst.GetImageArray(url, width, height, q)
    yield video
    video.stop()

@pytest.fixture()
def invalid_stream_video():
    q = multiprocessing.Queue()
    video = gst.GetImageArray(invalid_url, width, height, q)
    yield video
    video.stop()

def test_normal_001_init(stream_video):
    assert stream_video.pipe is not None

def test_normal_001_get_query(stream_video):
    pipe_str = stream_video.get_pipe()
    assert pipe_str.find(str(width)) != -1
    assert pipe_str.find(str(height)) != -1
    assert pipe_str.find(str(url)) != -1

def test_normal_001_convert_loop(stream_video):
    q = queue.Queue()
    t = Thread(target=stream_video.convert_loop, args=(q,))
    t.start()
    res = q.get(timeout=1)
    assert res.array.shape == (height, width, 3)
    assert res.type == streaming_matching.RequestType.Array
    t.join(timeout=1)

def test_abnormal_001_convert_loop(invalid_stream_video):
    q = queue.Queue()
    t = Thread(target=invalid_stream_video.convert_loop, args=(q,))
    t.start()
    with pytest.raises(queue.Empty):
        _ = q.get(block=False)
    t.join(timeout=1)

