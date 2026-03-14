"""
MegPad ディスプレイ表情UI モジュール

KTC MegPad 27インチをロボットの「顔」として使用し、
表情アニメーション、ステータス表示、音声応答テキストを表示する。
Flask + WebSocketでリアルタイム表情を制御する。
"""

import json
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from loguru import logger

try:
    from flask import Flask, render_template_string
    from flask_socketio import SocketIO
except ImportError:
    Flask = None
    SocketIO = None
    logger.warning("Flask not installed - display module unavailable")


class Expression(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    THINKING = "thinking"
    SURPRISED = "surprised"
    SLEEPING = "sleeping"
    TALKING = "talking"
    SAD = "sad"
    ANGRY = "angry"
    WINK = "wink"


@dataclass
class DisplayConfig:
    host: str = "0.0.0.0"
    port: int = 5000
    width: int = 1920
    height: int = 1080
    fps: int = 30


# MegPadに表示するHTML/CSS/JSの表情アニメーションUI
FACE_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HomeBot Face</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: #1a1a2e;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    overflow: hidden;
    font-family: 'Segoe UI', sans-serif;
}
.face-container {
    position: relative;
    width: 800px;
    height: 500px;
}
.eye {
    position: absolute;
    width: 120px;
    height: 120px;
    background: #00d4ff;
    border-radius: 50%;
    top: 100px;
    transition: all 0.3s ease;
    box-shadow: 0 0 40px rgba(0, 212, 255, 0.5);
}
.eye-left { left: 220px; }
.eye-right { right: 220px; }
.pupil {
    position: absolute;
    width: 50px;
    height: 50px;
    background: #0a0a1a;
    border-radius: 50%;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    transition: all 0.2s ease;
}
.eye-highlight {
    position: absolute;
    width: 18px;
    height: 18px;
    background: white;
    border-radius: 50%;
    top: 25px;
    right: 25px;
}
.mouth {
    position: absolute;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    width: 200px;
    height: 60px;
    border: 4px solid #00d4ff;
    border-top: none;
    border-radius: 0 0 100px 100px;
    transition: all 0.3s ease;
    box-shadow: 0 5px 20px rgba(0, 212, 255, 0.3);
}
.status-bar {
    position: fixed;
    bottom: 30px;
    color: #00d4ff;
    font-size: 24px;
    text-align: center;
    opacity: 0.8;
}
.speech-bubble {
    position: fixed;
    top: 40px;
    background: rgba(0, 212, 255, 0.1);
    border: 2px solid rgba(0, 212, 255, 0.3);
    border-radius: 20px;
    padding: 15px 30px;
    color: #00d4ff;
    font-size: 28px;
    max-width: 80%;
    text-align: center;
    display: none;
}

/* Expressions */
.happy .eye { height: 80px; border-radius: 80px 80px 50% 50%; }
.happy .mouth { height: 80px; border-radius: 0 0 100px 100px; }

.thinking .eye-right { height: 60px; }
.thinking .mouth {
    width: 40px; height: 40px;
    border: 4px solid #00d4ff;
    border-radius: 50%;
}

.surprised .eye { width: 150px; height: 150px; }
.surprised .mouth {
    width: 80px; height: 80px;
    border: 4px solid #00d4ff;
    border-radius: 50%;
}

.sleeping .eye {
    height: 6px;
    border-radius: 3px;
    top: 160px;
}
.sleeping .mouth {
    width: 100px;
    height: 30px;
    border-radius: 0 0 50px 50px;
}

.talking .mouth {
    animation: talk 0.3s infinite alternate;
}
@keyframes talk {
    0% { height: 30px; }
    100% { height: 70px; }
}

.sad .eye { top: 120px; }
.sad .mouth {
    border: none;
    border-top: 4px solid #00d4ff;
    border-radius: 100px 100px 0 0;
    height: 40px;
    bottom: 100px;
}

.wink .eye-right {
    height: 6px;
    border-radius: 3px;
    top: 160px;
}

/* Blink animation */
@keyframes blink {
    0%, 95%, 100% { transform: scaleY(1); }
    97% { transform: scaleY(0.1); }
}
.eye { animation: blink 4s infinite; }

/* Breathing glow */
@keyframes glow {
    0%, 100% { box-shadow: 0 0 40px rgba(0, 212, 255, 0.3); }
    50% { box-shadow: 0 0 60px rgba(0, 212, 255, 0.6); }
}
.face-container { animation: glow 3s infinite; }
</style>
</head>
<body>
<div class="speech-bubble" id="speech"></div>
<div class="face-container" id="face">
    <div class="eye eye-left">
        <div class="pupil"></div>
        <div class="eye-highlight"></div>
    </div>
    <div class="eye eye-right">
        <div class="pupil"></div>
        <div class="eye-highlight"></div>
    </div>
    <div class="mouth"></div>
