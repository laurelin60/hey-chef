import asyncio
from dotenv import load_dotenv
from livekit import rtc, api
import os
import logging

from livekit.rtc import RpcInvocationData

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
    room="playground-q2wz-olQz",
)).to_jwt()

# Global variables for room and chat
room = None
chat = None


async def join_room():
    """
    Main entry point for the bot.
    Connects to the LiveKit room and handles video tracks and participants.
    """
    global room, chat  # Use global variables to allow access in other scripts
    room = rtc.Room()

    @room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        logging.info(
            "Participant connected: %s %s", participant.sid, participant.identity)

    async def receive_frames(stream: rtc.VideoStream):
        async for frame in stream:
            # Process received video frames here
            pass

    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication,
                            participant: rtc.RemoteParticipant):
        print("Track subscribed: %s", publication.sid)
        if track.kind == rtc.TrackKind.KIND_VIDEO:
            video_stream = rtc.VideoStream(track)
            asyncio.ensure_future(receive_frames(video_stream))

    print('attempting to join room')

    # Connect to the LiveKit room
    await room.connect(LIVEKIT_URL, TOKEN)
    print("Connected to room:", room.name)
    await room.local_participant.set_name("[SERVER]")

    print(room.local_participant, room.remote_participants)

    for identity, participant in room.remote_participants.items():
        print(f"Identity: {identity}")
        print(f"Participant: {participant}")
        for tid, publication in participant.track_publications.items():
            print(f"\tTrack ID: {publication}")

    @room.on('transcription_received')
    def on_transcription_received(transcription: list[rtc.TranscriptionSegment]):
        if transcription[-1].final:
            print(transcription[-1].text)

    # Handle already available participants and tracks
    chat = rtc.ChatManager(room)

    await send_message(chat, "[SERVER] Connected")

    @chat.on("message_received")
    def on_message_received(msg: rtc.ChatMessage):
        print(f"message received: {msg.participant.identity}: {msg.message}")

    # Keep the script running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down bot...")
        await room.disconnect()


async def send_message(chat: rtc.ChatManager, text: str):
    print('sending message...')
    await chat.send_message(text)
    print('message sent!')


if __name__ == "__main__":
    room, chat = asyncio.run(join_room())