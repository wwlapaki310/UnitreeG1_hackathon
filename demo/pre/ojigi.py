"""
お辞儀モーション — arm_sdk で両肩を前方にピッチしてお辞儀を表現

制約:
  - G1 の WaistPitch は 23dof/29dof で LOCKED（物理的に体幹前傾不可）
  - お辞儀 API は LocoClient に存在しない
  → 代替: 両肩を前方にピッチ + LowStand で「前傾感」を演出

角度の目安（bow_angle で指定）:
  "shallow" — 両肩 0.5 rad（軽礼、会釈）
  "normal"  — 両肩 0.8 rad（普通礼、30度相当）
  "deep"    — 両肩 1.1 rad（深礼、45度相当）

Usage:
    python demo/ojigi.py <networkInterface> [bow_angle]
    例) python demo/ojigi.py eth0 normal
"""

import math
import sys
import time

import numpy as np

from unitree_sdk2py.core.channel import (
    ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize,
)
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_
from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread


class J:
    LeftShoulderPitch  = 15
    LeftShoulderRoll   = 16
    LeftShoulderYaw    = 17
    LeftElbow          = 18
    LeftWristRoll      = 19
    RightShoulderPitch = 22
    RightShoulderRoll  = 23
    RightShoulderYaw   = 24
    RightElbow         = 25
    RightWristRoll     = 26
    WaistYaw           = 12
    WaistRoll          = 13  # INVALID: waist locked
    WaistPitch         = 14  # INVALID: waist locked
    kWeight            = 29


ARM_JOINTS = [
    J.LeftShoulderPitch,  J.LeftShoulderRoll,  J.LeftShoulderYaw,  J.LeftElbow,  J.LeftWristRoll,
    J.RightShoulderPitch, J.RightShoulderRoll, J.RightShoulderYaw, J.RightElbow, J.RightWristRoll,
    J.WaistYaw, J.WaistRoll, J.WaistPitch,
]

# お辞儀の深さ別姿勢
# 両肩を前方にピッチ、肘はほぼ伸ばして腕を体前面に沿わせる
BOW_POSES = {
    "shallow": {
        "description": "会釈（軽礼）",
        "pose": [
            # L-Shoulder: Pitch, Roll, Yaw
             0.50,  0.05,  0.00,
            # L-Elbow, L-WristRoll
             0.20,  0.00,
            # R-Shoulder: Pitch, Roll, Yaw
             0.50, -0.05,  0.00,
            # R-Elbow, R-WristRoll
             0.20,  0.00,
            # Waist（locked なので 0 固定）
             0.00,  0.00,  0.00,
        ],
    },
    "normal": {
        "description": "普通礼（30度相当）",
        "pose": [
            # L-Shoulder: Pitch, Roll, Yaw
             0.80,  0.05,  0.00,
            # L-Elbow, L-WristRoll
             0.25,  0.00,
            # R-Shoulder: Pitch, Roll, Yaw
             0.80, -0.05,  0.00,
            # R-Elbow, R-WristRoll
             0.25,  0.00,
            # Waist
             0.00,  0.00,  0.00,
        ],
    },
    "deep": {
        "description": "深礼（45度相当）",
        "pose": [
            # L-Shoulder: Pitch, Roll, Yaw
             1.10,  0.05,  0.00,
            # L-Elbow, L-WristRoll
             0.30,  0.00,
            # R-Shoulder: Pitch, Roll, Yaw
             1.10, -0.05,  0.00,
            # R-Elbow, R-WristRoll
             0.30,  0.00,
            # Waist
             0.00,  0.00,  0.00,
        ],
    },
}

PHASE_BOW_SEC    = 1.5   # お辞儀へ移行
PHASE_HOLD_SEC   = 1.2   # お辞儀を保持
PHASE_RISE_SEC   = 1.5   # 起き上がり
PHASE_RELEASE_SEC = 0.5  # arm_sdk 解除


