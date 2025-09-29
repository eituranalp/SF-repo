import asyncio
import websockets
import sounddevice as sd
import numpy as np
import subprocess
import os
import sys
import threading
import queue
import time

# Configuration
SYSTEM_DEVICE_NAME = "Voicemeeter Out B1"
MIC_DEVICE_NAME = "Voicemeeter Out B2"
SAMPLE_RATE = 16000
CHANNELS = 1  # Each input is mono
BUFFER_SIZE = int(SAMPLE_RATE * 0.5)  # 500ms buffer
WS_SERVER_URL = "ws://localhost:8000/audio"

def find_device_index(name):
    """Find device index by name, fallback to default input"""
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if name in d['name'] and d['max_input_channels'] > 0:
            return i
    return sd.default.device[0]

# Device setup
system_index = find_device_index(SYSTEM_DEVICE_NAME)
mic_index = find_device_index(MIC_DEVICE_NAME)

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

def encode_audio_batch(audio_data):
    """Encode a batch of stereo audio using FFmpeg"""
    ffmpeg_path = os.path.join(os.path.dirname(__file__), 'bin', 'ffmpeg.exe')
    
    cmd = [
        ffmpeg_path,
        '-f', 's16le',
        '-ar', str(SAMPLE_RATE),
        '-ac', '2',  # stereo
        '-i', 'pipe:0',
        '-c:a', 'libopus',
        '-f', 'ogg',
        '-b:a', '64k',
        '-loglevel', 'error',
        'pipe:1'
    ]
    
    try:
        result = subprocess.run(
            cmd,
            input=audio_data,
            capture_output=True,
            timeout=5  # 5 second timeout
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"FFmpeg error: {result.stderr.decode()}")
            return None
            
    except subprocess.TimeoutExpired:
        print("FFmpeg timeout")
        return None
    except Exception as e:
        print(f"FFmpeg encoding error: {e}")
        return None

async def stream_audio():
    """Stream audio using batch encoding approach"""
    print(f"Connecting to WebSocket at {WS_SERVER_URL}...")
    
    async with websockets.connect(WS_SERVER_URL) as ws:
        print("Connected! Starting audio streaming...")
        
        while True:
            # Wait for enough audio data
            await asyncio.sleep(0.5)  # 500ms intervals
            
            with audio_lock:
                if len(mic_buffer) < BUFFER_SIZE or len(system_buffer) < BUFFER_SIZE:
                    continue
                    
                # Get 500ms of audio
                mic_chunk = np.array(mic_buffer[:BUFFER_SIZE], dtype=np.int16)
                sys_chunk = np.array(system_buffer[:BUFFER_SIZE], dtype=np.int16)
                
                # Remove used data
                del mic_buffer[:BUFFER_SIZE]
                del system_buffer[:BUFFER_SIZE]
            
            # Create stereo audio (mic=left, system=right)
            stereo_audio = np.column_stack((mic_chunk, sys_chunk))
            pcm_data = stereo_audio.tobytes()
            
            print(f"Encoding {len(pcm_data)} bytes of audio...")
            
            # Encode in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            ogg_data = await loop.run_in_executor(None, encode_audio_batch, pcm_data)
            
            if ogg_data and len(ogg_data) > 0:
                await ws.send(ogg_data)
                print(f"Sent {len(ogg_data)} bytes to server")
            else:
                print("Failed to encode audio")

async def main():
    print("Initializing audio streams...")
    print(f"System device: {system_index}")
    print(f"Mic device: {mic_index}")
    
    try:
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
        
        print("Audio streams created, starting...")
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
        print("Stopping...")