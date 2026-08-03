import threading
import traceback

from cohere_chat import ArabicChatEngine
from voice_engine import VoiceController, build_tts_stream

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except Exception:
    QtCore = None
    QtGui = None
    QtWidgets = None

BG_MAIN = "#050608"
BG_HEADER = "#0f1116"
BG_INPUT_BAR = "#0f1116"
BG_ENTRY = "#171a22"
BUBBLE_USER = "#5b51d8"
BUBBLE_BOT = "#1b1f28"
TEXT_LIGHT = "#f7f8fb"
TEXT_MUTED = "#8f95a6"
ACCENT = "#5b51d8"
MIC_OFF = "#2c313d"
MIC_ON = "#ef4c5f"
BORDER = "#232833"


class UiDispatcher(QtCore.QObject if QtCore is not None else object):
    if QtCore is not None:
        dispatch = QtCore.Signal(object)

    def __init__(self, parent=None):
        if QtCore is None:
            return
        super().__init__(parent)
        self.dispatch.connect(self._run, QtCore.Qt.QueuedConnection)

    def _run(self, callback):
        callback()


class ChatBubbleWidget(QtWidgets.QWidget if QtWidgets is not None else object):
    def __init__(self, text: str, sender: str = "bot", parent=None):
        if QtWidgets is None:
            super().__init__()
            return
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setContentsMargins(0, 0, 0, 0)

        bubble_color = BUBBLE_USER if sender == "user" else BUBBLE_BOT
        text_color = TEXT_LIGHT
        alignment = QtCore.Qt.AlignRight if sender == "user" else QtCore.Qt.AlignLeft

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(alignment)

        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        label.setOpenExternalLinks(False)
        label.setStyleSheet(
            f"background-color:{bubble_color}; color:{text_color};"
            "border-radius: 14px; padding: 10px 12px;"
            "margin: 2px 0;"
        )
        label.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Maximum,
        )
        label.setMaximumWidth(360)
        layout.addWidget(label, 1)


