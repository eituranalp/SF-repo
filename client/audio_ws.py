import asyncio
import websockets
import sounddevice as sd
import numpy as np
import os
import sys
import threading
import time

# Configuration
SYSTEM_DEVICE_NAME = "Voicemeeter Out B1"  # Voicemeeter system audio
MIC_DEVICE_NAME = "Voicemeeter Out B2"  # Voicemeeter microphone
SAMPLE_RATE = 16000
CHANNELS = 1  # Each input is mono

# Configurable chunk duration (ms). Defaults to 200ms. Set env AUDIO_CHUNK_MS to override (e.g., 100).
CHUNK_DURATION_MS = int(os.getenv("AUDIO_CHUNK_MS", "200"))
CHUNK_DURATION_SEC = CHUNK_DURATION_MS / 1000.0
BUFFER_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_SEC)

WS_SERVER_URL = "ws://localhost:8000/audio"

print("Starting raw PCM audio streaming client...")

def find_device_index(name):
    """Find device index by name"""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if name in d['name'] and d['max_input_channels'] > 0:
            return i
    print(f"Device '{name}' not found. Available devices:")
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            print(f"  {i}: {d['name']}")
    return None

# Device setup
system_index = find_device_index(SYSTEM_DEVICE_NAME)
mic_index = find_device_index(MIC_DEVICE_NAME)

if system_index is None or mic_index is None:
    print("Required audio devices not found. Exiting.")
    sys.exit(1)

# Audio buffers
system_buffer = []
mic_buffer = []
audio_lock = threading.Lock()

def system_callback(indata, frames, time, status):
    with audio_lock:
        system_buffer.extend(indata.flatten())
        # Keep buffer size reasonable
        if len(system_buffer) > BUFFER_SIZE * 2:
            system_buffer[:] = system_buffer[-BUFFER_SIZE:]

def mic_callback(indata, frames, time, status):
    with audio_lock:
        mic_buffer.extend(indata.flatten())
        # Keep buffer size reasonable  
        if len(mic_buffer) > BUFFER_SIZE * 2:
            mic_buffer[:] = mic_buffer[-BUFFER_SIZE:]

async def stream_audio():
    """Stream audio to server"""
    print(f"Connecting to WebSocket at {WS_SERVER_URL}...")
    
    chunk_count = 0
    
    async with websockets.connect(WS_SERVER_URL) as ws:
        print("Connected! Starting audio streaming...")
        
        while True:
            # Wait for the configured amount of audio data
            await asyncio.sleep(CHUNK_DURATION_SEC)
            
            with audio_lock:
                if len(mic_buffer) < BUFFER_SIZE or len(system_buffer) < BUFFER_SIZE:
                    continue
                    
                # Get the configured chunk of both microphone and system audio
                mic_chunk = np.array(mic_buffer[:BUFFER_SIZE], dtype=np.int16)
                sys_chunk = np.array(system_buffer[:BUFFER_SIZE], dtype=np.int16)
                
                # Remove used data
                del mic_buffer[:BUFFER_SIZE]
                del system_buffer[:BUFFER_SIZE]
            
            # Create stereo PCM: mic=left channel, system=right channel
            stereo_audio = np.column_stack((mic_chunk, sys_chunk))
            pcm_data = stereo_audio.tobytes()
            
            chunk_count += 1
            print(f"Sending chunk #{chunk_count}: {len(pcm_data)} bytes (~{CHUNK_DURATION_MS}ms)")
            
            # Send raw PCM data
            if pcm_data and len(pcm_data) > 0:
                await ws.send(pcm_data)
            else:
                print("No audio data to send")

async def main():
    print("Audio streaming client")
    print("=" * 30)
    print(f"System device: {system_index} ({SYSTEM_DEVICE_NAME})")
    print(f"Mic device: {mic_index} ({MIC_DEVICE_NAME})")
    print(f"Sample rate: {SAMPLE_RATE} Hz")
    print(f"Chunk size: {BUFFER_SIZE} samples ({CHUNK_DURATION_MS}ms)")
    print("=" * 30)
    
    try:
        # Start both audio streams
        sys_stream = sd.InputStream(
            device=system_index, 
            samplerate=SAMPLE_RATE,
            channels=CHANNELS, 
            dtype='int16', 
            callback=system_callback
        )
        mic_stream = sd.InputStream(
            device=mic_index, 
            samplerate=SAMPLE_RATE,
            channels=CHANNELS, 
            dtype='int16', 
            callback=mic_callback
        )
        
        print("Starting audio streams...")
        with sys_stream, mic_stream:
            print("Audio streams started, connecting to WebSocket...")
            await stream_audio()
            
    except Exception as e:
        print(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping...")