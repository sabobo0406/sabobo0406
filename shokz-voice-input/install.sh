#!/usr/bin/env bash
#
# Shokz × 音声入力(方法A)ワンショットインストーラー
#
# これ1つを Mac のターミナルで実行すると、以下を自動でやります:
#   1. Homebrew があるか確認(無ければ案内)
#   2. Hammerspoon をインストール
#   3. 既存の ~/.hammerspoon/init.lua をバックアップ
#   4. このリポジトリの init.lua を配置
#   5. Hammerspoon を起動
#   6. 残りの手動ステップ(権限・Typeless 設定・マイク選択)を表示
#
# 使い方(どちらか):
#   A) リポジトリを clone 済みなら:  bash shokz-voice-input/install.sh
#   B) ネットから直接:
#      curl -fsSL https://raw.githubusercontent.com/sabobo0406/sabobo0406/claude/shokz-earbud-voice-input-ycnjy4/shokz-voice-input/install.sh | bash

set -euo pipefail

RAW_BASE="https://raw.githubusercontent.com/sabobo0406/sabobo0406/claude/shokz-earbud-voice-input-ycnjy4/shokz-voice-input"
HS_DIR="$HOME/.hammerspoon"
HS_CONFIG="$HS_DIR/init.lua"

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "\033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "\033[33m!\033[0m %s\n" "$1"; }
info() { printf "\033[36m→\033[0m %s\n" "$1"; }

bold "Shokz × 音声入力(方法A)セットアップを開始します"
echo

# 0. macOS チェック
if [[ "$(uname)" != "Darwin" ]]; then
  warn "このスクリプトは macOS 専用です。Mac で実行してください。"
  exit 1
fi

# 1. Homebrew
if ! command -v brew >/dev/null 2>&1; then
  warn "Homebrew が見つかりません。先にインストールしてください:"
  echo '   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  echo "   インストール後、このスクリプトをもう一度実行してください。"
  exit 1
fi
ok "Homebrew を確認"

# 2. Hammerspoon
if [[ -d "/Applications/Hammerspoon.app" ]] || brew list --cask hammerspoon >/dev/null 2>&1; then
  ok "Hammerspoon は既にインストール済み"
else
  info "Hammerspoon をインストールしています..."
  brew install --cask hammerspoon
  ok "Hammerspoon をインストールしました"
fi

# 3. 既存設定のバックアップ
mkdir -p "$HS_DIR"
if [[ -f "$HS_CONFIG" ]]; then
  BACKUP="$HS_CONFIG.backup.$(date +%Y%m%d%H%M%S)"
  cp "$HS_CONFIG" "$BACKUP"
  warn "既存の init.lua をバックアップしました: $BACKUP"
  warn "  (元の設定を使いたい場合は、新しい init.lua の中身を手動でマージしてください)"
fi

# 4. init.lua を配置(ローカルにあればコピー、無ければダウンロード)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
LOCAL_SRC="$SCRIPT_DIR/hammerspoon/init.lua"
if [[ -f "$LOCAL_SRC" ]]; then
  cp "$LOCAL_SRC" "$HS_CONFIG"
  ok "init.lua を配置しました(ローカルから)"
else
  curl -fsSL "$RAW_BASE/hammerspoon/init.lua" -o "$HS_CONFIG"
  ok "init.lua を配置しました(ダウンロード)"
fi

# 5. Hammerspoon を起動 / リロード
open -a Hammerspoon 2>/dev/null || true
ok "Hammerspoon を起動しました"

echo
bold "ここからは手動で行う残りのステップです(2分):"
echo
info "【1】Hammerspoon の権限を許可"
echo "    システム設定 → プライバシーとセキュリティ → アクセシビリティ"
echo "    で Hammerspoon を ON にする。"
echo "    そのあとメニューバーの 🔨 → Reload Config。"
echo "    「Shokz voice input: ready」と出れば成功です。"
echo
info "【2】Typeless の設定"
echo "    Typeless → 設定 → ホットキー で、カスタムホットキーを ⌘⌥D に変更。"
echo "    録音モードは「トグル(1回押すと開始 / もう1回で終了)」を選ぶ。"
echo "    (Push-to-Talk は Shokz では使えないため)"
echo
info "【3】マイクを Shokz にする"
echo "    システム設定 → サウンド → 入力 で Shokz を選択。"
echo
bold "完了! ChatGPT / Claude のチャット欄をクリック → Shokz のボタンを押す"
bold "→ 話す → もう一度押す → 文字が入力されます 🎤"
