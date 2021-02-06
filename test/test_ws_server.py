import pytest

import queue
from multiprocessing import Queue
import socketio
from src.templatematching.old import ws_server
from time import sleep

host = "localhost"
uri = "/"
port = 15290
normal_data = {
    "json_file_path": "test_path",
    "category": "test_category",
    "eventName": "set_json_data",
    "sessionID": "0000",
}
abnormal_data = {
    "eventName": "set_json_data",
    "sessionID": "0000",
}

@pytest.fixture()
def sio_client():
    sio = None
    p = None
    try:
        # set input queue
        q = Queue()
        # start ws server
        ws_server.Server.start_multiprocessing(uri, host, port, q)
        sleep(0.5)

        # start ws client
        sio = socketio.Client()
        url = "http://localhost:" + str(port)
        sio.connect(url, transports=['websocket'], namespaces=uri)

        yield q, sio

    finally:
        # stop multiprocessing
        if sio is not None:
            sio.disconnect()
        ws_server.Server.stop()

def test_normal_001_get_request(sio_client):
    q, sio = sio_client
    sio.emit("sync_request", data=normal_data)
    res = q.get(timeout=1)
    assert res.json_path == normal_data["json_file_path"]
    assert res.category == normal_data["category"]

def test_abnormal_001_get_request(sio_client):
    q, sio = sio_client
    sio.emit("sync_request", data=abnormal_data)
    with pytest.raises(queue.Empty):
        res = q.get(timeout=1)

def test_abnormal_001_stop():
    ws_server.Server.stop()
