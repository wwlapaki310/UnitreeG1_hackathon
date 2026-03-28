"""
正座モーション — StandUp2Squat でしゃがみ姿勢を保持する

G1 に本来の正座 API はないため、StandUp2Squat を正座の代替として使う。
stand_up=False にすると立ち上がらずに返るので、
続けて茶筅モーションを呼び出すシーンで使える。

Usage:
    python seiza.py <networkInterface> [hold_sec]
    例) python seiza.py eth0 5
"""

import time
import sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient


def seiza(sport_client: LocoClient, hold_sec: float = 5.0, stand_up: bool = True) -> None:
    """
    正座（しゃがみ）姿勢を取る。

    Args:
        sport_client: 初期化済み LocoClient
        hold_sec:     正座を維持する秒数
        stand_up:     True なら hold_sec 後に自動で起立する
    """
    print("正座します...")
    sport_client.StandUp2Squat()
    time.sleep(1.5)  # モーション完了を待つ

    if hold_sec > 0:
        print(f"正座 {hold_sec}秒 保持中...")
        time.sleep(hold_sec)

    if stand_up:
        print("起立します...")
        sport_client.Squat2StandUp()
        time.sleep(1.5)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <networkInterface> [hold_sec]")
        print("  例) python seiza.py eth0 5")
        sys.exit(-1)

    hold_sec = float(sys.argv[2]) if len(sys.argv) >= 3 else 5.0

    print("WARNING: ロボット周辺に障害物がないことを確認してください。")
    input("準備ができたら Enter を押してください...")

    ChannelFactoryInitialize(0, sys.argv[1])

    sport_client = LocoClient()
    sport_client.SetTimeout(10.0)
    sport_client.Init()

    seiza(sport_client, hold_sec=hold_sec, stand_up=True)
    print("完了")
