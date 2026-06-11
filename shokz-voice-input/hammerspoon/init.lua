-- Shokz のマルチファンクションボタン(再生/一時停止)で音声入力をトグルする
-- ~/.hammerspoon/init.lua に置いて Hammerspoon をリロードしてください。
--
-- 動作: ボタン1回目 → 音声入力開始(録音中)
--       ボタン2回目 → 録音停止 → 文字起こしがチャット欄に入力される
--                     →(AUTO_SEND が true なら)数秒後に Enter を自動で押して
--                       AI にメッセージを送信する

-- ▼ 設定: 使う音声入力に合わせて MODE を選ぶ
--   "hotkey" : Typeless / Superwhisper / VoiceInk / Wispr Flow などのホットキーを送る
--              (アプリ側のホットキーを下の HOTKEY と同じに設定すること)
--   "apple"  : macOS 標準の音声入力を使う
--              (システム設定 → キーボード → 音声入力 のショートカットを
--               「Controlキーを2回押す」に設定しておくこと)
--
-- Typeless を使う場合(推奨設定):
--   1. Typeless の 設定 → キーボードショートカット で、「音声入力」の
--      ショートカットを ⌃⌥D(Control + Option + D)に変更する
--      (Typeless はショートカットを最大3キーまでしか登録できないため3キー構成)
--   2. Typeless はデフォルトでトグル動作(1回押すと開始 / もう1回で停止)なので、
--      特別なモード切替は不要。そのまま ⌃⌥D を設定すればよい。
--   3. 下の MODE は "hotkey" のまま、HOTKEY も ⌃⌥D のままにする
--      (⌘D=ブックマーク, ⌥⌘D=Dock表示切替, ⌃⌘D=辞書 と衝突するため避ける)
--   4. Typeless 側の「Fn」ショートカットは残してもよいが、Fn で開始/停止すると
--      このスクリプトの録音状態の認識とズレるので、Shokz 運用中はボタン側に統一を推奨
local MODE = "hotkey"
local HOTKEY = { mods = { "ctrl", "alt" }, key = "d" }

-- ▼ 自動送信: 録音停止(2回目のボタン)のあと AUTO_SEND_DELAY 秒待ってから
--   Enter を押し、チャット欄に入った文字を AI に送信する。
--   長く話して文字起こしが間に合わないと途中で送信されることがあるので、
--   その場合は AUTO_SEND_DELAY を増やす。手動で Enter したい人は false にする。
local AUTO_SEND = true
local AUTO_SEND_DELAY = 4 -- 秒

local dictating = false

local function tapCtrl()
  hs.eventtap.event.newKeyEvent("ctrl", true):post()
  hs.eventtap.event.newKeyEvent("ctrl", false):post()
end

local function toggleDictation()
  if MODE == "apple" then
    -- 「Controlキーを2回押す」をエミュレートして標準の音声入力を起動/停止
    tapCtrl()
    hs.timer.doAfter(0.1, tapCtrl)
  else
    hs.eventtap.keyStroke(HOTKEY.mods, HOTKEY.key, 0)
  end
end

-- メディアキー(systemDefined イベント)を横取りする。
-- グローバル変数にしないと GC されてタップが止まるので注意。
shokzVoiceTap = hs.eventtap.new({ hs.eventtap.event.types.systemDefined }, function(e)
  local sys = e:systemKey()
  if sys and sys.key == "PLAY" and not sys["repeat"] then
    if sys.down then
      toggleDictation()
      if dictating then
        -- 2回目: 録音停止 → 文字起こしを待って自動送信
        dictating = false
        if AUTO_SEND then
          hs.alert.show("⏹ 停止(" .. AUTO_SEND_DELAY .. "秒後に送信)", 1.5)
          hs.timer.doAfter(AUTO_SEND_DELAY, function()
            hs.eventtap.keyStroke({}, "return", 0)
            hs.alert.show("📨 送信", 1)
          end)
        else
          hs.alert.show("⏹ 停止", 1)
        end
      else
        -- 1回目: 録音開始
        dictating = true
        hs.alert.show("🎤 録音中", 1)
      end
    end
    -- true を返してイベントを握りつぶす(音楽が再生されないように)
    return true
  end
  return false
end)
shokzVoiceTap:start()

hs.alert.show("Shokz voice input: ready")
