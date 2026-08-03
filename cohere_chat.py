try:
    import cohere
except Exception:
    cohere = None

import config

SYSTEM_PROMPT = f"""أنت مساعد ودود تتحدث العربية فقط، وأنت جزء من روبوت دردشة صوتي سريع
يشبه محادثة خاصة (رسالة مباشرة) في تطبيق تواصل اجتماعي.

التزم دائمًا بهذه القواعد:
- اكتب ردًا قصيرًا جدًا لا يتجاوز {config.MAX_REPLY_SENTENCES} جمل.
- تحدث بأسلوب عفوي وطبيعي وودود، وكأنك ترسل رسالة دردشة سريعة، وليس مقالًا.
- لا تستخدم رموز تنسيق مثل النجوم أو العناوين، ولا تكثر من الرموز التعبيرية.
- لا تكرر سؤال المستخدم، وابدأ ردك مباشرة بالإجابة.
- إذا لم تفهم الطلب، اطرح سؤال توضيح واحد قصير بدل الافتراض أو الإطالة.
"""


class ArabicChatEngine:
    def __init__(self, api_key: str = None, model: str = None):
        api_key = (api_key or config.COHERE_API_KEY or "").strip()
        self.model = model or config.COHERE_MODEL
        self.history = []

        if not api_key or "ضع-مفتاح" in api_key:
            raise ValueError(
                "لم يتم ضبط مفتاح Cohere API بعد. أضف COHERE_API_KEY أو ضع المفتاح في ملف .env."
            )

        if cohere is None:
            raise RuntimeError("مكتبة Cohere غير مثبتة. قم بتثبيت المتطلبات أولًا.")

        try:
            self.client = cohere.Client(
                api_key=api_key,
                timeout=120,
                max_retries=1,
            )
        except Exception as e:
            raise RuntimeError(f"تعذّر تهيئة Cohere: {e}") from e

    def _trim_history(self):
        max_messages = config.MAX_HISTORY_TURNS * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    def _build_chat_history(self):
        chat_history = []
        for item in self.history:
            role = "USER" if item["role"] == "user" else "CHATBOT"
            chat_history.append({"role": role, "message": item["content"]})
        return chat_history

    def _call_chat(self, user_text):
        try:
            return self.client.chat(
                message=user_text,
                model=self.model,
                preamble=SYSTEM_PROMPT,
                chat_history=self._build_chat_history(),
                max_tokens=120,
            )
        except Exception as e:
            raise RuntimeError(f"خطأ من Cohere: {e}") from e

    def _extract_reply(self, response):
        response_text = getattr(response, "text", None)
        if response_text:
            return str(response_text).strip()

        return ""

    def get_reply(self, user_text: str) -> str:
        user_text = (user_text or "").strip()
        if not user_text:
            return ""

        history_before_request = list(self.history)
        response = self._call_chat(user_text)
        reply = self._extract_reply(response)

        if not reply:
            raise RuntimeError("Cohere أعاد استجابة فارغة.")

        self.history = history_before_request + [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": reply},
        ]
        self._trim_history()
        return reply
