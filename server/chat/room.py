import asyncio
from dotenv import load_dotenv
from livekit import rtc, api
import os
import logging
import base64
from PIL import Image
import io
from server.capture_utils import ScreenCapture, AudioCapture, is_frame_black

from livekit.rtc import RpcInvocationData

from server.chat.service import ChatService

# Load environment variables
load_dotenv()

# Set up logging

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")  # Default to empty string instead of None
if not LIVEKIT_URL:
    raise ValueError("LIVEKIT_URL environment variable is not set")

# Generate a token with room join grants
TOKEN = api.AccessToken() \
    .with_identity("server") \
    .with_name("server") \
    .with_grants(api.VideoGrants(
    room_join=True,
    room="playground-0I55-bfZu"
)).to_jwt()


class Room:
    def __init__(self):
        self.room = rtc.Room()
        self.chat = None
        self.chat_service = None  # Initialize later when we have chat
        self.screen_capture = ScreenCapture()
        self._running = False
        self._frame_process_task = None

        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logging.info(
                "Participant connected: %s %s", participant.sid, participant.identity)

        @self.room.on('transcription_received')
        def on_transcription_received(transcription: list[rtc.TranscriptionSegment]):
            print(transcription)
            if transcription[-1].final and self.chat_service is not None:
                user_prompt = transcription[-1].text
                frame = self.screen_capture.get_last_frame()

                async def process_prompt():
                    if frame and not is_frame_black(frame):
                        # Convert PIL Image to base64
                        buffered = io.BytesIO()
                        frame.save(buffered, format="JPEG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        response = await self.chat_service.user_prompt(user_prompt, img_str)
                    else:
                        response = await self.chat_service.user_prompt(user_prompt)
                    await self.send_message(response)

                asyncio.create_task(process_prompt())

    async def frame_processing_loop(self):
        last_process_time = 0
        process_interval = 0.1  # Process frames pretty much as soon as they come in

        while self._running:
            current_time = asyncio.get_event_loop().time()
            if current_time - last_process_time >= process_interval and self.chat_service:
                frame = self.screen_capture.get_last_frame()
                if frame and not is_frame_black(frame):
                    # Convert PIL Image to base64
                    buffered = io.BytesIO()
                    frame.save(buffered, format="JPEG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    
                    # response = await self.chat_service.passive_prompt(img_str)
                    # if response:
                    #     await self.send_message(response)
                
                last_process_time = current_time
            
            await asyncio.sleep(0.1)  # Small sleep to prevent CPU hogging

    async def connect(self):
        print('attempting to join room')
        self._running = True

        # Connect to the LiveKit room
        await self.room.connect(LIVEKIT_URL, TOKEN)
        print("Connected to room:", self.room.name)
        await self.room.local_participant.set_name("[SERVER]")

        print(self.room.local_participant, self.room.remote_participants)

        for identity, participant in self.room.remote_participants.items():
            print(f"Identity: {identity}")
            print(f"Participant: {participant}")
            for tid, publication in participant.track_publications.items():
                print(f"\tTrack ID: {publication}")

        self.chat = rtc.ChatManager(self.room)
        self.chat_service = ChatService(send_message=self.send_message)

        await self.send_message("[SERVER] Connected")

        try:
            # Start frame processing loop
            # self._frame_process_task = asyncio.create_task(self.frame_processing_loop())
            
            # Main room loop
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down bot...")
            self._running = False
            # if self._frame_process_task:
            #     await self._frame_process_task
            await self.room.disconnect()

    async def send_message(self, message):
        if self.chat:  # Only send if chat is initialized
            print('sending message...')
            await self.chat.send_message(message)
            print('message sent!')


if __name__ == "__main__":
    room = Room()
    asyncio.run(room.connect())
