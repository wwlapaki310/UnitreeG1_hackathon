"""G1 ばんざい"""
import sys
import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map

def main():
    iface = sys.argv[1] if len(sys.argv) > 1 else "en11"
    print(f"Connecting via {iface}...")
    ChannelFactoryInitialize(0, iface)

    client = G1ArmActionClient()
    client.SetTimeout(10.0)
    client.Init()

    print("ばんざい！")
    client.ExecuteAction(action_map.get("hands up"))
    time.sleep(3)

    print("腕を戻します")
    client.ExecuteAction(action_map.get("release arm"))
    time.sleep(1)
    print("完了")

if __name__ == "__main__":
    main()
