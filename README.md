# AI Sales Funnel Call Assistant

## Overview

This project is a **work-in-progress** real-time sales funnel call assistant. It captures audio from calls (Zoom/Meet/Teams), transcribes speech in real-time using AI, and is designed to provide AI-driven guidance aligned to custom sales funnel stages.

The system enables real-time analysis of sales conversations by separating and transcribing both the salesperson (microphone) and prospect (system audio) channels simultaneously.

## Current Progress

✅ **Completed:**
- Real-time dual-channel audio capture and streaming
- Integration with Deepgram API for speech-to-text transcription
- Channel separation (microphone vs system audio)
- WebSocket-based audio streaming architecture
- Interim and final transcription results processing
- Audio debugging tools for development

🚧 **In Development:**
- AI-powered sales funnel stage detection
- Real-time coaching and guidance system
- Custom sales playbook integration
- Advanced analytics and conversation insights

## Tech Stack

### Core Technologies
- **Python 3.8+** - Primary development language
- **FastAPI** - High-performance async web framework for the transcription server
- **WebSockets** - Real-time bidirectional communication
- **Deepgram API** - Advanced speech-to-text transcription service

### Audio Processing
- **SoundDevice** - Python audio I/O library for capturing system and microphone audio
- **NumPy** - Numerical computing for audio data processing
- **Voicemeeter** - Virtual audio mixer for audio routing and channel separation
- **FFmpeg** - Multimedia framework (used in testing utilities)

### Additional Libraries
- **asyncio** - Asynchronous programming for handling concurrent audio streams
- **aiohttp** - Async HTTP client for Deepgram WebSocket connections
- **python-dotenv** - Environment variable management

## Project Structure

```
├── audio/                          # Main application components
│   ├── transcription_server.py     # FastAPI transcription server
│   ├── real_time_audio_client.py   # Audio capture client
│   ├── server_requirements.txt     # Server dependencies
│   ├── client_requirements.txt     # Client dependencies
│   ├── tests/                      # Test scripts and utilities
│   └── transcriptions/             # Transcribed conversations output
│
└── setup/                          # Setup docs and utilities
    ├── SETUP.txt                   # Detailed setup instructions
    ├── LICENSE                     # MIT license
    └── ffmpeg.exe                  # Audio processing utility
```

## Quick Start

### Prerequisites
- Python 3.8+
- [Voicemeeter](https://vb-audio.com/Voicemeeter/) for audio routing
- [Deepgram API Key](https://deepgram.com/) for speech transcription

### Setup
1. **Clone and navigate to the project:**
   ```bash
   git clone <repository-url>
   cd salesFunnel-backend
   ```

2. **Configure environment:**
   ```bash
   # Create .env file with your Deepgram API key
   echo "DEEPGRAM_API_KEY=your_actual_deepgram_api_key" > .env
   ```

3. **Start the transcription server:**
   ```bash
   cd audio
   python -m venv .venv
   source .venv/Scripts/activate  # Windows Git Bash
   pip install -r server_requirements.txt
   python transcription_server.py
   ```

4. **Configure Voicemeeter audio routing:**
   - Route system audio to "Voicemeeter Out B1"
   - Route microphone to "Voicemeeter Out B2"

5. **Start the audio client (new terminal):**
   ```bash
   cd audio
   source .venv/Scripts/activate  # Activate same venv
   pip install -r client_requirements.txt
   python real_time_audio_client.py
   ```

For detailed setup instructions, see [`setup/SETUP.txt`](setup/SETUP.txt).

## Features

- Real-time dual-channel audio capture (microphone + system audio)
- WebSocket-based streaming to Deepgram API  
- Channel separation for conversation analysis
- Live interim and final transcription results
- REST API for accessing latest transcriptions (`GET /interim`)
- Audio debugging tools for development

## License

This project is licensed under the MIT License - see the [LICENSE](setup/LICENSE) file for details.

---

**Note:** This is a work-in-progress project focused on building the foundation for AI-assisted sales conversations. The current implementation demonstrates real-time audio transcription capabilities with plans for advanced sales funnel intelligence.
