# HomeBot - KTC MegPad + Open Claw 家庭用ロボット

KTC MegPad 27インチスマートモニターを「顔」として、Open Clawロボットグリッパーで物体操作を行う家庭用移動ロボットシステム。

## システム構成

```
┌─────────────────────────────────────────────┐
│              HomeBot システム構成              │
├─────────────────────────────────────────────┤
│                                             │
│   ┌───────────────────────┐                 │
│   │  KTC MegPad 27"       │  ← 顔/UI       │
│   │  (Android 14 FHD)     │    表情表示      │
│   │  WiFi/BT5.1           │    ステータス     │
│   └───────────┬───────────┘                 │
│               │                             │
│   ┌───────────┴───────────┐                 │
│   │  Raspberry Pi 4/5     │  ← メイン制御    │
│   │  (メインコントローラー)   │                 │
│   └──┬────────┬────────┬──┘                 │
│      │        │        │                    │
│  ┌───┴──┐ ┌──┴───┐ ┌──┴──────┐            │
│  │Open  │ │移動   │ │センサー   │            │
│  │Claw  │ │ベース  │ │LiDAR    │            │
│  │5軸   │ │4輪    │ │深度カメラ │            │
│  │アーム │ │メカナム│ │超音波    │            │
│  └──────┘ └──────┘ └─────────┘            │
│                                             │
└─────────────────────────────────────────────┘
```

## 必要なハードウェア

| パーツ | 型番/推奨品 | 用途 |
|--------|------------|------|
| ディスプレイ | KTC MegPad 27" (A27Q7) | 顔/UI表示 |
| ロボットアーム | Open Claw 5軸 | 物体の把持・操作 |
| メインコントローラー | Raspberry Pi 4B/5 (8GB) | 全体制御 |
| 移動ベース | メカナムホイール4輪 | 全方向移動 |
| モータードライバー | L298N x2 / 専用ドライバー | モーター制御 |
| LiDAR | RPLIDAR A1 | 地図作成・障害物検出 |
| 深度カメラ | Intel RealSense D435 | 物体認識 |
| バッテリー | 12V 20Ah LiFePO4 | 電源 |
| フレーム | アルミフレーム + 3Dプリント | 構造体 |

## 組み立てガイド

### Step 1: フレーム組み立て
```
        ┌──────────────────┐
        │    MegPad 27"    │  ← VESA/スタンドで固定
        │   (顔ディスプレイ)  │
        └────────┬─────────┘
                 │  スタンドポール
        ┌────────┴─────────┐
        │  Raspberry Pi    │  ← 背面に取り付け
        │  + センサー類      │
        ├──────────────────┤
        │   Open Claw      │  ← 前面にアーム取り付け
        │   ロボットアーム    │
        ├──────────────────┤
        │   バッテリー       │
        ├──┬──────────┬──┤
        │  ⚙  メカナム  ⚙  │  ← 4輪移動ベース
        └──┴──────────┴──┘
```

1. アルミフレーム（40x40cm）で移動ベースを組み立て
2. 4つのメカナムホイールを四隅に取り付け
3. バッテリーをベース中央に固定
4. 支柱（高さ約100cm）を立てる
5. MegPadをスタンドポールの上部に取り付け（コードレス設計を活用）
6. Open Clawアームを支柱中央部に取り付け
7. Raspberry Piを支柱背面に固定
8. LiDARをベース前面上部に設置
9. 深度カメラをMegPad下部に固定

### Step 2: 配線
```
Raspberry Pi GPIO/Serial:
  ├── /dev/ttyUSB0 → Open Claw (Arduino経由)
  ├── /dev/ttyUSB1 → 移動ベース (モータードライバー)
  ├── /dev/ttyUSB2 → RPLIDAR A1
  ├── USB → Intel RealSense D435
  └── WiFi → KTC MegPad (ADB接続)
```

### Step 3: MegPad設定
1. MegPadの電源をON（内蔵バッテリーまたは65Wアダプター）
2. WiFiでRaspberry Piと同じネットワークに接続
3. 開発者オプションでADBデバッグを有効化
4. ブラウザでRaspberry PiのIPアドレス:5000にアクセス
5. ロボットの顔UIが表示される

## セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/sabobo0406/sabobo0406.git
cd sabobo0406

# 依存パッケージをインストール
pip install -r requirements.txt

# ロボットを起動
python -m home_robot.control.robot_controller --config home_robot/config/robot_config.yaml
```

## 使い方（対話モード）

```
HomeBot> go kitchen          # キッチンに移動
HomeBot> fetch cup kitchen   # キッチンからカップを取ってくる
HomeBot> patrol              # 家の中を巡回
HomeBot> greet               # 挨拶
HomeBot> status              # ステータス表示
HomeBot> locations           # 登録場所一覧
HomeBot> quit                # シャットダウン
```

## できること

- **物を取ってくる**: 指定した場所から物を掴んで持ってくる
- **巡回**: 家の中を定期的に見回り
- **挨拶**: 人を検出して表情豊かに挨拶
- **片付け**: 散らかった物を元の場所に戻す
- **追従**: 人について歩く
- **表情表示**: MegPadの大画面で豊かな表情を表現

## プロジェクト構造

```
home_robot/
├── config/
│   └── robot_config.yaml     # ロボット設定ファイル
├── hardware/
│   ├── open_claw.py          # Open Clawグリッパー制御
│   └── mobile_base.py        # メカナムホイール移動ベース
├── display/
│   └── face_ui.py            # MegPad顔UI (Flask+WebSocket)
├── navigation/
│   ├── sensors.py            # センサーデータ管理
│   └── path_planner.py       # A*経路計画
├── control/
│   └── robot_controller.py   # メインオーケストレーター
└── tasks/
    └── home_tasks.py         # 家庭内タスク定義
```

## ライセンス

MIT License
