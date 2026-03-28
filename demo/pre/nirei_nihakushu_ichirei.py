"""
二礼二拍手一礼 — 神社参拝の作法をG1に実行させるスクリプト

Usage:
    macOS : python nirei_nihakushu_ichirei.py en11
    WSL2  : python nirei_nihakushu_ichirei.py eth0
"""

import time
import sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map


def bow(sport_client: LocoClient, hold_sec: float = 2.0) -> None:
    """LowStand → wait → HighStand で「礼」を表現"""
    sport_client.LowStand()
    time.sleep(hold_sec)
    sport_client.HighStand()
    time.sleep(2.0)  # 元の高さに戻るまで待つ


def clap(arm_client: G1ArmActionClient, wait_sec: float = 2.5) -> None:
    """clap アクションで「拍手」"""
    arm_client.ExecuteAction(action_map.get("clap"))
    time.sleep(wait_sec)  # アクション完了を待つ


def nirei_nihakushu_ichirei(sport_client: LocoClient, arm_client: G1ArmActionClient) -> None:
    print("=== 二礼二拍手一礼 開始 ===")

    print("[1/5] 一礼目...")
    bow(sport_client)

    print("[2/5] 二礼目...")
    bow(sport_client)

    print("[3/5] 一拍手...")
    clap(arm_client)

    print("[4/5] 二拍手...")
    clap(arm_client)

    print("[5/5] 一礼...")
    bow(sport_client)

    # アームを定位置に戻す
    arm_client.ExecuteAction(action_map.get("release arm"))
    time.sleep(1.0)

    print("=== 完了 ===")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <networkInterface>")
        print("  macOS : python nirei_nihakushu_ichirei.py en11")
        print("  WSL2  : python nirei_nihakushu_ichirei.py eth0")
        sys.exit(-1)

    print("WARNING: ロボット周辺に障害物がないことを確認してください。")
    input("準備ができたら Enter を押してください...")

    ChannelFactoryInitialize(0, sys.argv[1])

    sport_client = LocoClient()
    sport_client.SetTimeout(10.0)
    sport_client.Init()

    arm_client = G1ArmActionClient()
    arm_client.SetTimeout(10.0)
    arm_client.Init()

    nirei_nihakushu_ichirei(sport_client, arm_client)
