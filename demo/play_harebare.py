"""
harebare.csv モーション再生 — arm_sdk でCSV腕・腰関節データを再生

CSV の関節値（度）をラジアン変換して arm_sdk へ送信する。
脚・腰ロール/ピッチは arm_sdk で制御不可のためスキップ。

フェーズ:
  1. 現在姿勢 → CSV 1フレーム目 へスムーズ移行 (BLEND_SEC)
  2. CSV 全フレーム再生 (fps / speed で速度調整)
  3. 最終フレーム → ニュートラル へスムーズ移行 (BLEND_SEC)
  4. arm_sdk 解除 (RELEASE_SEC)

Usage:
    python demo/play_harebare.py <networkInterface> [fps] [speed]
    例) python demo/play_harebare.py eth0
        python demo/play_harebare.py eth0 30
        python demo/play_harebare.py eth0 30 0.5   # 0.5倍速
"""

import math
import os
import sys
import time

import numpy as np

from unitree_sdk2py.core.channel import (
    ChannelPublisher,
    ChannelSubscriber,
    ChannelFactoryInitialize,
)
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowState_
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_, LowState_
from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread

# ----------------------------------------------------------------
# CSV ファイルパス（このスクリプトと同じフォルダ）
# ----------------------------------------------------------------
CSV_PATH = os.path.join(os.path.dirname(__file__), "harebare.csv")

# ----------------------------------------------------------------
# CSV列名 → SDK 関節インデックス（arm_sdk で制御可能な関節のみ）
# 腰ロール(13)・腰ピッチ(14) は物理的にロックされているためスキップ
# ----------------------------------------------------------------
JOINT_MAP: dict[str, int] = {
    "waist_yaw_joint_dof":            12,
    "left_shoulder_pitch_joint_dof":  15,
    "left_shoulder_roll_joint_dof":   16,
    "left_shoulder_yaw_joint_dof":    17,
    "left_elbow_joint_dof":           18,
    "left_wrist_roll_joint_dof":      19,
    "right_shoulder_pitch_joint_dof": 22,
    "right_shoulder_roll_joint_dof":  23,
    "right_shoulder_yaw_joint_dof":   24,
    "right_elbow_joint_dof":          25,
    "right_wrist_roll_joint_dof":     26,
}

KWEIGHT = 29          # arm_sdk 有効/無効ウェイト関節インデックス
BLEND_SEC   = 2.0     # ブレンド移行秒数
RELEASE_SEC = 0.5     # arm_sdk 解除秒数
CONTROL_DT  = 0.02    # 制御ループ周期 (50 Hz)


# ----------------------------------------------------------------
# CSV ロード
# ----------------------------------------------------------------

def load_csv(path: str) -> tuple[list[str], list[list[float]]]:
    """
    Returns:
        col_names : ヘッダー列名リスト (Frame 含む)
        frames    : 各フレームの float 値リスト (Frame 列除く)
    """
    with open(path, "r") as f:
        lines = f.read().splitlines()

    col_names = [c.strip() for c in lines[0].split(",")]
    frames: list[list[float]] = []
    for line in lines[1:]:
        if not line.strip():
            continue
        vals = [float(v) for v in line.split(",")]
        frames.append(vals[1:])  # Frame 列をスキップ

    data_cols = col_names[1:]  # Frame 列を除いたカラム名
    return data_cols, frames


def build_joint_sequence(
    col_names: list[str],
    frames: list[list[float]],
) -> list[dict[int, float]]:
    """
    各フレームを {SDK関節インデックス: 角度(rad)} の辞書リストへ変換。
    CSV値は度単位なのでラジアンへ変換する。
    """
    col_idx = {name: i for i, name in enumerate(col_names)}
    sequence: list[dict[int, float]] = []

    for frame_vals in frames:
        pose: dict[int, float] = {}
        for col_name, joint_idx in JOINT_MAP.items():
            if col_name in col_idx:
                deg = frame_vals[col_idx[col_name]]
                pose[joint_idx] = math.radians(deg)
        sequence.append(pose)

    return sequence


# ----------------------------------------------------------------
# 再生クラス
# ----------------------------------------------------------------

