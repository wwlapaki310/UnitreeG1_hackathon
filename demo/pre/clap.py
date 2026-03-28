"""G1 一本締め — G1内蔵スピーカーで WAV 再生 → Clap 3回

音声１（WAV_PRE）→ Clap 3回 → 音声２（WAV_POST）の順で実行します。
音声ファイルは WAV_PRE / WAV_POST 定数を変更してください。

Usage:
    python demo/clap.py <networkInterface>
    例) python demo/clap.py eth2
"""

import sys
import time
import wave
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient, action_map
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient

APP_NAME = "clap_demo"
STREAM_ID = "ippon"

# ---- 音声ファイルパス（ここを変更してください） ----
WAV_PRE  = "demo/ippon.wav"   # clap 前に流す音声
WAV_POST = "demo/clap.wav"  # clap 後に流す音声
# ------------------------------------------------


def play_wav_on_robot(audio: AudioClient, path: str) -> None:
    """WAV ファイルの PCM データを G1 内蔵スピーカーで再生"""
    try:
        with wave.open(path, "rb") as wf:
            pcm_data = wf.readframes(wf.getnframes())
        code, _ = audio.PlayStream(APP_NAME, STREAM_ID, pcm_data)
        print(f"PlayStream code: {code}")
    except FileNotFoundError:
        print(f"[警告] WAV ファイルが見つかりません: {path}")
    except Exception as e:
        print(f"[警告] 音声再生に失敗しました: {e}")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <networkInterface>")
        sys.exit(-1)

    ChannelFactoryInitialize(0, sys.argv[1])

    audio = AudioClient()
    audio.SetTimeout(10.0)
    audio.Init()

    code, vol = audio.GetVolume()
    print(f"現在の音量: {vol} (code: {code})")
    audio.SetVolume(80)
    print("音量を 80 に設定しました")

    arm = G1ArmActionClient()
    arm.SetTimeout(10.0)
    arm.Init()

    # 音声１
    print(f"音声１再生: {WAV_PRE}")
    play_wav_on_robot(audio, WAV_PRE)
    time.sleep(1.0)

    # Clap 3回
    for i in range(1, 4):
        print(f"一本締め {i}/3...")
        arm.ExecuteAction(action_map["clap"])
        time.sleep(4.0)

    # 音声２
    print(f"音声２再生: {WAV_POST}")
    play_wav_on_robot(audio, WAV_POST)
    time.sleep(1.0)

    audio.PlayStop(APP_NAME)

    print("腕を戻します")
    arm.ExecuteAction(action_map["release arm"])
    time.sleep(2.0)
    print("完了")


if __name__ == "__main__":
    main()
