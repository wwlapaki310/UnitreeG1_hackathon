# 和のコゝロ — Unitree G1 Hackathon

**テーマ：ロボットと生きる未来をデザインするハッカソン（RobotMateHub）**

---

## コンセプト

おもてなしの所作と会話で、**"ちょっと嬉しい"** を届けるロボット。

効率化のためのロボットではなく、人の心に寄り添うロボットを目指しました。
「やらなくていいこと」ではなく、**「やってくれたら嬉しいこと」** にこそ価値があると考え、
和の所作（礼・拍手・お点前）を Unitree G1 に実装しました。

---

## ディレクトリ構成

```
UnitreeG1_hackathon/
├── demo/                        # G1 実機動作スクリプト
│   ├── nirei_nihakushu_ichirei.py   # 二礼二拍手一礼
│   ├── omotenashi.py                # おもてなし歓迎シーケンス
│   ├── otemae.py                    # お点前（茶道風）
│   ├── ippon_jime.py                # 一本締め（TTS + Clap）
│   ├── play_harebare.py             # CSVモーション再生
│   └── harebare.csv                 # モーションデータ
├── movie2motion/                # 動画 → G1モーションCSV 生成
│   └── movie2motion.ipynb           # Colaboratory用 Notebook
├── slides/                      # 発表スライド
│   └── index.html
├── unitree_sdk2_python/         # Unitree Python SDK
└── reference/                   # サンプルコード
```

---

## セットアップ

```bash
# unitree_sdk2_python（Python 3.10 推奨）
pip install -e ./unitree_sdk2_python
```

**ネットワーク設定**

| デバイス | IP |
|---|---|
| 開発PC | 192.168.123.99 |
| Jetson Orin（G1内部） | 192.168.123.164 |

---

## demo/ — G1 実機動作スクリプト

### 共通の実行方法

```bash
python demo/<スクリプト名>.py <ネットワークインターフェース名>
# 例
python demo/omotenashi.py eth2
```

| 環境 | インターフェース確認 | 例 |
|---|---|---|
| WSL2 | `ip a` | `eth2` |
| macOS | `ifconfig` | `en11` |

**注意事項**
- 実行前にロボット周辺 **1m 以上**の空間を確保してください
- Enter 入力後にモーションが開始します
- 緊急停止はコントローラーの `L2+A` で行ってください

---

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

### 一本締め（`ippon_jime.py`）

TTS アナウンス → Clap × 3回 の一本締めシーケンスです。

| ステップ | 内容 |
|---|---|
| TTS | "Everyone, thank you for your hard work today. Please clap your hands." |
| TTS | "Hey!" |
| Clap × 3 | 一本締め |
| TTS | "Thanks for today, yeah!" |

```bash
python demo/ippon_jime.py eth2
```

---

### CSVモーション再生（`play_harebare.py`）

`harebare.csv` の関節角度データを arm_sdk で再生します。

```bash
# 基本（30fps・等速）
python demo/play_harebare.py eth2

# fps・速度を指定
python demo/play_harebare.py eth2 30 0.5   # 0.5倍速
```

---

## movie2motion/ — 動画からG1モーションCSVを生成

おもてなしの所作をロボットに直接実装するのは難しい。
そこで **人の動画からモーションを自動生成する仕組み** を構築しました。

### パイプライン

```
mp4 動画
  ↓ Step 1-2: GEM-X
SOMA BVH（77関節 3Dポーズ）
  ↓ Step 3-4: SOMA Retargeter
G1 関節CSV（29 DOF）
```

### 使い方

`movie2motion/movie2motion.ipynb` を Google Colaboratory で開いて実行してください。

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/)

**参考：** [NVlabs/GEM-X](https://github.com/NVlabs/GEM-X)

> ※ 今回は安定性が確保できず実機動作は断念。Colaboratory の構築と CSV 生成までを実装・公開しています。

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