class OjigiMotion:
    def __init__(self, bow_angle: str = "normal"):
        if bow_angle not in BOW_POSES:
            raise ValueError(f"Unknown bow_angle: {bow_angle}. Choose from {list(BOW_POSES)}")
        self.pose        = BOW_POSES[bow_angle]["pose"]
        self.control_dt  = 0.02
        self.time_       = 0.0
        self.low_cmd     = unitree_hg_msg_dds__LowCmd_()
        self.low_state   = None
        self.first_state = False
        self.done        = False
        self.crc         = CRC()
        self.kp          = 60.0
        self.kd          = 1.5
        self._neutral    = None  # 開始時の関節角を保存

    def init(self):
        self.pub = ChannelPublisher("rt/arm_sdk", LowCmd_)
        self.pub.Init()
        self.sub = ChannelSubscriber("rt/lowstate", LowState_)
        self.sub.Init(self._state_cb, 10)

    def start(self):
        self.thread = RecurrentThread(
            interval=self.control_dt, target=self._write, name="ojigi"
        )
        print("LowState 受信待機中...")
        while not self.first_state:
            time.sleep(0.1)
        # 開始時の関節角をスナップショット
        self._neutral = [self.low_state.motor_state[j].q for j in ARM_JOINTS]
        self.thread.Start()

    def _state_cb(self, msg: LowState_):
        self.low_state = msg
        self.first_state = True

    def _set_joint(self, joint: int, q: float):
        self.low_cmd.motor_cmd[joint].tau = 0.0
        self.low_cmd.motor_cmd[joint].q   = q
        self.low_cmd.motor_cmd[joint].dq  = 0.0
        self.low_cmd.motor_cmd[joint].kp  = self.kp
        self.low_cmd.motor_cmd[joint].kd  = self.kd

    def _write(self):
        t = self.time_
        self.time_ += self.control_dt

        t1 = PHASE_BOW_SEC
        t2 = t1 + PHASE_HOLD_SEC
        t3 = t2 + PHASE_RISE_SEC
        t4 = t3 + PHASE_RELEASE_SEC

        if t < t1:
            # Phase 1: お辞儀姿勢へ
            self.low_cmd.motor_cmd[J.kWeight].q = 1.0
            ratio = np.clip(t / t1, 0.0, 1.0)
            # ease-in-out でなめらかに
            ratio = 0.5 - 0.5 * math.cos(math.pi * ratio)
            for i, joint in enumerate(ARM_JOINTS):
                q = (1.0 - ratio) * self._neutral[i] + ratio * self.pose[i]
                self._set_joint(joint, q)

        elif t < t2:
            # Phase 2: お辞儀を保持
            for i, joint in enumerate(ARM_JOINTS):
                self._set_joint(joint, self.pose[i])

        elif t < t3:
            # Phase 3: 起き上がり
            ratio = np.clip((t - t2) / PHASE_RISE_SEC, 0.0, 1.0)
            ratio = 0.5 - 0.5 * math.cos(math.pi * ratio)
            for i, joint in enumerate(ARM_JOINTS):
                q = (1.0 - ratio) * self.pose[i] + ratio * self._neutral[i]
                self._set_joint(joint, q)

        elif t < t4:
            # Phase 4: arm_sdk 解除
            ratio = np.clip((t - t3) / PHASE_RELEASE_SEC, 0.0, 1.0)
            self.low_cmd.motor_cmd[J.kWeight].q = 1.0 - ratio

        else:
            self.done = True
            return

        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.pub.Write(self.low_cmd)


def run_ojigi(bow_angle: str = "normal") -> None:
    """
    ChannelFactoryInitialize 済みの前提で呼ぶ。
    他スクリプト（demo.py 等）から import して使う。
    """
    info = BOW_POSES.get(bow_angle, {})
    print(f"お辞儀: {bow_angle} — {info.get('description', '')}")
    motion = OjigiMotion(bow_angle)
    motion.init()
    motion.start()
    while not motion.done:
        time.sleep(0.1)
    print("お辞儀完了")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <networkInterface> [bow_angle]")
        print(f"  bow_angle: {' | '.join(BOW_POSES)}  (default: normal)")
        for k, v in BOW_POSES.items():
            print(f"    {k:8s} — {v['description']}")
        sys.exit(-1)

    net       = sys.argv[1]
    bow_angle = sys.argv[2] if len(sys.argv) >= 3 else "normal"

    if bow_angle not in BOW_POSES:
        print(f"ERROR: Unknown bow_angle '{bow_angle}'. Choose from {list(BOW_POSES)}")
        sys.exit(-1)

    print("WARNING: ロボット周辺に障害物がないことを確認してください。")
    input("準備ができたら Enter を押してください...")

    ChannelFactoryInitialize(0, net)
    run_ojigi(bow_angle)
