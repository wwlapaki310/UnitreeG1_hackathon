"""
茶筅モーション — arm_sdk で茶を点てる風の腕動作を行う

手に棒（茶筅）をテープで固定した状態で RightWristRoll を動かす。
4 つのパターンを用意: gentle / standard / vigorous / figure8

前提: LocoClient で StandUp2Squat 済みの姿勢で呼ぶと自然に見える。

Usage:
    python chasen_motion.py <networkInterface> [pattern]
    例) python chasen_motion.py eth0 standard
    パターン: gentle | standard | vigorous | figure8
"""

import math
import sys
import time
from dataclasses import dataclass
from typing import Callable

import numpy as np

from unitree_sdk2py.core.channel import (
    ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize,
)
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_
from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread


# ---- 関節インデックス ----
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


ARM_JOINTS = [
    J.LeftShoulderPitch,  J.LeftShoulderRoll,  J.LeftShoulderYaw,  J.LeftElbow,  J.LeftWristRoll,
    J.RightShoulderPitch, J.RightShoulderRoll, J.RightShoulderYaw, J.RightElbow, J.RightWristRoll,
    J.WaistYaw, J.WaistRoll, J.WaistPitch,
]

# 茶を点てる姿勢（左腕=茶碗保持、右腕=茶筅保持）
TEA_POSE = [
    # L-Shoulder: Pitch, Roll, Yaw
     0.50,  0.15,  0.00,
    # L-Elbow, L-WristRoll
     1.30,  0.00,
    # R-Shoulder: Pitch, Roll, Yaw
     0.50, -0.15,  0.00,
    # R-Elbow, R-WristRoll（WristRoll は動的に上書き）
     1.30,  0.00,
    # Waist
     0.00,  0.00,  0.00,
]

PHASE_PREPARE_SEC = 3.0
PHASE_RETURN_SEC  = 2.0
PHASE_RELEASE_SEC = 1.0


# ============================================================
# パターン定義
# ============================================================

@dataclass
class WhiskPattern:
    name:        str
    description: str
    duration:    float              # 茶筅動作の秒数
    wrist_fn:    Callable[[float], float]  # t → RightWristRoll のオフセット量
    elbow_fn:    Callable[[float], float]  # t → RightElbow のオフセット量（なければ 0）


def _make_patterns() -> dict[str, WhiskPattern]:
    tau = 2 * math.pi

    return {
        # ---- 丁寧: ゆっくり大きく、茶道らしい ----
        "gentle": WhiskPattern(
            name="gentle",
            description="丁寧 — 1Hz ±0.30 rad、ゆっくり優雅",
            duration=8.0,
            wrist_fn=lambda t: 0.30 * math.sin(tau * 1.0 * t),
            elbow_fn=lambda t: 0.0,
        ),

        # ---- 標準: 一般的な泡立て速度 ----
        "standard": WhiskPattern(
            name="standard",
            description="標準 — 2Hz ±0.45 rad、普通の泡立て",
            duration=8.0,
            wrist_fn=lambda t: 0.45 * math.sin(tau * 2.0 * t),
            elbow_fn=lambda t: 0.0,
        ),

        # ---- 力強い: 速く細かく ----
        "vigorous": WhiskPattern(
            name="vigorous",
            description="力強い — 3Hz ±0.50 rad、しっかり泡立て",
            duration=8.0,
            wrist_fn=lambda t: 0.50 * math.sin(tau * 3.0 * t),
            elbow_fn=lambda t: 0.0,
        ),

        # ---- figure8: 2 周波合成でランダム感、より自然な手の揺れ ----
        # 基本 1.5Hz + 倍音 4.5Hz を合成
        "figure8": WhiskPattern(
            name="figure8",
            description="figure8 — 2周波合成でランダム感、自然な手の動き",
            duration=10.0,
            wrist_fn=lambda t: (
                0.35 * math.sin(tau * 1.5 * t)
              + 0.15 * math.sin(tau * 4.5 * t + 0.5)
            ),
            # 肘も少し連動（手首と逆位相で小さく動かす）
            elbow_fn=lambda t: 0.05 * math.sin(tau * 1.5 * t + math.pi),
        ),
    }


