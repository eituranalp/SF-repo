#!/usr/bin/env python3
"""Live monitoring of audio streaming performance"""

import time
import os
from pathlib import Path

def live_monitor():
    """Monitor audio streaming in real-time"""
    print("LIVE STREAMING MONITOR")
    print("=" * 40)
    print("Monitoring server/audio_chunks/ directory...")
    print("Press Ctrl+C to stop\n")
    
    server_dir = Path("../server/audio_chunks")
    if not server_dir.exists():
        print("Server audio directory not found")
        return
    
    last_count = 0
    last_time = time.time()
    session_start = time.time()
    total_files = 0
    total_size = 0
    
    try:
        while True:
            # Count current files
            current_files = list(server_dir.glob("*.ogg"))
            current_count = len(current_files)
            current_time = time.time()
            
            # Calculate stats
            new_files = current_count - last_count
            time_diff = current_time - last_time
            session_time = current_time - session_start
            
            if new_files > 0:
                # Get size of new files
                recent_files = sorted(current_files, key=lambda f: f.stat().st_mtime)[-new_files:]
                new_size = sum(f.stat().st_size for f in recent_files)
                total_files += new_files
                total_size += new_size
                
                # Calculate rates
                files_per_sec = new_files / time_diff if time_diff > 0 else 0
                bytes_per_sec = new_size / time_diff if time_diff > 0 else 0
                avg_session_rate = total_files / session_time if session_time > 0 else 0
                avg_file_size = new_size / new_files if new_files > 0 else 0
                
                # Determine mode
                if files_per_sec > 7:
                    mode = "HIGH-FREQ"
                    color = "🟢"
                elif files_per_sec > 1.5:
                    mode = "STANDARD"
                    color = "🟡"
                else:
                    mode = "SLOW"
                    color = "🔴"
                
                # Display update
                print(f"{color} {mode} | "
                      f"{new_files} files | "
                      f"{files_per_sec:.1f}/s | "
                      f"{avg_file_size:.0f}B avg | "
                      f"{bytes_per_sec/1024:.1f} KB/s | "
                      f"Session: {avg_session_rate:.1f}/s")
            
            last_count = current_count
            last_time = current_time
            time.sleep(1)  # Update every second
            
    except KeyboardInterrupt:
        print(f"\nFINAL SESSION STATS:")
        print(f"  Duration: {session_time:.1f} seconds")
        print(f"  Total files: {total_files}")
        print(f"  Total data: {total_size:,} bytes ({total_size/1024:.1f} KB)")
        print(f"  Average rate: {total_files/session_time:.1f} files/second")
        print(f"  Average throughput: {total_size/session_time/1024:.1f} KB/second")

if __name__ == "__main__":
    live_monitor()