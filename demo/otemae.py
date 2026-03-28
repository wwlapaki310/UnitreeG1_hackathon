"""
お点前 — G1 による茶道風シーケンス

定義済みアクションのみ使用（安全第一）

流れ:
  1. お辞儀（LowStand）           ← 一礼
  2. right hand up               ← お湯を注ぐ
  3. clap                        ← 茶筅で点てる
  4. shake hand                  ← お茶をどうぞ
  5. お辞儀（LowStand）           ← 一礼

Usage:
    python demo/otemae.py <networkInterface>
    例) python demo/otemae.py eth2
"""

import sys
import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map


def bow(loco: LocoClient, hold_sec: float = 3.0) -> None:
    """LowStand → wait → HighStand で一礼"""
    loco.LowStand()
    time.sleep(hold_sec)
    loco.HighStand()
    time.sleep(3.0)  # 姿勢が安定するまで待つ


def do_action(arm: G1ArmActionClient, name: str, wait_sec: float = 5.0) -> None:
    arm.ExecuteAction(action_map[name])
    time.sleep(wait_sec)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <networkInterface>")
        sys.exit(-1)

    print("WARNING: ロボット周辺に障害物がないことを確認してください。")
    input("準備ができたら Enter を押してください...")

    ChannelFactoryInitialize(0, sys.argv[1])

    loco = LocoClient()
    loco.SetTimeout(10.0)
    loco.Init()

    arm = G1ArmActionClient()
    arm.SetTimeout(10.0)
    arm.Init()

    print("=== お点前 開始 ===")

    print("[1/5] 一礼...")
    bow(loco)

    print("[2/5] お湯を注ぎます（right hand up）...")
    do_action(arm, "right hand up", wait_sec=5.0)

    print("[3/5] 茶筅で点てます（clap）...")
    do_action(arm, "clap", wait_sec=6.0)

    print("[4/5] お茶をどうぞ（shake hand）...")
    do_action(arm, "shake hand", wait_sec=5.0)

    print("[5/5] 一礼...")
    bow(loco)

    arm.ExecuteAction(action_map["release arm"])
    time.sleep(2.0)

    print("=== お点前 完了 ===")


if __name__ == "__main__":
    main()
