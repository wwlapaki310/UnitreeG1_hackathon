# UnitreeG1 Hackathon

**テーマ：遠く離れた人、もう会えない人の動きをロボットで再現する**

Unitree G1 を使い、MediaPipe で取得した人の骨格情報をリアルタイムまたは収録済み動画からロボットの動作として再現するプロジェクトです。

---

## コンセプト

- カメラ1台で人の動きを骨格推定（MediaPipe）
- 関節角度に変換し、Unitree G1（29DoF）へマッピング
- 「会えない人の動き」を事前収録しておき、当日ロボットで再現

---

## システム構成

```
動画 / カメラ入力
    ↓
MediaPipe Pose（33点 3D骨格）
    ↓
① 欠損補間（visibility < 0.5）
② 身長正規化（体幹長=1.0）
③ 関節角度計算
④ ローパスフィルタ（3Hz）
⑤ G1可動域クリップ
⑥ 速度制限
    ↓
motion.json 保存
    ↓
unitree_sdk2_python / unitree_mujoco で再生
```

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
