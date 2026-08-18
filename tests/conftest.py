"""Shared fixtures for the ROS-agnostic bridge tests (no rospy required)."""
from __future__ import annotations

import pytest


class FakeArm:
    """Minimal litearm.Arm stand-in recording every call."""

    def __init__(self):
        self.calls = []
        self.q = [0.1] * 7
        self.state = "ready"

    def get_state(self):
        self.calls.append("get_state")
        return {
            "q": list(self.q),
            "dq": [0.01] * 7,
            "tau": [0.0] * 7,
            "fault": [],
            "state": self.state,
        }

    def get_tcp_pose(self):
        return ([0.2, 0.3, 0.4], [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]])

    def fk(self, q):
        return ([0.2, 0.3, 0.4], [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]])

    def ik(self, pose, q_seed=None):
        return ([0.5] * 7, True)

    def movej(self, q_target, speed=1.0, settle_s=1.0, **kwargs):
        self.calls.append(("movej", list(q_target), speed, settle_s))
        self.q = list(q_target)
        return True

    def movel(self, pose, speed=1.0, settle_s=1.0, **kwargs):
        self.calls.append(("movel", pose, speed, settle_s))
        return True

    def request_stop(self):
        self.calls.append("request_stop")

    def clear_stop(self):
        self.calls.append("clear_stop")
        return True

    def enable(self):
        self.calls.append("enable")

    def disable(self):
        self.calls.append("disable")

    def close(self):
        self.calls.append("close")


@pytest.fixture
def fake_arm():
    return FakeArm()
