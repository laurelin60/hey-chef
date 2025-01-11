from server.capture_utils import ScreenCapture, AudioCapture
from server.mic_utils import VirtualMicrophone
import time
from PIL import Image
import numpy as np
import wave
import struct

def test_screen_capture():
    print("Testing screen capture...")
    screen_cap = ScreenCapture()
    
    # Wait a bit for first capture
    time.sleep(0.1)
    
    # Get and save a frame
    frame = screen_cap.get_last_frame()
    if frame:
        frame.save("test_screenshot.png")
        print("Screenshot saved as 'test_screenshot.png'")
    
    screen_cap.stop()

def test_audio_capture():
    print("\nTesting audio capture and virtual microphone...")
    audio_cap = AudioCapture()
    virtual_mic = VirtualMicrophone(
        sample_rate=audio_cap.sample_rate,
        channels=audio_cap.channels,
        buffer_size=audio_cap.chunk_size
    )
    
    audio_cap.start()
    virtual_mic.start()
    
    print("Streaming audio to virtual microphone...")
    print("Press Ctrl+C to stop...")
    
    last_log_time = time.time()
    data_count = 0
    
    try:
        while True:
            data = audio_cap.get_audio_data()
            if data is not None:
                data_count += 1
                virtual_mic.write(data)
                
                # Log stats every second
                current_time = time.time()
                if current_time - last_log_time >= 1.0:
                    print(f"Audio chunks processed in last second: {data_count}")
                    if data_count > 0:
                        print(f"Last chunk shape: {data.shape}, max amplitude: {np.max(np.abs(data))}")
                    data_count = 0
                    last_log_time = current_time
                    
            time.sleep(0.001)  # Small sleep to prevent CPU overuse
    except KeyboardInterrupt:
        print("\nStopping audio capture and virtual microphone...")
    finally:
        audio_cap.stop()
        virtual_mic.stop()

if __name__ == "__main__":
    test_audio_capture() 