from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import aiohttp
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import datetime

# Load environment variables
load_dotenv()

app = FastAPI()

# Output directory for transcription files
TRANSCRIPTION_OUTPUT_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "transcriptions"
TRANSCRIPTION_OUTPUT_DIR.mkdir(exist_ok=True)

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

def write_transcription_to_file(channel_num: int, transcript: str, confidence: float):
    """Write transcription to the appropriate channel file"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    channel_file = TRANSCRIPTION_OUTPUT_DIR / f"channel_{channel_num}.txt"
    
    with open(channel_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] (confidence: {confidence:.2f}) {transcript}\n")
    
    print(f"📝 Written to {channel_file.name}: {transcript}")

@app.websocket("/audio")
async def audio_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🎯 Client connected to audio endpoint")
    print(f"📁 Transcription files will be saved to: {TRANSCRIPTION_OUTPUT_DIR.absolute()}")
    
    # Initialize/clear channel files for this session
    for channel_num in [0, 1]:
        channel_file = TRANSCRIPTION_OUTPUT_DIR / f"channel_{channel_num}.txt"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(channel_file, "w", encoding="utf-8") as f:
            f.write(f"=== New Session Started at {timestamp} ===\n\n")
        print(f"📄 Initialized {channel_file.name}")
    
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
                                # Send audio data to Deepgram
                                await dg_ws.send_bytes(audio_data)
                                
                    except WebSocketDisconnect:
                        print("🔌 Client disconnected")
                        # Send finalize message to Deepgram before closing
                        await dg_ws.send_str('{"type":"Finalize"}')
                        await asyncio.sleep(1)  # Give time for final responses
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
                                                
                                                # Write final transcriptions to file
                                                if is_final:
                                                    write_transcription_to_file(channel_index, transcript, confidence)
                                    
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
                                                    
                                                    # Write final transcriptions to appropriate channel file
                                                    if is_final and transcript.strip():
                                                        write_transcription_to_file(i, transcript, confidence)
                                
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