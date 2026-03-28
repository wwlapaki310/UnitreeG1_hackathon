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
