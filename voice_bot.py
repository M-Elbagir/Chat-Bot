import sys

from RealtimeSTT import AudioToTextRecorder

import config
from cohere_chat import ArabicChatEngine
from voice_engine import build_tts_stream

STOP_WORDS = {"توقف", "إيقاف", "أوقف", "قف", "باي", "وداعا", "وداعًا", "خلاص"}


def speak(stream, text: str):
    print(f"🤖 المساعد: {text}")
    stream.feed(text)
    stream.play()


def main():
    print("جارٍ تجهيز بوت الدردشة الصوتي...")

    try:
        chat_engine = ArabicChatEngine()
    except ValueError as e:
        print(f"\n❌ {e}\n")
        sys.exit(1)

    tts_stream = build_tts_stream()
    recorder = AudioToTextRecorder(language=config.LANGUAGE, spinner=False)

    speak(tts_stream, "أهلًا فيك! أنا جاهز، اتفضل اتكلم.")
    print("\n(قل: توقف / إيقاف لإنهاء المحادثة، أو اضغط Ctrl+C)\n")

    try:
        while True:
            print("🎙️  تحدث الآن...")
            user_text = recorder.text()
            if not user_text or not user_text.strip():
                continue

            user_text = user_text.strip()
            print(f"🧑 أنت: {user_text}")

            if user_text in STOP_WORDS:
                speak(tts_stream, "تمام، إلى اللقاء!")
                break

            reply = chat_engine.get_reply(user_text)
            speak(tts_stream, reply)

    except KeyboardInterrupt:
        print("\nتم إنهاء المحادثة.")
    finally:
        recorder.shutdown()


if __name__ == "__main__":
    main()
