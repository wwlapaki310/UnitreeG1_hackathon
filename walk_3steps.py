"""G1 3歩前進"""
import sys
import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.loco.g1_loco_client import LocoClient

def main():
    iface = sys.argv[1] if len(sys.argv) > 1 else "en11"
    print(f"Connecting via {iface}...")
    ChannelFactoryInitialize(0, iface)

    client = LocoClient()
    client.SetTimeout(10.0)
    client.Init()

    print("3歩前進します...")
    client.Move(0.2, 0, 0)   # 前進 0.2 m/s（ゆっくり）
    time.sleep(3)             # 約3歩分
    client.Move(0, 0, 0)     # 停止
    print("停止しました")

if __name__ == "__main__":
    main()
