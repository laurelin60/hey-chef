import numpy as np
import soundcard as sc
from PIL import ImageGrab
import threading
import queue
import time

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
        self.audio_queue = queue.Queue(maxsize=100)
        
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
            
        print(f"Using loopback device: {self.mic.name}")

    def start(self):
        if not self._running:
            self._running = True
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()

    def _capture_loop(self):
        # Use a smaller blocksize for more frequent updates
        with self.mic.recorder(samplerate=self.sample_rate, channels=self.channels, blocksize=self.chunk_size) as mic:
            while self._running:
                # Record a block of audio
                data = mic.record(numframes=self.chunk_size)
                if np.max(np.abs(data)) > 0:  # Only queue if we have actual audio
                    try:
                        self.audio_queue.put_nowait(data)
                    except queue.Full:
                        # If queue is full, remove oldest item
                        try:
                            self.audio_queue.get_nowait()
                            self.audio_queue.put_nowait(data)
                        except queue.Empty:
                            pass

    def stop(self):
        self._running = False
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join()
            self._capture_thread = None

    def get_audio_data(self):
        """Get all audio data that has accumulated since the last call"""
        chunks = []
        while not self.audio_queue.empty():
            chunks.append(self.audio_queue.get())
        
        if not chunks:
            return None
            
        # Concatenate all chunks into a single array
        return np.vstack(chunks)  # Use vstack for 2D arrays

    def __del__(self):
        self.stop()