class ChatCanvas(QtWidgets.QWidget if QtWidgets is not None else object):
    def __init__(self, parent=None):
        if QtWidgets is None:
            self._layout = None
            self._scroll_area = None
            return
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")

        self._scroll_area = QtWidgets.QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._scroll_area.setStyleSheet("background: transparent;")

        self._content = QtWidgets.QWidget(self._scroll_area)
        self._content.setStyleSheet("background: transparent;")
        self._layout = QtWidgets.QVBoxLayout(self._content)
        self._layout.setContentsMargins(12, 10, 12, 10)
        self._layout.setSpacing(10)
        self._layout.addStretch(1)
        self._scroll_area.setWidget(self._content)

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._scroll_area)

    def add_bubble(self, text: str, sender: str = "bot"):
        if QtWidgets is None:
            return
        bubble = ChatBubbleWidget(text, sender=sender, parent=self._content)
        self._layout.insertWidget(self._layout.count() - 1, bubble)
        QtCore.QTimer.singleShot(0, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        if QtWidgets is None or self._scroll_area is None:
            return
        self._scroll_area.verticalScrollBar().setValue(self._scroll_area.verticalScrollBar().maximum())


class VoiceChatApp:
    def __init__(self, root=None):
        if QtWidgets is None:
            raise RuntimeError("PySide6 is required to run the GUI.")

        self.root = root if root is not None else QtWidgets.QMainWindow()
        self.chat_engine = None
        self.tts_stream = None
        self._message_seq = 0
        self._active_message_id = 0
        self._init_done = False
        self._init_failed = False
        self._init_warning_shown = False
        self._ui_dispatcher = UiDispatcher(self.root)
        self.voice = VoiceController(on_text=self._on_voice_text, on_status=self._on_voice_status)

        self._build_window()
        self._build_header()
        self._build_chat_area()
        self._build_input_bar()

        self.send_btn.setEnabled(False)
        self.mic_btn.setEnabled(False)
        self.status_label.setText("جارٍ التجهيز...")

        QtCore.QTimer.singleShot(160, lambda: self._add_bot_bubble("جارٍ تجهيز البوت، لحظات..."))
        QtCore.QTimer.singleShot(7000, self._handle_init_timeout)
        threading.Thread(target=self._init_engines, daemon=True).start()

    def _build_window(self):
        self.root.setWindowTitle("المساعد الذكي")
        self.root.resize(430, 720)
        self.root.setMinimumSize(360, 620)
        self.root.setStyleSheet(
            "QMainWindow { background: #050608; color: #f7f8fb; }"
            "QWidget { font-family: 'Segoe UI'; }"
            "QLineEdit { border: 1px solid #232833; border-radius: 14px; padding: 8px 12px; background: #171a22; color: #f7f8fb; }"
            "QPushButton { border-radius: 14px; padding: 8px 12px; background: #5b51d8; color: white; }"
            "QPushButton:hover { background: #6f63f0; }"
        )

        central = QtWidgets.QWidget(self.root)
        central.setStyleSheet("background: #050608;")
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if hasattr(self.root, "setCentralWidget"):
            self.root.setCentralWidget(central)
        self._central_widget = central
        self._central_layout = layout

    def _build_header(self):
        header = QtWidgets.QWidget(self._central_widget)
        header.setFixedHeight(88)
        header.setStyleSheet("background: #0f1116;")
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(10)

        avatar = QtWidgets.QLabel("🤖", header)
        avatar.setAlignment(QtCore.Qt.AlignCenter)
        avatar.setStyleSheet(
            "background: #5b51d8; color: white; border-radius: 20px; min-width: 40px; min-height: 40px;"
        )
        header_layout.addWidget(avatar, 0, QtCore.Qt.AlignRight)

        info = QtWidgets.QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        title = QtWidgets.QLabel("المساعد الذكي")
        title.setAlignment(QtCore.Qt.AlignRight)
        title.setStyleSheet("color: #f7f8fb; font-size: 14px; font-weight: 700;")
        info.addWidget(title)
        self.status_label = QtWidgets.QLabel("المايكروفون مطفأ")
        self.status_label.setAlignment(QtCore.Qt.AlignRight)
        self.status_label.setStyleSheet("color: #8f95a6; font-size: 11px;")
        info.addWidget(self.status_label)
        header_layout.addLayout(info)

        self._central_layout.addWidget(header)

    def _build_chat_area(self):
        chat_wrapper = QtWidgets.QWidget(self._central_widget)
        chat_wrapper.setStyleSheet("background: #050608;")
        chat_wrapper_layout = QtWidgets.QVBoxLayout(chat_wrapper)
        chat_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = ChatCanvas(chat_wrapper)
        chat_wrapper_layout.addWidget(self.canvas)
        self._central_layout.addWidget(chat_wrapper, 1)

    def _build_input_bar(self):
        bar = QtWidgets.QWidget(self._central_widget)
        bar.setStyleSheet("background: #0f1116; border-top: 1px solid #232833;")
        bar.setFixedHeight(84)
        bar_layout = QtWidgets.QHBoxLayout(bar)
        bar_layout.setContentsMargins(12, 10, 12, 10)
        bar_layout.setSpacing(8)

        self.mic_btn = QtWidgets.QPushButton("🎤")
        self.mic_btn.setFixedSize(44, 44)
        self.mic_btn.setStyleSheet(
            "background: #2c313d; color: white; border-radius: 22px; font-size: 16px;"
        )
        self.mic_btn.clicked.connect(self._toggle_mic)
        bar_layout.addWidget(self.mic_btn)

        self.entry = QtWidgets.QLineEdit()
        self.entry.setPlaceholderText("اكتب رسالة...")
        self.entry.returnPressed.connect(self._on_send_clicked)
        bar_layout.addWidget(self.entry, 1)

        self.send_btn = QtWidgets.QPushButton("إرسال")
        self.send_btn.setFixedHeight(44)
        self.send_btn.clicked.connect(self._on_send_clicked)
        bar_layout.addWidget(self.send_btn)

        self._central_layout.addWidget(bar)

    def _toggle_mic(self):
        if self.chat_engine is None:
            return
        if self.voice.is_listening:
            self.voice.stop()
            self._draw_mic_button(active=False)
        else:
            self.voice.start()
            self._draw_mic_button(active=True)

    def _draw_mic_button(self, active: bool):
        color = MIC_ON if active else MIC_OFF
        self.mic_btn.setStyleSheet(
            f"background: {color}; color: white; border-radius: 22px; font-size: 16px;"
        )

    def _call_ui(self, callback):
        dispatcher = getattr(self, "_ui_dispatcher", None)
        if dispatcher is None or QtCore is None:
            callback()
            return
        dispatcher.dispatch.emit(callback)

    def _on_voice_status(self, status: str):
        self._call_ui(lambda: self.status_label.setText(status))

    def _on_voice_text(self, text: str):
        self._call_ui(lambda: self._handle_user_message(text))

    def _on_send_clicked(self):
        if self.chat_engine is None:
            return
        text = self.entry.text().strip()
        if not text:
            return
        self.entry.clear()
        self._handle_user_message(text)

    def _init_engines(self):
        try:
            chat_engine = ArabicChatEngine()
        except Exception as e:
            traceback.print_exc()
            self._call_ui(lambda: self._on_init_failed(str(e)))
            return

        self.chat_engine = chat_engine

        try:
            self.tts_stream = build_tts_stream()
        except Exception as e:
            traceback.print_exc()
            print(f"تعذّر تجهيز الصوت (سيعمل البوت بدون نطق): {e}")
            self.tts_stream = None

        self._call_ui(self._on_init_success)

    def _handle_init_timeout(self):
        if self._init_done or self._init_failed:
            return
        self.status_label.setText("ما زال الاتصال جارٍ...")
        if not self._init_warning_shown:
            self._init_warning_shown = True
            self._add_bot_bubble("⏳ الاتصال بالخدمة يأخذ وقتًا أطول من المتوقع... جارٍ المحاولة.")
        QtCore.QTimer.singleShot(7000, self._handle_init_timeout)

    def _on_init_failed(self, message: str):
        if self._init_done or self._init_failed:
            return
        self._init_failed = True
        self._add_bot_bubble(f"❌ تعذّر تشغيل البوت:\n{message}\n\nتحقق من COHERE_API_KEY والاتصال بالإنترنت ثم أعد التشغيل.")
        self.status_label.setText("تعذّر الاتصال")
        if hasattr(self, "send_btn"):
            self.send_btn.setEnabled(False)
        if hasattr(self, "mic_btn"):
            self.mic_btn.setEnabled(False)

    def _on_init_success(self):
        if self._init_failed:
            return
        self._init_done = True
        self.send_btn.setEnabled(True)
        self.mic_btn.setEnabled(True)
        self.status_label.setText("المايكروفون مطفأ")
        note = "" if self.tts_stream else " (بدون نطق صوتي حاليًا)"
        self._add_bot_bubble(f"أهلًا! اكتب رسالة أو فعّل المايك وابدأ الكلام 🎙️{note}")

    def _handle_user_message(self, text: str):
        self._stop_current_speech()
        self._message_seq += 1
        self._active_message_id = self._message_seq
        self._add_user_bubble(text)
        threading.Thread(target=self._get_reply_and_respond, args=(text, self._active_message_id), daemon=True).start()

    def _get_reply_and_respond(self, text: str, message_id: int):
        try:
            reply = self.chat_engine.get_reply(text)
        except Exception as e:
            self._call_ui(lambda: self._deliver_error(message_id, str(e)))
            return

        self._call_ui(lambda: self._deliver_reply(message_id, reply))

    def _deliver_error(self, message_id: int, error_text: str):
        if message_id != self._active_message_id:
            return
        self._add_bot_bubble(f"❌ {error_text}")

    def _deliver_reply(self, message_id: int, reply: str):
        if message_id != self._active_message_id:
            return
        self._add_bot_bubble(reply)
        self._speak_reply(reply)

    def _stop_current_speech(self):
        if self.tts_stream is None:
            return
        try:
            self.tts_stream.stop()
        except Exception as e:
            print(f"تعذّر إيقاف الصوت: {e}")

    def _speak_reply(self, reply: str):
        if self.tts_stream is None or not reply:
            return
        try:
            self._stop_current_speech()
            self.tts_stream.feed(reply)
            self.tts_stream.play_async()
        except Exception as e:
            print(f"تعذّر تشغيل الصوت: {e}")

    def _add_user_bubble(self, text):
        self.canvas.add_bubble(text, sender="user")

    def _add_bot_bubble(self, text):
        self.canvas.add_bubble(text, sender="bot")


def main():
    if QtWidgets is None:
        raise RuntimeError("PySide6 is required to run the GUI. Install it with pip install PySide6")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = VoiceChatApp()
    window.root.show()
    app.exec()


if __name__ == "__main__":
    main()
