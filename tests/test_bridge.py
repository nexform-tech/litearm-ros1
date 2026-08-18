"""Tests for LiteArmBridge (ROS-agnostic, no rospy needed)."""
from __future__ import annotations

from litearm_ros1 import LiteArmBridge


def test_read_joint_state(fake_arm):
    bridge = LiteArmBridge(fake_arm)
    js = bridge.read_joint_state()
    assert js["name"] == [f"joint{i}" for i in range(7)]
    assert js["position"] == fake_arm.q
    assert len(js["velocity"]) == 7
    assert len(js["effort"]) == 7


def test_read_tcp_pose_identity(fake_arm):
    bridge = LiteArmBridge(fake_arm)
    pose = bridge.read_tcp_pose()
    assert pose[0:3] == (0.2, 0.3, 0.4)      # position
    assert pose[3:7] == (0.0, 0.0, 0.0, 1.0)  # identity rotation quaternion


def test_read_tcp_pose_none_on_error(fake_arm):
    bridge = LiteArmBridge(fake_arm)
    fake_arm.get_tcp_pose = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    assert bridge.read_tcp_pose() is None


def test_movej_success(fake_arm):
    bridge = LiteArmBridge(fake_arm)
    ok, message = bridge.movej([0.0] * 7, speed=0.3, settle_s=0.5)
    assert ok and message == "ok"
    assert ("movej", [0.0] * 7, 0.3, 0.5) in fake_arm.calls


def test_movej_error(fake_arm):
    def _fail(q_target, speed=1.0, settle_s=1.0, **kw):
        raise RuntimeError("busy")

    fake_arm.movej = _fail
    bridge = LiteArmBridge(fake_arm)
    ok, message = bridge.movej([0.0] * 7)
    assert ok is False
    assert "busy" in message


def test_movel_converts_pose(fake_arm):
    bridge = LiteArmBridge(fake_arm)
    ok, message = bridge.movel([0.1, 0.2, 0.3, 0, 0, 0, 1], speed=0.4)
    assert ok and message == "ok"
    # the arm must receive the litearm [position, rotation] format
    pose = fake_arm.calls[-1][1]
    assert pose[0] == [0.1, 0.2, 0.3]
    assert pose[1] == [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]


def test_fk(fake_arm):
    bridge = LiteArmBridge(fake_arm)
    pose, ok, message = bridge.fk([0.1] * 7)
    assert ok and message == "ok"
    assert pose[0:3] == (0.2, 0.3, 0.4)


def test_ik(fake_arm):
    bridge = LiteArmBridge(fake_arm)
    q, ok, message = bridge.ik([0.1, 0.2, 0.3, 0, 0, 0, 1])
    assert ok and message == "ok"
    assert q == [0.5] * 7


def test_controls(fake_arm):
    bridge = LiteArmBridge(fake_arm)
    for name in ("request_stop", "clear_stop", "enable", "disable"):
        ok, message = getattr(bridge, name)()
        assert ok, (name, message)
    assert fake_arm.calls.count("request_stop") == 1
    assert fake_arm.calls.count("enable") == 1


def test_get_state(fake_arm):
    bridge = LiteArmBridge(fake_arm)
    state = bridge.get_state()
    assert state["state"] == "ready"
    assert state["fault"] is False
    assert len(state["q"]) == 7


def test_close(fake_arm):
    bridge = LiteArmBridge(fake_arm)
    bridge.close()
    assert fake_arm.calls.count("close") == 1
