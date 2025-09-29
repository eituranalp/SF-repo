#!/usr/bin/env python3
"""Test script to verify audio files and channel separation"""

import os
import subprocess
import glob
from pathlib import Path

def test_audio_files():
    """Test the recorded audio files"""
    
    print("AUDIO FILE TESTING SUITE")
    print("=" * 50)
    
    # Find all OGG files in server directory
    server_dir = Path("../server/audio_chunks")
    ogg_files = list(server_dir.glob("*.ogg"))
    
    if not ogg_files:
        print("No audio files found in server/audio_chunks/")
        return
    
    print(f"Found {len(ogg_files)} audio files")
    print(f"Directory: {server_dir.absolute()}")
    
    # Test the latest/largest file
    latest_file = max(ogg_files, key=lambda f: f.stat().st_size)
    print(f"\nTesting file: {latest_file.name}")
    print(f"Size: {latest_file.stat().st_size} bytes")
    
    # Get detailed info about the file
    ffmpeg_path = os.path.join(os.path.dirname(__file__), 'bin', 'ffmpeg.exe')
    
    print("\nAUDIO PROPERTIES:")
    print("-" * 30)
    
    info_cmd = [
        ffmpeg_path, '-i', str(latest_file),
        '-hide_banner', '-f', 'null', '-'
    ]
    
    try:
        result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=10)
        stderr_lines = result.stderr.split('\n')
        
        for line in stderr_lines:
            if 'Duration:' in line or 'Stream' in line or 'Audio:' in line:
                print(f"  {line.strip()}")
                
    except Exception as e:
        print(f"Error getting file info: {e}")
    
    # Extract channels for testing
    print(f"\nCHANNEL SEPARATION TEST:")
    print("-" * 30)
    
    try:
        # Extract left channel (should be microphone)
        left_cmd = [
            ffmpeg_path, '-i', str(latest_file),
            '-af', 'pan=mono|c0=0.5*c0',
            '-y', 'test_mic_channel.wav'
        ]
        
        result = subprocess.run(left_cmd, capture_output=True, timeout=10)
        if result.returncode == 0:
            print("Left channel (MIC) extracted -> test_mic_channel.wav")
        else:
            print("Failed to extract left channel")
            
        # Extract right channel (should be system audio)
        right_cmd = [
            ffmpeg_path, '-i', str(latest_file),
            '-af', 'pan=mono|c0=0.5*c1', 
            '-y', 'test_system_channel.wav'
        ]
        
        result = subprocess.run(right_cmd, capture_output=True, timeout=10)
        if result.returncode == 0:
            print("Right channel (SYSTEM) extracted -> test_system_channel.wav")
        else:
            print("Failed to extract right channel")
            
        # Convert original to WAV for easier playback
        wav_cmd = [
            ffmpeg_path, '-i', str(latest_file),
            '-y', 'test_stereo_full.wav'
        ]
        
        result = subprocess.run(wav_cmd, capture_output=True, timeout=10)
        if result.returncode == 0:
            print("Full stereo converted -> test_stereo_full.wav")
        else:
            print("Failed to convert to WAV")
            
    except Exception as e:
        print(f"Error extracting channels: {e}")
    
    # Show test files created
    test_files = glob.glob("test_*.wav")
    if test_files:
        print(f"\nTEST FILES CREATED:")
        print("-" * 30)
        for file in test_files:
            size = os.path.getsize(file)
            print(f"  {file} ({size} bytes)")
    
    print(f"\nHOW TO TEST:")
    print("-" * 30)
    print("1. Play 'test_stereo_full.wav' → Should hear both mic + system")
    print("2. Play 'test_mic_channel.wav' → Should hear only microphone audio")  
    print("3. Play 'test_system_channel.wav' → Should hear only system audio")
    print("\nUse Windows Media Player, VLC, or any audio player")
    print("Or double-click the .wav files to play them")
    
    print(f"\nSUMMARY:")
    print("-" * 30)
    print(f"Total files: {len(ogg_files)}")
    print(f"Latest file: {latest_file.name}")
    print(f"Format: Opus in OGG, Stereo, ~500ms chunks")
    print(f"Channels: Left=Mic, Right=System")

if __name__ == "__main__":
    test_audio_files()