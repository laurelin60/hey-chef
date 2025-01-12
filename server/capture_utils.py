import numpy as np
import soundcard as sc
from PIL import ImageGrab, Image
import threading
import queue
import time
import warnings
from screeninfo import get_monitors

def is_frame_black(frame):
    """Check if a PIL Image is completely or almost completely black."""
    if frame is None:
        return True
    # Convert to numpy array and check all color channels
    frame_array = np.array(frame)
    # Calculate the mean pixel value across all channels
    mean_value = np.mean(frame_array)
    # print(f"Mean pixel value: {mean_value}")  # Debug info
    # If mean is very close to 0, frame is essentially black
    return mean_value < 1.0

class ScreenCapture:
    def __init__(self, custom_crop_box=None):
        self._last_frame = None
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._running = False
        
        # Find secondary monitor
        monitors = get_monitors()
        # print("\nDetailed monitor information:")
        # for i, m in enumerate(monitors):
        #     print(f"Monitor {i}:")
        #     print(f"  Name: {m.name}")
        #     print(f"  Resolution: {m.width}x{m.height}")
        #     print(f"  Position: ({m.x}, {m.y})")
        #     print(f"  Primary: {m.is_primary}")
            
        # Try using the non-primary monitor
        self.monitor = None
        for m in monitors:
            if not m.is_primary:
                self.monitor = m
                break
                
        if self.monitor is None:
            raise RuntimeError("No secondary monitor found")
            
        # print(f"\nSelected monitor:")
        # print(f"  Name: {self.monitor.name}")
        # print(f"  Resolution: {self.monitor.width}x{self.monitor.height}")
        # print(f"  Position: ({self.monitor.x}, {self.monitor.y})")
        
        # Default crop box for vertical bar (hardcoded dimensions from test_capture.py)
        bar_width = 550
        top_crop = 46
        bottom_crop = 54
        default_crop = (
            1920//2 - bar_width//2,  # Center horizontally
            top_crop,                # Crop from top
            1920//2 + bar_width//2,  # Right edge
            1080 - bottom_crop       # Crop from bottom
        )
        
        # Use custom crop box if provided, otherwise use default
        crop_box = custom_crop_box if custom_crop_box is not None else default_crop
        
        # Calculate the exact region to capture
        left = self.monitor.x + crop_box[0]
        top = self.monitor.y + crop_box[1]
        right = self.monitor.x + crop_box[2]
        bottom = self.monitor.y + crop_box[3]
        self.capture_bounds = (left, top, right, bottom)
        
        # Calculate downscaled dimensions
        self.target_width = (right - left) // 2
        self.target_height = (bottom - top) // 2
            
        # print(f"Capture bounds: {self.capture_bounds}")
        # print(f"Downscaled size: {self.target_width}x{self.target_height}")
        
        # Create a lock for thread safety
        self._lock = threading.Lock()
        self.start()
    
    def start(self):
        self._running = True
        self._capture_thread.start()
    
    def stop(self):
        self._running = False
        if self._capture_thread.is_alive():
            self._capture_thread.join()
    
    def _capture_loop(self):
        last_capture_time = 0
        target_interval = 1.0 / 30  # Target 30 FPS
        
        while self._running:
            current_time = time.time()
            elapsed = current_time - last_capture_time
            
            if elapsed >= target_interval:
                try:
                    # Capture and downscale in one step
                    frame = ImageGrab.grab(bbox=self.capture_bounds, all_screens=True)
                    if frame:
                        frame = frame.resize((self.target_width, self.target_height), Image.Resampling.LANCZOS)
                        with self._lock:
                            self._last_frame = frame
                    last_capture_time = current_time
                except Exception as e:
                    print(f"Capture error: {e}")
            else:
                # Sleep for the remaining time to maintain target FPS
                sleep_time = target_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
    
    def get_last_frame(self):
        with self._lock:
            return self._last_frame if self._last_frame else None

class AudioCapture:
    """
    A class to capture Windows system audio output using soundcard library.
    """
    def __init__(self, sample_rate=44100, channels=2, chunk_size=1024):
        self._running = False
        self._capture_thread = None
        self.audio_queue = queue.Queue(maxsize=10000)
        self._ready = threading.Event()
        self._data_available = threading.Condition()
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        
        # Get default microphone that can capture system audio
        mics = sc.all_microphones(include_loopback=True)
        if not mics:
            raise RuntimeError("Could not find any loopback audio devices")
        
        self.mic = None
        # Find a loopback device
        for mic in mics:
            #if 'speakers (realtek(r) audio)' in mic.name.lower():
            if 'headphones (oculus virtual audio device)' in mic.name.lower(): # we can route the whatsapp audio to this device
                self.mic = mic
                break
        
        if self.mic is None:
            raise RuntimeError("Could not find specified audio device to capture")
        
        print(f"Using {self.mic.name} as captured audio device")
        

    def start(self):
        if not self._running:
            self._running = True
            self._ready.clear()
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()
            self._ready.wait(timeout=5.0)

    def _capture_loop(self):
        warnings.filterwarnings('ignore', category=sc.SoundcardRuntimeWarning)
        try:
            if self.mic is None:
                return None
            with self.mic.recorder(samplerate=self.sample_rate, channels=self.channels, blocksize=self.chunk_size) as mic:
                self._ready.set()
                while self._running:
                    try:
                        data = mic.record(numframes=self.chunk_size)
                        max_amplitude = np.max(np.abs(data))
                        if max_amplitude > 0:
                            with self._data_available:
                                try:
                                    self.audio_queue.put_nowait(data)
                                    self._data_available.notify()
                                except queue.Full:
                                    try:
                                        self.audio_queue.get_nowait()
                                        self.audio_queue.put_nowait(data)
                                    except queue.Empty:
                                        pass
                    except Exception as e:
                        if not self._running:
                            break
        except Exception as e:
            self._ready.set()

    def stop(self):
        self._running = False
        self._ready.clear()
        with self._data_available:
            self._data_available.notify_all()
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join()
            self._capture_thread = None

    def get_audio_data(self, timeout=0.1):
        """Get all audio data that has accumulated since the last call"""
        if not self._ready.is_set():
            return None
            
        with self._data_available:
            if self.audio_queue.empty():
                self._data_available.wait(timeout=timeout)
            
            chunks = []
            try:
                while not self.audio_queue.empty():
                    chunks.append(self.audio_queue.get_nowait())
            except (queue.Empty, IndexError):
                pass
            
            if not chunks:
                return None
                
            return np.vstack(chunks)

    def __del__(self):
        self.stop()