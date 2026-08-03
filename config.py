import os


def _load_dotenv_file():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            current_value = os.environ.get(key, "")
            if not current_value or "ضع-مفتاح" in current_value:
                os.environ[key] = value


_load_dotenv_file()

COHERE_API_KEY = os.environ.get("COHERE_API_KEY", "").strip()

COHERE_MODEL = "command-r7b-12-2024"

LANGUAGE = "ar"

ARABIC_VOICE = "ar-SA-HamedNeural"

MAX_HISTORY_TURNS = 6

MAX_REPLY_SENTENCES = 3
