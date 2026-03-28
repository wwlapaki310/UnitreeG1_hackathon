"""
茶筅モーション — arm_sdk でお茶を点てる風の腕動作を行う

右手首（RightWristRoll）を sin 波で往復させて茶筅の動きを表現する。
左腕は茶碗を持つ姿勢で固定。

前提: LocoClient で StandUp2Squat 済みの姿勢で呼ぶと自然に見える。

Usage:
    python chasen_motion.py <networkInterface>
    例) python chasen_motion.py eth0
"""

import time
import sys
import math

import numpy as np

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_
from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread


# ---- 関節インデックス（g1_arm5_sdk_dds_example.py から流用） ----
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
    WaistRoll          = 13
    WaistPitch         = 14
    kWeight            = 29  # 1:arm_sdk 有効 / 0:無効


# arm_sdk で制御する関節リスト（順序は target_pos と対応）
ARM_JOINTS = [
    J.LeftShoulderPitch,  J.LeftShoulderRoll,  J.LeftShoulderYaw,  J.LeftElbow,  J.LeftWristRoll,
    J.RightShoulderPitch, J.RightShoulderRoll, J.RightShoulderYaw, J.RightElbow, J.RightWristRoll,
    J.WaistYaw, J.WaistRoll, J.WaistPitch,
]

# 茶を点てる姿勢の目標角度（単位: rad）
# 左腕: 茶碗を支える → 前方に出して肘を曲げる
# 右腕: 茶筅を持つ  → 同様に前方・肘曲げ（手首は動的に制御）
TEA_POSE = [
    # LeftShoulder: Pitch, Roll, Yaw
     0.50,  0.15,  0.00,
    # LeftElbow, LeftWristRoll
     1.30,  0.00,
    # RightShoulder: Pitch, Roll, Yaw
     0.50, -0.15,  0.00,
    # RightElbow, RightWristRoll（Rollは後で動的に上書き）
     1.30,  0.00,
    # Waist
     0.00,  0.00,  0.00,
]

# 茶筅の往復パラメータ
WHISK_AMPLITUDE = 0.45   # rad（±約 26°）
WHISK_FREQ_HZ   = 2.0    # 往復速度

PHASE_PREPARE_SEC = 3.0   # 姿勢移行
PHASE_WHISK_SEC   = 8.0   # 茶筅動作
PHASE_RETURN_SEC  = 2.0   # ニュートラルへ戻す
PHASE_RELEASE_SEC = 1.0   # arm_sdk 解除


class ChasenMotion:
    def __init__(self):
        self.control_dt = 0.02
        self.time_       = 0.0
        self.whisk_time_ = 0.0
        self.low_cmd     = unitree_hg_msg_dds__LowCmd_()
        self.low_state   = None
        self.first_state = False
        self.done        = False
        self.crc         = CRC()
        self.kp          = 60.0
        self.kd          = 1.5

    def init(self):
        self.pub = ChannelPublisher("rt/arm_sdk", LowCmd_)
        self.pub.Init()
        self.sub = ChannelSubscriber("rt/lowstate", LowState_)
        self.sub.Init(self._state_cb, 10)

    def start(self):
        self.thread = RecurrentThread(
            interval=self.control_dt, target=self._write, name="chasen"
        )
        print("LowState 受信待機中...")
        while not self.first_state:
            time.sleep(0.1)
        self.thread.Start()

    def _state_cb(self, msg: LowState_):
        self.low_state = msg
        self.first_state = True

    def _set_arm_joint(self, joint: int, q: float):
        self.low_cmd.motor_cmd[joint].tau = 0.0
        self.low_cmd.motor_cmd[joint].q   = q
        self.low_cmd.motor_cmd[joint].dq  = 0.0
        self.low_cmd.motor_cmd[joint].kp  = self.kp
        self.low_cmd.motor_cmd[joint].kd  = self.kd

    def _write(self):
        t = self.time_
        self.time_ += self.control_dt

        t1 = PHASE_PREPARE_SEC
        t2 = t1 + PHASE_WHISK_SEC
        t3 = t2 + PHASE_RETURN_SEC
        t4 = t3 + PHASE_RELEASE_SEC

        if t < t1:
            # ---- Phase 1: 茶を点てる姿勢へ移行 ----
            self.low_cmd.motor_cmd[J.kWeight].q = 1.0  # arm_sdk 有効
            ratio = np.clip(t / t1, 0.0, 1.0)
            for i, joint in enumerate(ARM_JOINTS):
                q_start = self.low_state.motor_state[joint].q
                q_target = TEA_POSE[i]
                self._set_arm_joint(joint, (1.0 - ratio) * q_start + ratio * q_target)

        elif t < t2:
            # ---- Phase 2: 茶筅往復（右手首を sin 波で動かす） ----
            self.whisk_time_ += self.control_dt
            whisk_q = WHISK_AMPLITUDE * math.sin(2 * math.pi * WHISK_FREQ_HZ * self.whisk_time_)

            for i, joint in enumerate(ARM_JOINTS):
                q = TEA_POSE[i]
                if joint == J.RightWristRoll:
                    q += whisk_q  # 右手首だけ動的に上書き
                self._set_arm_joint(joint, q)

        elif t < t3:
            # ---- Phase 3: ニュートラルへ戻す ----
            ratio = np.clip((t - t2) / PHASE_RETURN_SEC, 0.0, 1.0)
            for i, joint in enumerate(ARM_JOINTS):
                q_current = self.low_state.motor_state[joint].q
                self._set_arm_joint(joint, (1.0 - ratio) * q_current)

        elif t < t4:
            # ---- Phase 4: arm_sdk を徐々に解除 ----
            ratio = np.clip((t - t3) / PHASE_RELEASE_SEC, 0.0, 1.0)
            self.low_cmd.motor_cmd[J.kWeight].q = 1.0 - ratio

        else:
            self.done = True
            return

        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.pub.Write(self.low_cmd)


def run_chasen_motion(network_interface: str) -> None:
    """関数として呼び出す場合のエントリポイント（他スクリプトから import して使える）"""
    ChannelFactoryInitialize(0, network_interface)
    motion = ChasenMotion()
    motion.init()
    motion.start()
    print("茶筅モーション開始...")
    while not motion.done:
        time.sleep(0.5)
    print("茶筅モーション完了")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <networkInterface>")
        print("  例) python chasen_motion.py eth0")
        sys.exit(-1)

    print("WARNING: ロボット周辺に障害物がないことを確認してください。")
    input("準備ができたら Enter を押してください...")

    run_chasen_motion(sys.argv[1])
