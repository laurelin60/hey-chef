import sounddevice as sd
import numpy as np
import threading
import queue
import time

class VirtualMicrophone:
    def __init__(self, sample_rate=44100, channels=2, buffer_size=1024):
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer_size = buffer_size
        self.audio_queue = queue.Queue(maxsize=100)
        self._running = False
        self._stream = None
        self._thread = None
        
        # Find the VB-Audio Virtual Cable device
        devices = sd.query_devices()
        self.device = None
        for i, dev in enumerate(devices):
            if 'CABLE Input' in dev['name']:  # We want to output to CABLE Input (it becomes CABLE Output for other apps)
                self.device = i
                print(f"Using virtual audio device: {dev['name']}")
                break
                
        if self.device is None:
            raise RuntimeError("Could not find VB-Audio Virtual Cable. Please make sure it's installed.")

    def _audio_callback(self, outdata, frames, time, status):
        try:
            data = self.audio_queue.get_nowait()
            if len(data) < frames:
                outdata[:len(data)] = data
                outdata[len(data):] = np.zeros((frames - len(data), self.channels))
            else:
                outdata[:] = data[:frames]
        except queue.Empty:
            outdata.fill(0)

    def start(self):
        if self._running:
            return

        self._running = True
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._audio_callback,
            blocksize=self.buffer_size,
            device=self.device  # Specify the virtual cable device
        )
        self._stream.start()

    def stop(self):
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def write(self, audio_data):
        """Write audio data to the virtual microphone"""
        if not self._running:
            return

        try:
            self.audio_queue.put_nowait(audio_data)
        except queue.Full:
            # If queue is full, remove oldest data
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.put_nowait(audio_data)
            except queue.Empty:
                pass

    def __del__(self):
        self.stop() 