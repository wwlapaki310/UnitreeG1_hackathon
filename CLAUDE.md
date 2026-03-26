# Unitree G1 Hackathon Project

## プロジェクト概要
ハッカソン「ロボットと生きる未来をデザインするハッカソン（RobotMateHub）」向けのUnitree G1ヒューマノイドロボット開発環境。
Mac / Windows 混在環境で、多くの参加者が同じ環境を構築する想定。

## 接続・環境構築
**開発環境の構築と G1 への接続手順は `05_開発環境構築＆接続手順.md` を参照してください。**
Mac / Windows 両対応の手順、ネットワーク設定、トラブルシューティングが記載されています。

## ネットワーク構成
| デバイス | IP |
|---|---|
| 開発PC | 192.168.123.99 |
| Jetson Orin（G1内部） | 192.168.123.164 |
| RockChip（ロコモーション） | 192.168.123.161 |
| LiDAR | 192.168.123.120 |

SSH と SDK（DDS）は別の通信経路です。SSH が通っても SDK が動くとは限りません。詳細は 05 を参照。

## 開発方針
- **Python SDK（unitree_sdk2_python）のみで基本開発**（Docker/ROS2不要）
- ROS2が必要になった場合（SLAM/Nav2/LiDAR）に改めてDocker環境を検討
- Python 3.10 推奨（cyclonedds==0.10.2 のビルド済みwheelが 3.7〜3.10 のみ。3.11以降は不可）

## SDK情報
- `unitree_sdk2_python` v1.0.1 (master branch)
- 依存: cyclonedds==0.10.2, numpy, opencv-python
- DDS通信: CycloneDDS 0.10.2（バージョン一致が必須、絶対に変えないこと）
- インストール: `pip install -e ./unitree_sdk2_python`

## Python SDKでできること（ROS2不要）
- 歩行制御（LocoClient: Move, Stand, Squat, WaveHand等）
- アームアクション（G1ArmActionClient: 16種のプリセット — ばんざい、拍手、ハグ等）
- 関節の個別制御（LowCmd / LowState）— 低レベル制御もPython SDKで可能
- 音声入出力
- カメラ映像取得
- コントローラー状態取得

## ROS2が必要な場面
- SLAM（FAST-LIO + LiDAR）
- Nav2（自律ナビゲーション）
- LiDAR点群処理
- RViz可視化
- G1内部は ROS2 **Foxy**（Humbleではない）

## 潜在リスク・注意点

### 1. macOS + Docker + DDS のネットワーク問題（重大）
- Docker Desktop for Mac は内部にLinux VMがあり、`--network=host` が物理LANに到達しない
- DDSマルチキャスト（239.255.0.1:7400）がVM壁を越えられない
- **結論: macOSのDockerからG1へのDDS通信は現状不可能**
- macOSでROS2が必要な場合は Multipass + ブリッジネットワークを検討

### 2. ROS2環境が必要になった場合のOS別対応
| OS | 推奨方法 | 備考 |
|---|---|---|
| Windows | WSL2 + Docker（既存Dockerfileそのまま） | .wslconfigでnetworkingMode=mirrored設定が必要 |
| macOS | Multipass + cloud-init（ブリッジネットワーク） | VMがG1と同一サブネットに参加でき、DDS問題を回避 |
| Linux | Docker --network=host | 問題なし |

### 3. 機体ごとのSDKバージョン差異
- G1の機体によって内部ファームウェア/SDKバージョンが異なる
- バージョン違いでAPIが変わる可能性（トピック名、メッセージ型、API廃止/追加）
- 事前に全パターン網羅は不可能 → 実機接続時に都度対応

### 4. Dockerfileについて
- 現在のDockerfileは `src/`（ROS2パッケージ群）と `docker/`（CycloneDDS設定）を参照するが、これらは配布物に含まれない
- Dockerfileだけではビルド不可 → ROS2環境の構成理解・AI読解用として同梱
- ベースイメージが `nvidia/cuda:12.2.2-devel-ubuntu22.04` で GPU前提

## ドキュメント構成
| ファイル | 内容 |
|---|---|
| 01_安全ガイドライン.txt | 緊急停止コマンド、安全距離、起動前チェックリスト |
| 02_開発環境セットアップ.txt | Python SDK セットアップ手順（初心者向け） |
| 03_コントローラー操作ガイド.txt | R3リモコン操作、ファームウェア別コマンド表 |
| 04_Pythonで学ぶG1基本プログラミング.txt | コピペで動くサンプル集、LocoClient解説 |
| 05_開発環境構築＆接続手順.md | **Mac/Windows対応の実機接続手順（実機検証済み）** |
| 06_API一覧_この機体.md | 特定機体で確認済みのAPI・DDSトピック一覧 |
| banzai.py | アーム動作サンプル（ばんざい） |
| walk_3steps.py | 歩行サンプル（前進） |
| Dockerfile | ROS2環境構成（AI読解用、ビルド不可） |

## プログラム実行時の注意
- SDK実行には**ネットワークインターフェース名**を引数で渡す必要がある
  - macOS: `python banzai.py en11`（`ifconfig` で確認）
  - WSL2: `python banzai.py eth0`（`ip a` で確認、再起動で名前が変わることがある）
- `Move()` の後は必ず `Move(0, 0, 0)` で停止させること
- アームアクション後は `release arm` で腕を戻すこと