</div>
<div class="status-bar" id="status">HomeBot Ready</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.js"></script>
<script>
const socket = io();
const face = document.getElementById('face');
const status = document.getElementById('status');
const speech = document.getElementById('speech');

socket.on('expression', (data) => {
    face.className = 'face-container ' + data.expression;
});

socket.on('status', (data) => {
    status.textContent = data.text;
});

socket.on('speech', (data) => {
    speech.textContent = data.text;
    speech.style.display = 'block';
    if (data.duration > 0) {
        setTimeout(() => { speech.style.display = 'none'; }, data.duration);
    }
});

// 目がマウス/タッチに追従
document.addEventListener('mousemove', (e) => {
    const pupils = document.querySelectorAll('.pupil');
    pupils.forEach(pupil => {
        const eye = pupil.parentElement;
        const rect = eye.getBoundingClientRect();
        const eyeX = rect.left + rect.width / 2;
        const eyeY = rect.top + rect.height / 2;
        const angle = Math.atan2(e.clientY - eyeY, e.clientX - eyeX);
        const distance = Math.min(15, Math.hypot(e.clientX - eyeX, e.clientY - eyeY) / 10);
        pupil.style.transform = `translate(calc(-50% + ${Math.cos(angle) * distance}px), calc(-50% + ${Math.sin(angle) * distance}px))`;
    });
});
</script>
</body>
</html>
"""


class MegPadFaceUI:
    """KTC MegPadに表示するロボットの顔UIを制御する"""

    def __init__(self, config: Optional[DisplayConfig] = None):
        self.config = config or DisplayConfig()
        self.current_expression = Expression.NEUTRAL
        self._app: Optional[Flask] = None
        self._socketio: Optional[SocketIO] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

        if Flask is None:
            logger.warning("Flask not available - Face UI disabled")
            return

        self._app = Flask(__name__)
        self._app.config["SECRET_KEY"] = "homebot-face"
        self._socketio = SocketIO(self._app, cors_allowed_origins="*")

        @self._app.route("/")
        def index():
            return render_template_string(FACE_HTML)

    def start(self):
        """WebサーバーをバックグラウンドスレッドとFして起動する"""
        if not self._app:
            logger.warning("Cannot start Face UI - Flask not available")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        logger.info(f"Face UI started at http://{self.config.host}:{self.config.port}")

    def _run_server(self):
        """Flaskサーバーを実行する"""
        self._socketio.run(
            self._app,
            host=self.config.host,
            port=self.config.port,
            allow_unsafe_werkzeug=True,
        )

    def stop(self):
        """UIサーバーを停止する"""
        self._running = False
        logger.info("Face UI stopped")

    def set_expression(self, expression: Expression):
        """表情を変更する"""
        self.current_expression = expression
        if self._socketio:
            self._socketio.emit("expression", {"expression": expression.value})
        logger.debug(f"Expression changed to: {expression.value}")

    def set_status_text(self, text: str):
        """ステータスバーのテキストを更新する"""
        if self._socketio:
            self._socketio.emit("status", {"text": text})

    def show_speech(self, text: str, duration_ms: int = 5000):
        """吹き出しでテキストを表示する"""
        if self._socketio:
            self._socketio.emit("speech", {"text": text, "duration": duration_ms})
        logger.info(f"Speech: {text}")

    def express_greeting(self):
        """挨拶の表情シーケンス"""
        self.set_expression(Expression.HAPPY)
        self.show_speech("こんにちは！何かお手伝いしましょうか？")

    def express_thinking(self):
        """考え中の表情"""
        self.set_expression(Expression.THINKING)
        self.set_status_text("考え中...")

    def express_task_complete(self):
        """タスク完了の表情"""
        self.set_expression(Expression.HAPPY)
        self.show_speech("できました！", duration_ms=3000)

    def express_error(self, message: str = ""):
        """エラー表情"""
        self.set_expression(Expression.SAD)
        self.show_speech(f"すみません... {message}" if message else "すみません...", duration_ms=5000)

    def get_status(self) -> dict:
        """現在の状態を返す"""
        return {
            "expression": self.current_expression.value,
            "server_running": self._running,
            "url": f"http://{self.config.host}:{self.config.port}",
        }
