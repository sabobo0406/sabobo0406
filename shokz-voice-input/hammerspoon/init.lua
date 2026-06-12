-- Shokz のボタンで音声入力をトグルする(OpenComm 等・アプリ非対応モデル向け)
-- ~/.hammerspoon/init.lua に置いて Hammerspoon をリロードしてください。
--
-- 動作: 引き金ボタン1回目 → 音声入力開始(録音中)
--       引き金ボタン2回目 → 録音停止 → 文字起こしがチャット欄に入力される
--                          →(AUTO_SEND が true なら)数秒後に Enter を自動送信

-- ▼ 引き金にする Shokz のボタンを選ぶ(TRIGGER)
--   "PLAY"       : マルチファンクションボタンを「短く1回」押す(=再生/一時停止)
--                  ※ 長押しすると Siri が起動してしまい捕まえられないので「短く」
--   "SOUND_UP"   : 音量+ ボタン(短押し)。Siri を絶対に呼ばないので確実。
--                  代わりに音量+操作は無効になります(このスクリプトが横取りするため)
--   "SOUND_DOWN" : 音量− ボタン(短押し)。同上。
--
--   まず "PLAY" を短押しで試し、どうしても Siri が出てしまう/反応しない場合は
--   "SOUND_UP" か "SOUND_DOWN" に変えてください(確実に動きます)。
local TRIGGER = "PLAY"

-- ▼ 使う音声入力に合わせて MODE を選ぶ
--   "hotkey" : Typeless / Superwhisper / VoiceInk などのホットキーを送る
--   "apple"  : macOS 標準の音声入力(Control 2回押し)を使う
local MODE = "hotkey"
-- Typeless: 設定 → キーボードショートカット →「音声入力」を ⌃⌥D に設定(最大3キー)
local HOTKEY = { mods = { "ctrl", "alt" }, key = "d" }

-- ▼ 自動送信: 録音停止のあと AUTO_SEND_DELAY 秒待って Enter を押し、AI に送信する。
--   長く話して文字起こしが間に合わない場合は AUTO_SEND_DELAY を増やす。
--   自分で Enter したい人は false に。
local AUTO_SEND = true
local AUTO_SEND_DELAY = 4 -- 秒

local dictating = false

local function tapCtrl()
  hs.eventtap.event.newKeyEvent("ctrl", true):post()
  hs.eventtap.event.newKeyEvent("ctrl", false):post()
end

local function toggleDictation()
  if MODE == "apple" then
    tapCtrl()
    hs.timer.doAfter(0.1, tapCtrl)
  else
    hs.eventtap.keyStroke(HOTKEY.mods, HOTKEY.key, 0)
  end
end

local function onTrigger()
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

-- メディアキー(systemDefined イベント)を横取りする。
-- グローバル変数にしないと GC されてタップが止まるので注意。
shokzVoiceTap = hs.eventtap.new({ hs.eventtap.event.types.systemDefined }, function(e)
  local sys = e:systemKey()
  if sys and sys.key == TRIGGER and not sys["repeat"] then
    if sys.down then
      onTrigger()
    end
    -- true を返してイベントを握りつぶす(音楽再生や音量変化が起きないように)
    return true
  end
  return false
end)
shokzVoiceTap:start()

hs.alert.show("Shokz voice input: ready (" .. TRIGGER .. ")")