class HarebarePlayer:
    def __init__(
        self,
        sequence: list[dict[int, float]],
        fps: float = 30.0,
        speed: float = 1.0,
    ):
        self.sequence   = sequence
        self.frame_dt   = 1.0 / (fps * speed)  # 1フレームの実時間
        self.kp         = 60.0
        self.kd         = 1.5
        self.control_dt = CONTROL_DT

        self.low_cmd    = unitree_hg_msg_dds__LowCmd_()
        self.low_state  = None
        self.first_state = False
        self.done       = False
        self.crc        = CRC()

        self._time      = 0.0
        self._frame_acc = 0.0   # フレーム累積時間

        # フェーズ管理
        self._phase       = "blend_in"
        self._blend_start = None  # ブレンド開始時の関節角スナップショット

    # ---- チャンネル初期化 ----

    def init(self) -> None:
        self.pub = ChannelPublisher("rt/arm_sdk", LowCmd_)
        self.pub.Init()
        self.sub = ChannelSubscriber("rt/lowstate", LowState_)
        self.sub.Init(self._state_cb, 10)

    def start(self) -> None:
        self.thread = RecurrentThread(
            interval=self.control_dt, target=self._write, name="harebare"
        )
        print("LowState 受信待機中...")
        while not self.first_state:
            time.sleep(0.1)

        # ブレンド開始姿勢を記録
        joints = list(JOINT_MAP.values())
        self._blend_start = {j: self.low_state.motor_state[j].q for j in joints}
        self._phase_time  = 0.0

        self.thread.Start()

    # ---- コールバック ----

    def _state_cb(self, msg: LowState_) -> None:
        self.low_state   = msg
        self.first_state = True

    # ---- 関節セット ----

    def _set_joint(self, joint: int, q: float) -> None:
        self.low_cmd.motor_cmd[joint].tau = 0.0
        self.low_cmd.motor_cmd[joint].q   = q
        self.low_cmd.motor_cmd[joint].dq  = 0.0
        self.low_cmd.motor_cmd[joint].kp  = self.kp
        self.low_cmd.motor_cmd[joint].kd  = self.kd

    # ---- 制御ループ ----

    def _write(self) -> None:
        self._phase_time += self.control_dt

        if self._phase == "blend_in":
            self._do_blend_in()
        elif self._phase == "play":
            self._do_play()
        elif self._phase == "blend_out":
            self._do_blend_out()
        elif self._phase == "release":
            self._do_release()
        else:
            self.done = True
            return

        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.pub.Write(self.low_cmd)

    def _ease(self, t: float, total: float) -> float:
        r = max(0.0, min(1.0, t / total))
        return 0.5 - 0.5 * math.cos(math.pi * r)

    def _blend_in(self, ratio: float, target: dict[int, float]) -> None:
        """現在姿勢 → target へ補間"""
        self.low_cmd.motor_cmd[KWEIGHT].q = 1.0
        for joint, q_tgt in target.items():
            q_src = self._blend_start.get(joint, 0.0)
            self._set_joint(joint, (1.0 - ratio) * q_src + ratio * q_tgt)

    def _do_blend_in(self) -> None:
        ratio = self._ease(self._phase_time, BLEND_SEC)
        self._blend_in(ratio, self.sequence[0])
        if self._phase_time >= BLEND_SEC:
            self._phase      = "play"
            self._phase_time = 0.0
            self._frame_acc  = 0.0
            self._cur_frame  = 0
            print(f"再生開始: {len(self.sequence)} フレーム")

    def _do_play(self) -> None:
        self._frame_acc += self.control_dt
        # 経過時間から現在フレームを決定
        self._cur_frame = min(
            int(self._frame_acc / self.frame_dt),
            len(self.sequence) - 1,
        )
        pose = self.sequence[self._cur_frame]
        self.low_cmd.motor_cmd[KWEIGHT].q = 1.0
        for joint, q in pose.items():
            self._set_joint(joint, q)

        if self._cur_frame >= len(self.sequence) - 1:
            # 最終フレームに到達
            self._last_pose  = dict(self.sequence[-1])
            # ブレンドアウト用に現在の実関節角をスナップショット
            self._blend_start = {
                j: self.low_state.motor_state[j].q for j in self._last_pose
            }
            self._phase      = "blend_out"
            self._phase_time = 0.0
            print("再生完了、ニュートラルへ戻ります")

    def _do_blend_out(self) -> None:
        ratio = self._ease(self._phase_time, BLEND_SEC)
        self.low_cmd.motor_cmd[KWEIGHT].q = 1.0
        for joint in self._last_pose:
            q_src = self._blend_start.get(joint, 0.0)
            self._set_joint(joint, (1.0 - ratio) * q_src)  # → 0 (ニュートラル)
        if self._phase_time >= BLEND_SEC:
            self._phase      = "release"
            self._phase_time = 0.0

    def _do_release(self) -> None:
        ratio = max(0.0, min(1.0, self._phase_time / RELEASE_SEC))
        self.low_cmd.motor_cmd[KWEIGHT].q = 1.0 - ratio
        if self._phase_time >= RELEASE_SEC:
            self._phase = "done"


# ----------------------------------------------------------------
# エントリポイント
# ----------------------------------------------------------------

def run_harebare(fps: float = 30.0, speed: float = 1.0) -> None:
    """
    ChannelFactoryInitialize 済みの前提で呼ぶ。
    他スクリプトから import して使う。
    """
    col_names, frames = load_csv(CSV_PATH)
    sequence = build_joint_sequence(col_names, frames)
    print(f"harebare.csv 読み込み完了: {len(sequence)} フレーム / {fps} fps / {speed}x 速度")

    player = HarebarePlayer(sequence, fps=fps, speed=speed)
    player.init()
    player.start()

    while not player.done:
        time.sleep(0.1)
    print("harebare モーション完了")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <networkInterface> [fps] [speed]")
        print("  fps   : フレームレート (default: 30)")
        print("  speed : 再生速度倍率  (default: 1.0 / 例: 0.5 で半速)")
        sys.exit(-1)

    net   = sys.argv[1]
    fps   = float(sys.argv[2]) if len(sys.argv) >= 3 else 30.0
    speed = float(sys.argv[3]) if len(sys.argv) >= 4 else 1.0

    print("WARNING: ロボット周辺に障害物がないことを確認してください。")
    input("準備ができたら Enter を押してください...")

    ChannelFactoryInitialize(0, net)
    run_harebare(fps=fps, speed=speed)
