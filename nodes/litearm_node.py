#!/usr/bin/env python3
"""litearm_node — ROS1 (Noetic) bridge for the LiteArm robotic arm.

Publishes:
    /joint_states            sensor_msgs/JointState     (q / dq / tau)
    /litearm/tcp_pose        geometry_msgs/PoseStamped  (TCP pose in base)
    /tf                      base_link -> tool0

Subscribes:
    /litearm/cmd_joint       sensor_msgs/JointState     (position -> movej)
    /litearm/stop            std_msgs/Empty             (emergency stop)

Services:
    /litearm/movej           litearm_ros1/Movej
    /litearm/movel           litearm_ros1/Movel
    /litearm/fk              litearm_ros1/Fk
    /litearm/ik              litearm_ros1/Ik
    /litearm/get_state       litearm_ros1/GetState
    /litearm/request_stop    std_srvs/Trigger
    /litearm/clear_stop      std_srvs/Trigger
    /litearm/enable          std_srvs/Trigger
    /litearm/disable         std_srvs/Trigger
"""
from __future__ import annotations

import rospy
from geometry_msgs.msg import Pose, PoseStamped
from sensor_msgs.msg import JointState
from std_msgs.msg import Empty
from std_srvs.srv import Trigger, TriggerResponse
import tf

import litearm

from litearm_ros1.bridge import LiteArmBridge
from litearm_ros1.srv import (
    Fk, FkResponse,
    GetState, GetStateResponse,
    Ik, IkResponse,
    Movej, MovejResponse,
    Movel, MovelResponse,
)

import os


class LiteArmNode:
    def __init__(self, bridge: LiteArmBridge, loop_hz: float = 50.0,
                 base_frame: str = "base_link", tcp_frame: str = "tool0") -> None:
        self.bridge = bridge
        self.loop_hz = loop_hz
        self.base_frame = base_frame
        self.tcp_frame = tcp_frame

        # publishers
        self.pub_joint = rospy.Publisher("/joint_states", JointState, queue_size=10)
        self.pub_pose = rospy.Publisher("/litearm/tcp_pose", PoseStamped, queue_size=10)
        self.tf_broadcaster = tf.TransformBroadcaster()

        # subscribers
        rospy.Subscriber("/litearm/cmd_joint", JointState, self._on_cmd_joint)
        rospy.Subscriber("/litearm/stop", Empty, self._on_stop)

        # services
        rospy.Service("/litearm/movej", Movej, self._srv_movej)
        rospy.Service("/litearm/movel", Movel, self._srv_movel)
        rospy.Service("/litearm/fk", Fk, self._srv_fk)
        rospy.Service("/litearm/ik", Ik, self._srv_ik)
        rospy.Service("/litearm/get_state", GetState, self._srv_get_state)
        rospy.Service("/litearm/request_stop", Trigger, self._srv_request_stop)
        rospy.Service("/litearm/clear_stop", Trigger, self._srv_clear_stop)
        rospy.Service("/litearm/enable", Trigger, self._srv_enable)
        rospy.Service("/litearm/disable", Trigger, self._srv_disable)

        rospy.Timer(rospy.Duration(1.0 / self.loop_hz), self._publish_state)

    # ── publishers ───────────────────────────────────────────────────────────

    def _publish_state(self, _event) -> None:
        js = self.bridge.read_joint_state()
        if js is None:
            return
        msg = JointState()
        msg.header.stamp = rospy.Time.now()
        msg.header.frame_id = self.base_frame
        msg.name = js["name"]
        msg.position = js["position"]
        msg.velocity = js["velocity"]
        msg.effort = js["effort"]
        self.pub_joint.publish(msg)

        pose = self.bridge.read_tcp_pose()
        if pose is not None:
            pmsg = PoseStamped()
            pmsg.header.stamp = msg.header.stamp
            pmsg.header.frame_id = self.base_frame
            pmsg.pose.position.x, pmsg.pose.position.y, pmsg.pose.position.z = pose[0:3]
            pmsg.pose.orientation.x, pmsg.pose.orientation.y = pose[3], pose[4]
            pmsg.pose.orientation.z, pmsg.pose.orientation.w = pose[5], pose[6]
            self.pub_pose.publish(pmsg)
            self.tf_broadcaster.sendTransform(
                pose[0:3], pose[3:7], msg.header.stamp, self.tcp_frame, self.base_frame
            )

    # ── subscribers ──────────────────────────────────────────────────────────

    def _on_cmd_joint(self, msg: JointState) -> None:
        if not msg.position:
            return
        ok, message = self.bridge.movej(msg.position, speed=rospy.get_param("~cmd_speed", 0.5))
        if not ok:
            rospy.logwarn("movej failed: %s", message)

    def _on_stop(self, _msg: Empty) -> None:
        ok, message = self.bridge.request_stop()
        rospy.loginfo("emergency stop: %s (%s)", ok, message)

    # ── services ─────────────────────────────────────────────────────────────

    def _srv_movej(self, req) -> MovejResponse:
        ok, message = self.bridge.movej(req.q_target, speed=req.speed, settle_s=req.settle_s)
        res = MovejResponse()
        res.success, res.message = ok, message
        return res

    def _srv_movel(self, req) -> MovelResponse:
        xyz_quat = _pose_to_xyz_quat(req.pose)
        ok, message = self.bridge.movel(xyz_quat, speed=req.speed, settle_s=req.settle_s)
        res = MovelResponse()
        res.success, res.message = ok, message
        return res

    def _srv_fk(self, req) -> FkResponse:
        pose, ok, message = self.bridge.fk(req.q)
        res = FkResponse()
        res.success, res.message = ok, message
        if pose is not None:
            res.pose = _xyz_quat_to_pose(pose)
        return res

    def _srv_ik(self, req) -> IkResponse:
        q, ok, message = self.bridge.ik(_pose_to_xyz_quat(req.pose), q_seed=req.q_seed)
        res = IkResponse()
        res.success, res.message = ok, message
        res.q = q or []
        return res

    def _srv_get_state(self, req) -> GetStateResponse:
        res = GetStateResponse()
        state = self.bridge.get_state()
        if state is None:
            res.message = "no state yet"
            return res
        res.q, res.dq, res.tau = state["q"], state["dq"], state["tau"]
        res.state = state["state"]
        res.fault = state["fault"]
        res.message = "ok"
        return res

    def _srv_request_stop(self, req) -> TriggerResponse:
        ok, message = self.bridge.request_stop()
        return TriggerResponse(success=ok, message=message)

    def _srv_clear_stop(self, req) -> TriggerResponse:
        ok, message = self.bridge.clear_stop()
        return TriggerResponse(success=ok, message=message)

    def _srv_enable(self, req) -> TriggerResponse:
        ok, message = self.bridge.enable()
        return TriggerResponse(success=ok, message=message)

    def _srv_disable(self, req) -> TriggerResponse:
        ok, message = self.bridge.disable()
        return TriggerResponse(success=ok, message=message)


