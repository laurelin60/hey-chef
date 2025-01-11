import numpy as np
import soundcard as sc
from PIL import ImageGrab
import threading
import queue
import time
import warnings

class ScreenCapture:
    def __init__(self):
        self._last_frame = None
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._running = False
        self.start()
    
    def start(self):
        self._running = True
        self._capture_thread.start()
    
    def stop(self):
        self._running = False
        if self._capture_thread.is_alive():
            self._capture_thread.join()
    
    def _capture_loop(self):
        while self._running:
            self._last_frame = ImageGrab.grab()
            time.sleep(1/30)  # Limit to ~30 FPS
    
    def get_last_frame(self):
        return self._last_frame

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
        
        # Find a loopback device
        self.mic = mics[0]  # Default to first available device
        for mic in mics:
            if 'loopback' in mic.name.lower():
                self.mic = mic
                break

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