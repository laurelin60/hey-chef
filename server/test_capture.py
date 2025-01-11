from server.capture_utils import ScreenCapture, AudioCapture
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
    print("\nTesting audio capture...")
    audio_cap = AudioCapture()
    audio_cap.start()
    
    print("Recording for 5 seconds...")
    audio_data = []
    start_time = time.time()
    while time.time() - start_time < 5:
        data = audio_cap.get_audio_data()
        if data is not None:
            audio_data.append(data)
        time.sleep(0.01)  # Small sleep to prevent busy waiting
    
    audio_cap.stop()
    
    if audio_data:
        # Combine all audio chunks
        combined_audio = np.vstack(audio_data)
        duration = len(combined_audio) / audio_cap.sample_rate
        print(f"Captured {len(combined_audio)} audio samples")
        print(f"Audio duration: {duration:.3f} seconds")
        print(f"Audio shape: {combined_audio.shape}")
        print(f"Max amplitude: {np.max(np.abs(combined_audio))}")
        
        # Verify duration is close to 5 seconds
        if abs(duration - 5.0) > 0.1:  # Allow 0.1 second tolerance
            print(f"WARNING: Audio duration ({duration:.3f}s) is not close to expected 5 seconds!")
        
        # Save as WAV file
        wav_file = "test_recording.wav"
        with wave.open(wav_file, 'wb') as wf:
            wf.setnchannels(audio_cap.channels)
            wf.setsampwidth(2)  # 2 bytes per sample (16-bit)
            wf.setframerate(audio_cap.sample_rate)
            
            # Convert float32 to int16, preserving stereo
            audio_int16 = (combined_audio * 32767).astype(np.int16)
            wf.writeframes(audio_int16.tobytes())
        
        print(f"Audio saved to '{wav_file}'")
    else:
        print("No audio data captured")

if __name__ == "__main__":
    test_audio_capture() 