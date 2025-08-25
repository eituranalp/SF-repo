from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import aiohttp
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import datetime
import wave
from array import array

# Load environment variables
load_dotenv()

app = FastAPI()

# Output directory for transcription files
TRANSCRIPTION_OUTPUT_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "transcriptions"
TRANSCRIPTION_OUTPUT_DIR.mkdir(exist_ok=True)

# Directory to write debug WAV snippets per channel
AUDIO_CHUNKS_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "audio_chunks"
AUDIO_CHUNKS_DIR.mkdir(exist_ok=True)

# In-memory store for latest interim transcripts (per channel)
LATEST_INTERIM = {
    0: {"transcript": "", "confidence": 0.0, "timestamp": ""},
    1: {"transcript": "", "confidence": 0.0, "timestamp": ""}
}

@app.get("/interim")
async def get_interim():
    """Return the latest interim transcript for each channel."""
    return {"channels": LATEST_INTERIM}

# Deepgram configuration
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY environment variable is required")

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"
DEEPGRAM_PARAMS = {
    "encoding": "linear16",
    "sample_rate": 16000,
    "channels": 2,
    "multichannel": "true",
    "interim_results": "true",
    "punctuate": "true"
}

# Debug configuration (optional)
AUDIO_DEBUG = os.getenv("AUDIO_DEBUG", "false").lower() in ("1", "true", "yes", "on")
AUDIO_DEBUG_SNIPPET_MS = int(os.getenv("AUDIO_DEBUG_SNIPPET_MS", "2000"))  # length per WAV snippet
AUDIO_DEBUG_MAX_SNIPPETS = int(os.getenv("AUDIO_DEBUG_MAX_SNIPPETS", "30"))  # per channel limit

def write_transcription_to_file(channel_num: int, transcript: str, confidence: float):
    """Write transcription to the appropriate channel file"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_file = TRANSCRIPTION_OUTPUT_DIR / f"channel_{channel_num}.txt"
    
    with open(channel_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] (confidence: {confidence:.2f}) {transcript}\n")
    
    print(f"📝 Written to {channel_file.name}: {transcript}")

def write_interim_to_file(channel_num: int, transcript: str, confidence: float):
    """Write the latest interim transcription to a channel-specific interim file (overwrite)."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    interim_file = TRANSCRIPTION_OUTPUT_DIR / f"channel_{channel_num}_interim.txt"
    with open(interim_file, "w", encoding="utf-8") as f:
        if transcript and transcript.strip():
            f.write(f"[{timestamp}] (confidence: {confidence:.2f}) {transcript}\n")
        else:
            f.write(f"[{timestamp}] <no interim>\n")

