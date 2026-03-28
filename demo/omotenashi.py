"""
おもてなし — G1 による歓迎シーケンス

流れ:
  1. お辞儀（LowStand）
  2. 大きく手を振る（high wave）    ← いらっしゃいませ
  3. ハート（heart）               ← ようこそ
  4. 握手（shake hand）            ← よろしくお願いします
  5. お辞儀（LowStand）

Usage:
    python demo/omotenashi.py <networkInterface>
    例) python demo/omotenashi.py eth2
"""

import sys
import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map


def bow(loco: LocoClient, hold_sec: float = 3.0) -> None:
    loco.LowStand()
    time.sleep(hold_sec)
    loco.HighStand()
    time.sleep(3.0)


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

    print("=== おもてなし 開始 ===")

    print("[1/5] お辞儀...")
    bow(loco)

    print("[2/5] いらっしゃいませ（high wave）...")
    arm.ExecuteAction(action_map["high wave"])
    time.sleep(5.0)

    print("[3/5] ようこそ（heart）...")
    arm.ExecuteAction(action_map["heart"])
    time.sleep(5.0)

    print("[4/5] よろしくお願いします（shake hand）...")
    arm.ExecuteAction(action_map["shake hand"])
    time.sleep(5.0)

    print("[5/5] お辞儀...")
    bow(loco)

    arm.ExecuteAction(action_map["release arm"])
    time.sleep(2.0)

    print("=== 完了 ===")


if __name__ == "__main__":
    main()
