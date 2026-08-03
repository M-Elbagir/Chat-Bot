import threading

try:
    from RealtimeSTT import AudioToTextRecorder
except Exception:
    AudioToTextRecorder = None

try:
    from RealtimeTTS import TextToAudioStream, EdgeEngine
except Exception:
    TextToAudioStream = None
    EdgeEngine = None

import config


def build_tts_stream():
    if EdgeEngine is None or TextToAudioStream is None:
        raise RuntimeError("مكتبات RealtimeTTS غير مثبتة. قم بتثبيت المتطلبات أولًا.")

    engine = EdgeEngine()
    engine.set_voice(config.ARABIC_VOICE)
    return TextToAudioStream(engine, language=config.LANGUAGE)


class VoiceController:
    def __init__(self, on_text, on_status=None, language: str = None):
        self.on_text = on_text
        self.on_status = on_status or (lambda status: None)
        self.language = language or config.LANGUAGE
        self._recorder = None
        self._thread = None
        self._running = False

    @property
    def is_listening(self) -> bool:
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._running = False
        self.on_status("جارٍ إيقاف المايكروفون...")
        recorder = self._recorder
        if recorder is not None:
            try:
                recorder.abort()
            except Exception:
                pass
            try:
                recorder.shutdown()
            except Exception:
                pass
        self._recorder = None
        self.on_status("المايكروفون مطفأ")

    def _listen_loop(self):
        self.on_status("جارٍ تشغيل المايكروفون...")
        try:
            self._recorder = AudioToTextRecorder(
                language=self.language,
                spinner=False,
            )
        except Exception as e:
            self.on_status(f"تعذّر تشغيل المايكروفون: {e}")
            self._running = False
            return

        self.on_status("أستمع الآن... تحدث براحتك")
        while self._running:
            try:
                text = self._recorder.text()
            except Exception:
                break
            if not self._running:
                break
            text = text.strip() if text else ""
            if text:
                self.on_text(text)

        self._recorder = None