def write_wav_mono(file_path: Path, sample_rate: int, data_bytes: bytes):
    """Write mono 16-bit PCM bytes to a WAV file."""
    with wave.open(str(file_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        wf.writeframes(data_bytes)

@app.websocket("/audio")
async def audio_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🎯 Client connected to audio endpoint")
    print(f"📁 Transcription files will be saved to: {TRANSCRIPTION_OUTPUT_DIR.absolute()}")
    if AUDIO_DEBUG:
        print(f"🎧 Audio debug mode ON: writing ~{AUDIO_DEBUG_SNIPPET_MS}ms WAV snippets per channel to {AUDIO_CHUNKS_DIR}")
    
    # Initialize/clear channel files for this session
    for channel_num in [0, 1]:
        channel_file = TRANSCRIPTION_OUTPUT_DIR / f"channel_{channel_num}.txt"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(channel_file, "w", encoding="utf-8") as f:
            f.write(f"=== New Session Started at {timestamp} ===\n\n")
        print(f"📄 Initialized {channel_file.name}")
        # Initialize interim files and in-memory state
        LATEST_INTERIM[channel_num] = {"transcript": "", "confidence": 0.0, "timestamp": ""}
        interim_file = TRANSCRIPTION_OUTPUT_DIR / f"channel_{channel_num}_interim.txt"
        with open(interim_file, "w", encoding="utf-8") as f:
            f.write(f"=== Interim Initialized at {timestamp} ===\n")

    # Debug buffers and counters (per connection)
    debug_left_buffer = bytearray()
    debug_right_buffer = bytearray()
    debug_snippet_idx = {0: 0, 1: 0}
    target_bytes_per_channel = int(DEEPGRAM_PARAMS["sample_rate"] * (AUDIO_DEBUG_SNIPPET_MS / 1000.0) * 2)
    
    # Build Deepgram WebSocket URL with parameters
    params_str = "&".join([f"{k}={v}" for k, v in DEEPGRAM_PARAMS.items()])
    dg_url = f"{DEEPGRAM_WS_URL}?{params_str}"
    
    try:
        # Connect to Deepgram WebSocket
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Token {DEEPGRAM_API_KEY}"}
            
            async with session.ws_connect(dg_url, headers=headers) as dg_ws:
                print("🔗 Connected to Deepgram WebSocket")
                
                # Create tasks for handling both directions
                async def forward_audio():
                    """Forward audio from client to Deepgram"""
                    try:
                        while True:
                            # Receive audio data from client
                            audio_data = await websocket.receive_bytes()
                            
                            if audio_data:
                                # Debug: deinterleave and write periodic WAV snippets per channel
                                if AUDIO_DEBUG:
                                    try:
                                        samples = array('h')
                                        samples.frombytes(audio_data)
                                        left_samples = samples[0::2]
                                        right_samples = samples[1::2]
                                        debug_left_buffer.extend(left_samples.tobytes())
                                        debug_right_buffer.extend(right_samples.tobytes())
                                        # Flush to WAV when enough data accumulated
                                        for ch, buf in ((0, debug_left_buffer), (1, debug_right_buffer)):
                                            while len(buf) >= target_bytes_per_channel and debug_snippet_idx[ch] < AUDIO_DEBUG_MAX_SNIPPETS:
                                                idx = debug_snippet_idx[ch]
                                                file_path = AUDIO_CHUNKS_DIR / f"channel_{ch}_snippet_{idx:04d}.wav"
                                                write_wav_mono(file_path, DEEPGRAM_PARAMS["sample_rate"], bytes(buf[:target_bytes_per_channel]))
                                                del buf[:target_bytes_per_channel]
                                                debug_snippet_idx[ch] += 1
                                    except Exception as e:
                                        print(f"⚠️ Audio debug write failed: {e}")
                                # Send audio data to Deepgram
                                await dg_ws.send_bytes(audio_data)
                                
                    except WebSocketDisconnect:
                        print("🔌 Client disconnected")
                        # Send finalize message to Deepgram before closing
                        await dg_ws.send_str('{"type":"Finalize"}')
                        await asyncio.sleep(1)  # Give time for final responses
                        # On disconnect, flush any remaining partial buffers as final snippets
                        if AUDIO_DEBUG:
                            try:
                                if len(debug_left_buffer) > 0 and debug_snippet_idx[0] < AUDIO_DEBUG_MAX_SNIPPETS:
                                    file_path = AUDIO_CHUNKS_DIR / f"channel_0_snippet_{debug_snippet_idx[0]:04d}_final.wav"
                                    write_wav_mono(file_path, DEEPGRAM_PARAMS["sample_rate"], bytes(debug_left_buffer))
                                    debug_snippet_idx[0] += 1
                                if len(debug_right_buffer) > 0 and debug_snippet_idx[1] < AUDIO_DEBUG_MAX_SNIPPETS:
                                    file_path = AUDIO_CHUNKS_DIR / f"channel_1_snippet_{debug_snippet_idx[1]:04d}_final.wav"
                                    write_wav_mono(file_path, DEEPGRAM_PARAMS["sample_rate"], bytes(debug_right_buffer))
                                    debug_snippet_idx[1] += 1
                            except Exception as e:
                                print(f"⚠️ Audio debug final flush failed: {e}")
                        await dg_ws.close()
                    except Exception as e:
                        print(f"❌ Error forwarding audio: {e}")
                
                async def handle_transcriptions():
                    """Handle transcription responses from Deepgram"""
                    try:
                        async for msg in dg_ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                try:
                                    response = json.loads(msg.data)
                                    
                                    # Check if this is a transcription result
                                    if "channel" in response and "alternatives" in response["channel"]:
                                        channel_data = response["channel"]
                                        alternatives = channel_data["alternatives"]
                                        
                                        if alternatives:
                                            transcript = alternatives[0].get("transcript", "")
                                            is_final = response.get("is_final", False)
                                            confidence = alternatives[0].get("confidence", 0)
                                            channel_index = response.get("channel_index", [0])[0]
                                            
                                            if transcript and transcript.strip():
                                                # Print transcription with channel info
                                                status = "FINAL" if is_final else "INTERIM"
                                                print(f"🎤 [{status}] Channel {channel_index}: {transcript} (confidence: {confidence:.2f})")
                                                
                                                # Update interim or write final
                                                if is_final:
                                                    write_transcription_to_file(channel_index, transcript, confidence)
                                                    # Clear interim state after finalizing
                                                    LATEST_INTERIM[channel_index] = {"transcript": "", "confidence": 0.0, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                                                    write_interim_to_file(channel_index, "", 0.0)
                                                else:
                                                    # Store and write the latest interim
                                                    LATEST_INTERIM[channel_index] = {
                                                        "transcript": transcript,
                                                        "confidence": float(confidence or 0.0),
                                                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                    }
                                                    write_interim_to_file(channel_index, transcript, confidence)
                                    
                                    # Handle multichannel results
                                    elif "results" in response and "channels" in response["results"]:
                                        channels = response["results"]["channels"]
                                        is_final = response.get("is_final", False)
                                        status = "FINAL" if is_final else "INTERIM"
                                        
                                        for i, channel in enumerate(channels):
                                            if "alternatives" in channel and channel["alternatives"]:
                                                transcript = channel["alternatives"][0]["transcript"]
                                                confidence = channel["alternatives"][0].get("confidence", 0)
                                                if transcript:
                                                    print(f"🎤 [{status}] Channel {i}: {transcript} (confidence: {confidence:.2f})")
                                                    
                                                    # Update interim or write final
                                                    if is_final and transcript.strip():
                                                        write_transcription_to_file(i, transcript, confidence)
                                                        LATEST_INTERIM[i] = {"transcript": "", "confidence": 0.0, "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                                                        write_interim_to_file(i, "", 0.0)
                                                    elif transcript.strip():
                                                        LATEST_INTERIM[i] = {
                                                            "transcript": transcript,
                                                            "confidence": float(confidence or 0.0),
                                                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                                        }
                                                        write_interim_to_file(i, transcript, confidence)
                                
                                except json.JSONDecodeError as e:
                                    print(f"❌ Error parsing Deepgram response: {e}")
                                except KeyError as e:
                                    print(f"❌ Unexpected response format: {e}")
                            
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                print(f"❌ Deepgram WebSocket error: {dg_ws.exception()}")
                                break
                                
                    except Exception as e:
                        print(f"❌ Error handling transcriptions: {e}")
                
                # Run both tasks concurrently
                await asyncio.gather(
                    forward_audio(),
                    handle_transcriptions(),
                    return_exceptions=True
                )
                
    except Exception as e:
        print(f"❌ Error connecting to Deepgram: {e}")
    finally:
        print("🔚 Audio endpoint session ended")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)