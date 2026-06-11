-- 【診断用 v2】Shokz のボタンが送る systemDefined イベントだけを記録する
--
-- キーボード入力は記録しないので、スクショ用の ⌘⇧5 などのノイズが混ざりません。
-- 結果は「消えないコンソール」にも残るので、スクショ不要でコピペできます。
--
-- 使い方:
--   1. これを ~/.hammerspoon/init.lua に入れて、メニューバー 🔨 → Reload Config
--   2. メニューバー 🔨 → Console を開く(ログが残る窓)
--   3. Mac で音楽を数秒再生してから、次を1つずつ 2〜3回押す:
--        ・マルチファンクションボタン(短押し)
--        ・音量+ ボタン
--        ・音量− ボタン
--   4. Console に出る [DIAG] の行を全部コピーして送る
--
-- ⚠️ 終わったら元の init.lua に戻してください。

local n = 0
diagSysTap = hs.eventtap.new({ hs.eventtap.event.types.systemDefined }, function(e)
  local sys = e:systemKey()
  local raw = e:getRawEventData() or {}
  local d = raw.NSEventData or {}
  n = n + 1
  local msg
  if sys and sys.key then
    msg = string.format("#%d  systemKey=%s down=%s repeat=%s",
      n, tostring(sys.key), tostring(sys.down), tostring(sys["repeat"]))
  else
    msg = string.format("#%d  other subtype=%s data1=%s data2=%s",
      n, tostring(d.subtype), tostring(d.data1), tostring(d.data2))
  end
  print("[DIAG] " .. msg)
  hs.alert.show(msg, 3)
  return false -- 素通り(挙動は変えない)
end)
diagSysTap:start()

hs.alert.show("診断モード v2: 🔨→Console を開いてボタンを押してください", 8)
print("[DIAG] ready - press Shokz buttons (MFB short / Vol+ / Vol-) while Mac plays audio")
