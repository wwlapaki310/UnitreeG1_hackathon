"""音声動作確認スクリプト

TTS（英語）で G1 内蔵スピーカーの動作を確認します。

Usage:
    python demo/test_audio.py <networkInterface>
    例) python demo/test_audio.py eth2
"""

import sys
import time
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <networkInterface>")
        sys.exit(-1)

    ChannelFactoryInitialize(0, sys.argv[1])

    audio = AudioClient()
    audio.SetTimeout(10.0)
    audio.Init()

    # 音量確認
    code, vol = audio.GetVolume()
    print(f"現在の音量: {vol}  (code: {code})")

    # 音量を 80 に設定
    audio.SetVolume(80)
    print("音量を 80 に設定しました")

    # TTS テスト
    print("TTS 再生中: 'Hello, I am G1 robot.'")
    code = audio.TtsMaker("Hello, I am G1 robot.", 1)
    print(f"TTS code: {code}")
    time.sleep(4.0)

    print("完了")


if __name__ == "__main__":
    main()
