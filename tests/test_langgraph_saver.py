import pytest
from graph.langgraph_saver import attach_langgraph_saver


def test_attach_sets_marker_on_graph():
    class G:
        pass

    g = G()
    ok = attach_langgraph_saver(g)
    assert ok is True
    assert getattr(g, "_langgraph_custom_saver", False) is True


def test_attach_handles_setattr_error():
    # Create an object whose __setattr__ raises to simulate failure
    class Bad:
        def __setattr__(self, name, value):
            raise RuntimeError("cannot set")

    b = Bad()
    ok = attach_langgraph_saver(b)
    assert ok is False
