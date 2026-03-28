"""一本締め — TTS + Clap

流れ:
  1. TTS「皆さん本日はお疲れさまでした。お手を拝借」
  2. TTS「よ～」
  3. Clap（一本締め）
  4. TTS「パチパチパチ」

Usage:
    python demo/ippon_jime.py <networkInterface>
    例) python demo/ippon_jime.py eth2
"""

import sys
import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient

VOLUME = 100


def tts(audio: AudioClient, text: str, wait_sec: float) -> None:
    print(f"[TTS] {text}")
    audio.TtsMaker(text, 1)
    time.sleep(wait_sec)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <networkInterface>")
        sys.exit(-1)

    ChannelFactoryInitialize(0, sys.argv[1])

    audio = AudioClient()
    audio.SetTimeout(10.0)
    audio.Init()
    audio.SetVolume(VOLUME)

    arm = G1ArmActionClient()
    arm.SetTimeout(10.0)
    arm.Init()

    print("=== 一本締め 開始 ===")

    tts(audio, "Everyone, thank you for your hard work today. Please clap your hands.", 5.0)

    tts(audio, "Hey!", 2.0)

    for i in range(1, 4):
        print(f"[Clap] 一本締め {i}/3...")
        arm.ExecuteAction(action_map["clap"])
        time.sleep(4.0)

    tts(audio, "Thanks for today, yeah!", 3.0)

    arm.ExecuteAction(action_map["release arm"])
    time.sleep(2.0)

    print("=== 完了 ===")


if __name__ == "__main__":
    main()