PATTERNS = _make_patterns()


# ============================================================
# メインクラス
# ============================================================

class ChasenMotion:
    def __init__(self, pattern: WhiskPattern):
        self.pattern     = pattern
        self.control_dt  = 0.02
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

    def _set_joint(self, joint: int, q: float):
        self.low_cmd.motor_cmd[joint].tau = 0.0
        self.low_cmd.motor_cmd[joint].q   = q
        self.low_cmd.motor_cmd[joint].dq  = 0.0
        self.low_cmd.motor_cmd[joint].kp  = self.kp
        self.low_cmd.motor_cmd[joint].kd  = self.kd

    def _write(self):
        t = self.time_
        self.time_ += self.control_dt

        t1 = PHASE_PREPARE_SEC
        t2 = t1 + self.pattern.duration
        t3 = t2 + PHASE_RETURN_SEC
        t4 = t3 + PHASE_RELEASE_SEC

        if t < t1:
            # Phase 1: 茶を点てる姿勢へ移行
            self.low_cmd.motor_cmd[J.kWeight].q = 1.0
            ratio = np.clip(t / t1, 0.0, 1.0)
            for i, joint in enumerate(ARM_JOINTS):
                q_start  = self.low_state.motor_state[joint].q
                q_target = TEA_POSE[i]
                self._set_joint(joint, (1.0 - ratio) * q_start + ratio * q_target)

        elif t < t2:
            # Phase 2: 茶筅動作（パターンに応じて手首・肘を動的制御）
            self.whisk_time_ += self.control_dt
            wt = self.whisk_time_
            wrist_offset = self.pattern.wrist_fn(wt)
            elbow_offset = self.pattern.elbow_fn(wt)

            for i, joint in enumerate(ARM_JOINTS):
                q = TEA_POSE[i]
                if joint == J.RightWristRoll:
                    q += wrist_offset
                elif joint == J.RightElbow:
                    q += elbow_offset
                self._set_joint(joint, q)

        elif t < t3:
            # Phase 3: ニュートラルへ戻す
            ratio = np.clip((t - t2) / PHASE_RETURN_SEC, 0.0, 1.0)
            for i, joint in enumerate(ARM_JOINTS):
                q_current = self.low_state.motor_state[joint].q
                self._set_joint(joint, (1.0 - ratio) * q_current)

        elif t < t4:
            # Phase 4: arm_sdk を徐々に解除
            ratio = np.clip((t - t3) / PHASE_RELEASE_SEC, 0.0, 1.0)
            self.low_cmd.motor_cmd[J.kWeight].q = 1.0 - ratio

        else:
            self.done = True
            return

        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.pub.Write(self.low_cmd)


# ============================================================
# 実行ヘルパー（他スクリプトから import して呼び出し可）
# ============================================================

def run_chasen_motion(pattern_name: str = "standard") -> None:
    """
    ChannelFactoryInitialize 済みの前提で呼ぶ。
    他スクリプト（demo.py 等）から import して使う。
    """
    if pattern_name not in PATTERNS:
        raise ValueError(f"Unknown pattern: {pattern_name}. Choose from {list(PATTERNS)}")

    p = PATTERNS[pattern_name]
    print(f"茶筅パターン: {p.name} — {p.description}")

    motion = ChasenMotion(p)
    motion.init()
    motion.start()
    print("茶筅モーション開始...")
    while not motion.done:
        time.sleep(0.5)
    print("茶筅モーション完了")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <networkInterface> [pattern]")
        print(f"  パターン: {' | '.join(PATTERNS)}")
        for p in PATTERNS.values():
            print(f"    {p.name:10s} — {p.description}")
        sys.exit(-1)

    net   = sys.argv[1]
    pname = sys.argv[2] if len(sys.argv) >= 3 else "standard"

    if pname not in PATTERNS:
        print(f"ERROR: Unknown pattern '{pname}'. Choose from {list(PATTERNS)}")
        sys.exit(-1)

    print("WARNING: ロボット周辺に障害物がないことを確認してください。")
    input("準備ができたら Enter を押してください...")

    ChannelFactoryInitialize(0, net)
    run_chasen_motion(pname)
