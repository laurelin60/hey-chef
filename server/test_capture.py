from server.capture_utils import ScreenCapture, AudioCapture, is_frame_black
from server.mic_utils import VirtualMicrophone
import time
from PIL import Image
import numpy as np
import wave
import struct
import cv2

def test_screen_capture():
    print("Testing screen capture...")
    
    # Create screen capture with default vertical bar region
    screen_cap = ScreenCapture()
    
    # Create window with specific properties
    window_name = 'Secondary Monitor Capture'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    # Set window size and position (using hardcoded values matching the downscaled capture)
    cv2.resizeWindow(window_name, 275, 490)  # Half of 550x980
    cv2.moveWindow(window_name, 100, 100)  # Position window away from corner
    
    try:
        while True:
            frame = screen_cap.get_last_frame()
            if frame:
                # Convert PIL image to OpenCV format
                frame_array = np.array(frame)
                if len(frame_array.shape) == 3:  # Color image
                    cv_frame = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
                else:  # Grayscale image
                    cv_frame = frame_array
                
                # Display the frame
                cv2.imshow(window_name, cv_frame)
                
                # Break loop on 'q' press
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                print("No frame captured")
            
            time.sleep(1/30)  # Limit refresh rate
            
    except KeyboardInterrupt:
        print("\nStopping capture...")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        screen_cap.stop()
        cv2.destroyAllWindows()

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
    test_screen_capture() 