# Sales Funnel Call Assistant

## Overview

This project is a **work-in-progress** real-time call assistant designed to support structured sales funnel conversations. It captures audio from calls (Zoom, Meet, Teams), transcribes speech in real time, and aligns the output to custom sales funnel stages.

The system processes and separates both the salesperson (microphone) and prospect (system audio) channels, enabling clear transcription and later analysis of sales conversations.

## Current Progress

**Completed:**
- Real-time dual-channel audio capture and streaming  
- Integration with Deepgram API for speech-to-text transcription  
- Channel separation (microphone vs. system audio)  
- WebSocket-based audio streaming architecture  
- Interim and final transcription result handling  
- Audio debugging and monitoring utilities  

**In Development:**
- Funnel stage detection and classification  
- Real-time guidance system  
- Custom sales playbook integration  
- Conversation analytics and reporting  

## Tech Stack

### Core Technologies
- **Python 3.8+** – Primary development language  
- **FastAPI** – Asynchronous web framework for the transcription server  
- **WebSockets** – Real-time bidirectional communication  
- **Deepgram API** – Speech-to-text transcription service  

### Audio Processing
- **SoundDevice** – Audio capture for system and microphone input  
- **NumPy** – Numerical operations for audio data handling  
- **Voicemeeter** – Virtual audio mixer for routing and separation. This is for temporary use.
- **FFmpeg** – Multimedia framework used in testing utilities  

### Additional Libraries
- **asyncio** – Asynchronous stream management  
- **aiohttp** – Async HTTP client for WebSocket connections  
- **python-dotenv** – Environment configuration management  

## Project Structure

├── audio/ # Application components
│ ├── transcription_server.py # FastAPI transcription server
│ ├── real_time_audio_client.py # Audio capture client
│ ├── server_requirements.txt # Server dependencies
│ ├── client_requirements.txt # Client dependencies
│ ├── tests/ # Test scripts and utilities
│ └── transcriptions/ # Transcribed conversation outputs
│
└── setup/ # Setup documentation and utilities
├── SETUP.txt # Detailed setup instructions
├── LICENSE # License file
└── ffmpeg.exe # Audio processing utility

## Quick Start

### Prerequisites
- Python 3.8+  
- [Voicemeeter](https://vb-audio.com/Voicemeeter/) for audio routing  
- [Deepgram API Key](https://deepgram.com/) for speech transcription  

### Setup

1. **Clone and navigate to the project
2. Configure environment: echo "DEEPGRAM_API_KEY=your_actual_deepgram_api_key" > .env
3. Start the transcription server: install server_requirements.txt, run python transcription_server.py
4. Configure Voicemeeter routing: Route system audio to "Voicemeeter Out B1", Route microphone to "Voicemeeter Out B2".
5. Start the audio client: install client_requirements.txt, run python real_time_audio_client.py

For more detailed setup instructions, see setup/SETUP.txt

## Features

- Real-time dual-channel audio capture (microphone and system audio)
- WebSocket-based audio streaming to a transcription server
- Integration with Deepgram for speech-to-text
- Channel separation for clear conversation analysis
- Live interim and final transcription output
- REST endpoint for accessing the latest transcription (`GET /interim`)
- Audio debugging and monitoring utilities for development

## License

This project uses a non-commercial license.  
See the LICENSE file for details.

## Project Status

This repository is an active work in progress.  
Current functionality demonstrates:
- Real-time audio capture
- Dual-channel separation
- Live transcription via Deepgram
- Basic server/client architecture over WebSockets

Planned additions include:
- Funnel stage tracking and classification
- Real-time guidance logic
- Custom sales playbook integration
- Conversation analytics and metrics
- Improved UI for live call assistance

## Contributing

This project is currently under solo development.  
Suggestions, issue reports, or feedback are welcome through GitHub Issues.

## Disclaimer

This project is intended for personal, educational, and experimental use.  
Commercial use is not permitted without explicit permission.

