#!/usr/bin/env python3
import pytest

import os
import queue
from src.templatematching import streaming_matching as sm
from multiprocessing import Queue, Process
import numpy as np

category = ["start", "end"]

def test_normal_case_001_request_container():
    json_path = "json_path"
    category = "category"
    rc = sm.RequestContainer().set_template_data(json_path, category)

    assert rc.type == sm.RequestType.Template
    assert rc.json_path == json_path
    assert rc.category == category
    assert rc.array is None

def test_normal_case_002_request_container():
    array = "array"
    category = "category"
    rc = sm.RequestContainer().set_array_data(array, category)

    assert rc.type == sm.RequestType.Array
    assert rc.json_path is None
    assert rc.category == category
    assert rc.array == array

@pytest.fixture
def init_matching():
    json_path, _ = get_data_path()
    input_q = Queue()
    output_q = Queue()
    s = sm.MatchingFromStreaming(input_q, output_q, json_path)
    yield s, input_q, output_q

    s.stop()
    input_q.put(None)
    input_q.close()
    output_q.close()

def get_data_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    files = ["../file/data/rob1_center_test.json", "../file/data/rob1_center_test.npy"]
    ret = []

    for x in files:
        ret.append(os.path.abspath(os.path.join(base_dir, x)))
    return ret[0], ret[1]

def normal_data_of_array():
    _, array_path = get_data_path()
    if not os.path.exists(array_path):
        raise FileNotFoundError
    array = np.load(array_path)
    return sm.RequestContainer().set_array_data(array, category[0])

def normal_002_data_of_array():
    return sm.RequestContainer().set_array_data(np.array([[0,0,0]]), category[0])

def test_normal_case_001_convert_loop(init_matching):
    s, input_q, output_q = init_matching

    p = Process(target=s.convert_loop,
                args=(input_q, output_q))
    p.start()

    input_q.put(normal_data_of_array())
    ret = output_q.get(timeout=1)

    assert ret["fitness"] == {category[0]: 1.0, category[1]: 1.0}
    assert ret["timestamp"] is not None


def test_normal_case_002_convert_loop(init_matching):
    s, input_q, output_q = init_matching

    p = Process(target=s.convert_loop,
                args=(input_q, output_q))
    p.start()

    input_q.put(normal_002_data_of_array())
    ret = output_q.get(timeout=1)

    assert ret["fitness"] == {category[0]: -1.0, category[1]: -1.0}
    assert ret["timestamp"] is not None

def test_normal_case_003_convert_loop(init_matching):
    s, input_q, output_q = init_matching

    p = Process(target=s.convert_loop,
                args=(input_q, output_q))
    p.start()

    input_q.put(None)
    ret = output_q.get(timeout=1)
    assert ret is None

def test_abnormal_case_001_convert_loop(init_matching):
    s, input_q, output_q = init_matching

    p = Process(target=s.convert_loop,
                args=(input_q, output_q))
    p.start()

    input_q.put("test")
    with pytest.raises(queue.Empty):
        output_q.get(timeout=1)

def test_abnormal_case_002_convert_loop(init_matching):
    s, input_q, output_q = init_matching

    p = Process(target=s.convert_loop,
                args=(input_q, output_q))
    p.start()

    input_q.put(None)
    _ = output_q.get(timeout=1)

    input_q.put(normal_data_of_array())
    with pytest.raises(queue.Empty):
        output_q.get(timeout=1)


