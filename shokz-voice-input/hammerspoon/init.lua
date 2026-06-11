-- Shokz のマルチファンクションボタン(再生/一時停止)で音声入力をトグルする
-- ~/.hammerspoon/init.lua に置いて Hammerspoon をリロードしてください。
--
-- 動作: Shokz のボタンを押すと音楽の再生/停止の代わりに音声入力が開始し、
--       もう一度押すと終了します。

-- ▼ 設定: 使う音声入力に合わせて MODE を選ぶ
--   "hotkey" : Typeless / Superwhisper / VoiceInk / Wispr Flow などのホットキーを送る
--              (アプリ側のホットキーを下の HOTKEY と同じに設定すること)
--   "apple"  : macOS 標準の音声入力を使う
--              (システム設定 → キーボード → 音声入力 のショートカットを
--               「Controlキーを2回押す」に設定しておくこと)
--
-- Typeless を使う場合(推奨設定):
--   1. Typeless の Settings → Shortcuts で、音声入力(dictation)の
--      開始/停止ショートカットを ⌘⌥D に変更する
--   2. Typeless はデフォルトでトグル動作(1回押すと開始 / もう1回で停止)なので、
--      特別なモード切替は不要。そのまま ⌘⌥D を設定すればよい。
--      ※ Shokz のボタンは「1回押す」信号しか出せないため、
--        「押している間だけ(Push-to-Talk)」の使い方はできません。
--   3. 下の MODE は "hotkey" のまま、HOTKEY も ⌘⌥D のままにする
local MODE = "hotkey"
local HOTKEY = { mods = { "cmd", "alt" }, key = "d" }

local function tapCtrl()
  hs.eventtap.event.newKeyEvent("ctrl", true):post()
  hs.eventtap.event.newKeyEvent("ctrl", false):post()
end

local function startDictation()
  if MODE == "apple" then
    -- 「Controlキーを2回押す」をエミュレートして標準の音声入力を起動
    tapCtrl()
    hs.timer.doAfter(0.1, tapCtrl)
  else
    hs.eventtap.keyStroke(HOTKEY.mods, HOTKEY.key, 0)
  end
  hs.alert.show("🎤", 0.5)
end

-- メディアキー(systemDefined イベント)を横取りする。
-- グローバル変数にしないと GC されてタップが止まるので注意。
shokzVoiceTap = hs.eventtap.new({ hs.eventtap.event.types.systemDefined }, function(e)
  local sys = e:systemKey()
  if sys and sys.key == "PLAY" and not sys["repeat"] then
    if sys.down then
      startDictation()
    end
    -- true を返してイベントを握りつぶす(音楽が再生されないように)
    return true
  end
  return false
end)
shokzVoiceTap:start()

hs.alert.show("Shokz voice input: ready")
