import asyncio
from dotenv import load_dotenv
from livekit import rtc, api
import os
import logging
import base64
from PIL import Image
import io
from server.chat.service import ChatService
from server.capture_utils import ScreenCapture
import time

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Disable httpx logging
logging.getLogger("httpx").setLevel(logging.WARNING)
# Disable httpcore logging
logging.getLogger("httpcore").setLevel(logging.WARNING)
# Disable OpenAI-related logging
logging.getLogger("openai").setLevel(logging.WARNING)
# Disable asyncio error logging for OpenAI rate limits
logging.getLogger("asyncio").setLevel(logging.WARNING)

LIVEKIT_URL = os.getenv("LIVEKIT_URL")

# Generate a token with room join grants
TOKEN = api.AccessToken() \
    .with_identity("server") \
    .with_name("server") \
    .with_grants(api.VideoGrants(
    room_join=True,
    room="playground-cwOH-fCXv",
)).to_jwt()

# Global variables for room and chat
room = None
chat = None
chat_service = None
screen_capture = None
startup_time = None


async def process_screen_frames():
    """Process frames from screen capture in a separate task."""
    global screen_capture
    last_process_time = 0
    min_interval = 5.0  # Minimum time between processing frames in seconds
    
    while True:
        current_time = time.time()
        if screen_capture and (current_time - last_process_time) >= min_interval:
            frame = screen_capture.get_last_frame()
            if frame:
                # Convert PIL Image to base64
                img_byte_arr = io.BytesIO()
                frame.save(img_byte_arr, format='JPEG')
                img_byte_arr = img_byte_arr.getvalue()
                frame_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
                
                # Send frame for passive prompt processing
                if chat_service:
                    response = await chat_service.passive_prompt(frame_base64)
                    if response:
                        await send_message(response)
                last_process_time = current_time
        
        await asyncio.sleep(1/30)  # Still maintain 30 FPS for frame capture


async def join_room():
    """
    Main entry point for the bot.
    Connects to the LiveKit room and handles video tracks and participants.
    """
    global room, chat, chat_service, screen_capture
    room = rtc.Room()
    chat_service = ChatService(send_message=send_message)
    
    # Initialize screen capture
    try:
        screen_capture = ScreenCapture()
        # Start the screen frame processing task
        asyncio.create_task(process_screen_frames())
    except Exception as e:
        logger.error(f"Failed to initialize screen capture: {e}")

    @room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        logging.info(
            "Participant connected: %s %s", participant.sid, participant.identity)

    async def receive_frames(stream: rtc.VideoStream):
        async for frame in stream:
            # We're not processing LiveKit frames directly anymore
            pass

    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication,
                            participant: rtc.RemoteParticipant):
        logger.info("Track subscribed: %s", publication.sid)
        if track.kind == rtc.TrackKind.KIND_VIDEO:
            video_stream = rtc.VideoStream(track)
            asyncio.ensure_future(receive_frames(video_stream))

    logger.info('attempting to join room')

    # Connect to the LiveKit room
    if LIVEKIT_URL:
        await room.connect(LIVEKIT_URL, TOKEN)
        logger.info("Connected to room: %s", room.name)
        await room.local_participant.set_name("[SERVER]")

    logger.info("Local participant: %s, Remote participants: %s", room.local_participant, room.remote_participants)

    for identity, participant in room.remote_participants.items():
        logger.info("Identity: %s", identity)
        logger.info("Participant: %s", participant)
        for tid, publication in participant.track_publications.items():
            logger.info("\tTrack ID: %s", publication)

    @room.on('transcription_received')
    def on_transcription_received(transcription: list[rtc.TranscriptionSegment]):
        if transcription[-1].final:
            text = transcription[-1].text
            # lk is so cringe
            if text.startswith("["):
                return

            logger.info("Processing transcription: %s", text)
            # Create task for async processing
            asyncio.create_task(process_transcription(text))

    # Handle already available participants and tracks
    chat = rtc.ChatManager(room)

    # await send_message("[SERVER] Connected")

    @chat.on("message_received")
    def on_message_received(msg: rtc.ChatMessage):
        if msg.participant and msg.participant.identity:
            logger.info("message received: %s: %s", msg.participant.identity, msg.message)

    # Keep the script running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down bot...")
        if screen_capture:
            screen_capture.stop()
        await room.disconnect()


async def send_message(text: str):
    global startup_time
    if chat:
        # Block messages for 6 seconds after startup
        if startup_time:
            current_time = time.time()
            time_since_startup = current_time - startup_time
            if time_since_startup < 1.0:
                # Queue the message to be sent after the delay
                remaining_delay = 1.0 - time_since_startup
                await asyncio.sleep(remaining_delay)

        logger.info('sending message...')

        if not text.startswith("["):
            text = f"[SERVER_MESSAGE] {text}"

        await chat.send_message(text)
        logger.info('message sent!')


async def process_transcription(text: str):
    """Process transcription text asynchronously."""
    print(f"Got transcription: \"{text}\"")
    if chat_service:
        response = await chat_service.user_prompt(text)
        if response:
            print(f"Sending response: \"{response}\"")
            await send_message(response)


if __name__ == "__main__":
    try:
        startup_time = time.time()  # Record startup time
        asyncio.run(join_room())
    except KeyboardInterrupt:
        logger.info("Shutting down due to keyboard interrupt...")
    except Exception as e:
        logger.error("Error in main loop: %s", e)
    finally:
        # Ensure screen capture is stopped
        if screen_capture:
            screen_capture.stop()