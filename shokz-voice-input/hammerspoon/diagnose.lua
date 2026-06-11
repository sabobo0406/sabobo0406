-- 【診断用】Shokz のボタンが実際にどんなイベントを送っているか調べる
--
-- 使い方:
--   1. これを ~/.hammerspoon/init.lua に入れて、メニューバー 🔨 → Reload Config
--   2. 「診断モード: ボタンを押してください」と出たら Shokz のボタンを押す
--   3. 画面に出た内容(systemKey / keyDown / NSEvent ...)をスクショで送る
--
-- ※ 調べ終わったら、元の init.lua に戻してください。

-- すべての systemDefined イベント(メディアキー・音声アシスタント等)を記録
diagSysTap = hs.eventtap.new({ hs.eventtap.event.types.systemDefined }, function(e)
  local sys = e:systemKey()
  local raw = e:getRawEventData()
  local msg
  if sys and sys.key then
    msg = "systemKey = " .. tostring(sys.key)
        .. " (down=" .. tostring(sys.down)
        .. ", repeat=" .. tostring(sys["repeat"]) .. ")"
  else
    -- systemKey に出ない特殊イベント(Siri/dictation など)の生データ
    local d = raw and raw.NSEventData or {}
    msg = "systemDefined(other) subtype="
        .. tostring(d.subtype) .. " data1=" .. tostring(d.data1)
  end
  print("[DIAG] " .. msg)
  hs.alert.show(msg, 4)
  return false  -- 握りつぶさず素通り(挙動を変えないため)
end)
diagSysTap:start()

-- 通常のキー入力(キーボードショートカット化されている場合)も記録
diagKeyTap = hs.eventtap.new({ hs.eventtap.event.types.keyDown }, function(e)
  local key = hs.keycodes.map[e:getKeyCode()] or ("code:" .. e:getKeyCode())
  local mods = {}
  for m, on in pairs(e:getFlags()) do if on then mods[#mods+1] = m end end
  local msg = "keyDown = " .. table.concat(mods, "+") .. (#mods > 0 and "+" or "") .. tostring(key)
  print("[DIAG] " .. msg)
  hs.alert.show(msg, 4)
  return false
end)
diagKeyTap:start()

hs.alert.show("診断モード: Shokz のボタンを押してください", 6)
print("[DIAG] diagnostic ready")