def _pose_to_xyz_quat(pose: Pose):
    p, o = pose.position, pose.orientation
    return (p.x, p.y, p.z, o.x, o.y, o.z, o.w)


def _xyz_quat_to_pose(xyz_quat) -> Pose:
    pose = Pose()
    pose.position.x, pose.position.y, pose.position.z = xyz_quat[0:3]
    pose.orientation.x, pose.orientation.y = xyz_quat[3], xyz_quat[4]
    pose.orientation.z, pose.orientation.w = xyz_quat[5], xyz_quat[6]
    return pose


def main():
    rospy.init_node("litearm_node")
    endpoint = rospy.get_param("~endpoint", os.environ.get("LITEARM_ENDPOINT", "tcp/127.0.0.1:7447"))
    arm_id = rospy.get_param("~arm_id", "armA")
    loop_hz = rospy.get_param("~loop_hz", 50.0)
    joint_names = rospy.get_param("~joint_names", [f"joint{i}" for i in range(7)])
    base_frame = rospy.get_param("~base_frame", "base_link")
    tcp_frame = rospy.get_param("~tcp_frame", "tool0")

    arm = litearm.Arm(endpoint=endpoint, arm_id=arm_id)
    bridge = LiteArmBridge(arm, joint_names=joint_names)
    LiteArmNode(bridge, loop_hz=loop_hz, base_frame=base_frame, tcp_frame=tcp_frame)

    rospy.loginfo(
        "litearm_node connected to %s arm_id=%s loop_hz=%s",
        endpoint, arm_id, loop_hz,
    )
    rospy.spin()
    bridge.close()


if __name__ == "__main__":
    main()
