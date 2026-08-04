# Chat Bot

Chat Bot is an Arabic voice assistant project that combines a Cohere-powered chat engine with voice input/output and a desktop GUI. It can respond to user messages in Arabic and supports both a console-based voice bot and a graphical interface.

## Features

- Arabic chat responses using Cohere
- Voice input through microphone
- Voice output through text-to-speech
- Desktop GUI built with PySide6
- Text-only chat mode in the GUI
- Microphone icon in the GUI to enable voice chat
- Conversation history for more contextual replies

## Project Files

- `cohere_chat.py` - Core chat logic using Cohere
- `config.py` - Configuration and environment loading
- `voice_engine.py` - Speech recognition and speech synthesis integration
- `voice_bot.py` - Console-based voice assistant entry point
- `gui_app.py` - Desktop graphical user interface

## Requirements

Install the following libraries:

- RealtimeSTT
- RealtimeTTS[edge]
- cohere
- PySide6

## Configuration

Create a `.env` file in the project root with your Cohere API key:

```env
COHERE_API_KEY=your_api_key_here
```

---

## Demo Video

[▶ Watch the demo](Demo.mp4)

