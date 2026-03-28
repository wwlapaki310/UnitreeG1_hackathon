# UnitreeG1 Hackathon

**テーマ：**


---

## コンセプト


---

## システム構成



---

## ディレクトリ構成

```
UnitreeG1_hackathon/
├── capture/
│   └── pose_estimator.py       # MediaPipe骨格取得＋保存
├── mapping/
│   └── joint_mapper.py         # G1関節角度変換・フィルタリング
├── simulator/
│   └── g1_player.py            # unitree_mujoco再生
├── data/
│   └── sample_motion.json      # 事前収録モーション
└── README.md
```

---

## セットアップ

```bash
# 依存関係
pip install mediapipe opencv-python scipy numpy

# unitree_sdk2_python
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git
cd unitree_sdk2_python
pip install -e .
```

---

## デモ一覧

| ファイル | 内容 | 使用API |
|---|---|---|
| `demo/nirei_nihakushu_ichirei.py` | 二礼二拍手一礼（神社参拝） | LocoClient + ArmAction |
| `demo/omotenashi.py` | おもてなし歓迎シーケンス | LocoClient + ArmAction |
| `demo/otemae.py` | お点前（茶道風） | LocoClient + ArmAction |
| `demo/play_harebare.py` | 晴れ晴れモーション再生（CSV） | arm_sdk 低レベル制御 |
| `demo/clap.py` | 拍手単体テスト | ArmAction |

**共通の実行方法**

```bash
python demo/<スクリプト名>.py <ネットワークインターフェース名>
# 例
python demo/omotenashi.py eth2
```

**インターフェース名の確認**

| 環境 | コマンド | 例 |
|---|---|---|
| WSL2 | `ip a` | `eth2` |
| macOS | `ifconfig` | `en11` |

**共通の注意事項**

- 実行前にロボット周辺 **1m 以上**の空間を確保してください
- Enter 入力後にモーションが開始します
- 緊急停止はコントローラーの `L2+A` で行ってください

---

## デモ詳細

### 二礼二拍手一礼（`nirei_nihakushu_ichirei.py`）

神社参拝の作法を再現します。

| ステップ | 動作 | アクション |
|---|---|---|
| 1 | 一礼 | LowStand |
| 2 | 二礼 | LowStand |
| 3 | 一拍手 | clap |
| 4 | 二拍手 | clap |
| 5 | 一礼 | LowStand |

```bash
python demo/nirei_nihakushu_ichirei.py eth2
```

---

### おもてなし（`omotenashi.py`）

来客を迎える歓迎シーケンスです。

| ステップ | 動作 | アクション |
|---|---|---|
| 1 | お辞儀 | LowStand |
| 2 | いらっしゃいませ | high wave |
| 3 | ようこそ | heart |
| 4 | よろしくお願いします | shake hand |
| 5 | お辞儀 | LowStand |

```bash
python demo/omotenashi.py eth2
```

---

### お点前（`otemae.py`）

茶道の所作を定義済みアクションで表現します。

| ステップ | 動作 | アクション |
|---|---|---|
| 1 | 一礼 | LowStand |
| 2 | お湯を注ぐ | right hand up |
| 3 | 茶筅で点てる | clap |
| 4 | お茶をどうぞ | shake hand |
| 5 | 一礼 | LowStand |

```bash
python demo/otemae.py eth2
```

---

## デモ：晴れ晴れモーション再生

`demo/` フォルダに収録した腕・腰モーションをG1実機で再生します。

### ファイル構成

```
demo/
├── harebare.csv       # モーションデータ（関節角度、度単位）
└── play_harebare.py   # CSV をアームSDKへ送信して再生するスクリプト
```

### 前提条件

- G1がスポーツモードで起動済み
- 開発PCがG1と同じネットワーク（192.168.123.x）に接続済み
- `unitree_sdk2_python` がインストール済み（`pip install -e ./unitree_sdk2_python`）

### 実行方法

```bash
# 基本（30fps・等速）
python demo/play_harebare.py <ネットワークインターフェース名>

# fps・速度を指定する場合
python demo/play_harebare.py <ネットワークインターフェース名> [fps] [speed]
```

**インターフェース名の確認方法**

| 環境 | コマンド | 例 |
|---|---|---|
| WSL2 | `ip a` | `eth1` |
| macOS | `ifconfig` | `en11` |

**実行例**

```bash
# WSL2 から eth1 で接続
python demo/play_harebare.py eth1

# 0.5倍速で再生
python demo/play_harebare.py eth1 30 0.5
```

### 動作の流れ

1. 現在の姿勢 → CSV 1フレーム目へスムーズ移行（2秒）
2. CSV 全フレーム再生
3. 最終フレーム → ニュートラル姿勢へスムーズ移行（2秒）
4. arm_sdk 解除

### 注意事項

- 実行前にロボット周辺 **1m 以上**の空間を確保してください
- Enter 入力後にモーションが開始します
- 緊急停止はコントローラーの `L2+A` で行ってください

---

## G1 仕様メモ

| 項目 | 値 |
|---|---|
| 自由度（本体） | 29 DoF |
| 腕 | 7 DoF × 2（肩3＋肘1＋手首2＋手先1） |
| 腰 | 3 DoF |
| 脚 | 6 DoF × 2 |
| 身長 | 約127cm |
| 計算モジュール | Jetson Orin NX 16GB |
| 低レベル通信 | unitree_hg（DDS） |
| 制御周波数 | 500Hz |
