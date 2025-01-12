import asyncio
from dotenv import load_dotenv
from livekit import rtc, api
import os
import logging

from livekit.rtc import RpcInvocationData

from server.chat.service import ChatService

# Load environment variables
load_dotenv()

# Set up logging

LIVEKIT_URL = os.getenv("LIVEKIT_URL")

# Generate a token with room join grants
TOKEN = api.AccessToken() \
    .with_identity("server") \
    .with_name("server") \
    .with_grants(api.VideoGrants(
    room_join=True,
    room="playground-CrNb-XQOq",
)).to_jwt()


class Room:
    def __init__(self):
        self.room = rtc.Room()
        self.chat = None
        self.chat_service = ChatService()

        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logging.info(
                "Participant connected: %s %s", participant.sid, participant.identity)

        @self.room.on('transcription_received')
        def on_transcription_received(transcription: list[rtc.TranscriptionSegment]):
            if transcription[-1].final:
                user_prompt = transcription[-1].text
                print(user_prompt)
                response = self.chat_service.user_prompt(user_prompt)

    async def connect(self):
        print('attempting to join room')

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

        await self.send_message("[SERVER] Connected")

        # @self.chat.on("message_received")
        # def on_message_received(msg: rtc.ChatMessage):
        #     print(f"message received: {msg.participant.identity}: {msg.message}")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down bot...")
            await self.room.disconnect()

    async def send_message(self, message):
        print('sending message...')
        await self.chat.send_message(message)
        print('message sent!')


if __name__ == "__main__":
    room = Room()
    asyncio.run(room.connect())
