import asyncio
from datetime import datetime
import json
from typing import Optional

import logging
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm, stt, transcription
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.agents.stt import STT
from livekit.plugins import deepgram, openai, silero

load_dotenv()
logger = logging.getLogger("my-worker")
logger.setLevel(logging.INFO)

# We'll keep an 'agent' reference at the module level so it can be called later
agent: Optional[VoicePipelineAgent] = None
#
async def _forward_transcription(
    stt_stream: stt.SpeechStream,
    stt_forwarder: transcription.STTSegmentsForwarder,
    room: rtc.Room
):
    """Forward the transcription and log the transcript in the console"""
    logger.info("Starting transcription forwarding")
    async for ev in stt_stream:
        logger.info(f"Got STT event type: {ev.type}")
        stt_forwarder.update(ev)
        timestamp = int(datetime.now().timestamp() * 1000)  # Convert to milliseconds
        if ev.type == stt.SpeechEventType.INTERIM_TRANSCRIPT:
            print(ev.alternatives[0].text, end="")
            segment = rtc.TranscriptionSegment(
                id=str(timestamp),
                text=ev.alternatives[0].text,
                start_time=timestamp,
                end_time=timestamp,
                language="en",
                final=False
            )
            # Send transcription through data channel
            logger.info(f"Publishing interim transcription: {segment.text}")
            await room.local_participant.publish_data(
                json.dumps([segment.__dict__]).encode(),
                topic="transcription"
            )
        elif ev.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
            print("\n")
            print(" -> ", ev.alternatives[0].text)
            segment = rtc.TranscriptionSegment(
                id=str(timestamp),
                text=ev.alternatives[0].text,
                start_time=timestamp,
                end_time=timestamp,
                language="en",
                final=True
            )
            # Send transcription through data channel
            logger.info(f"Publishing final transcription: {segment.text}")
            await room.local_participant.publish_data(
                json.dumps([segment.__dict__]).encode(),
                topic="transcription"
            )

async def entrypoint(ctx: JobContext):
    """
    This is your LiveKit job entrypoint. It sets up the VoicePipelineAgent, 
    connects to the room, and remains in the background. We'll store a reference
    to the agent in a global variable so we can access it in our FastAPI routes.
    """
    global agent
    tasks = []  # Define tasks list to track async operations

    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are a voice assistant created by LiveKit. Your interface with users will be voice. "
            "You should use short and concise responses, and avoid unpronounceable punctuation."
        ),
    )

    logger.info(f"Connecting to room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    agent = VoicePipelineAgent(
        vad=silero.VAD.load(),
        stt=deepgram.STT(),
        llm=openai.LLM(),
        tts=openai.TTS(),
        chat_ctx=initial_ctx,
    )
    agent.start(ctx.room)

    async def transcribe_track(participant: rtc.RemoteParticipant, track: rtc.Track):
        if not agent:
            logger.error("Agent not initialized")
            return
            
        logger.info(f"Starting to transcribe track from participant {participant.identity}")
        audio_stream = rtc.AudioStream(track)
        stt_forwarder = transcription.STTSegmentsForwarder(
            room=ctx.room, participant=participant, track=track
        )
        stt_stream = agent.stt.stream()  # Use the STT instance from the agent
        stt_task = asyncio.create_task(
            _forward_transcription(stt_stream, stt_forwarder, ctx.room)
        )
        tasks.append(stt_task)

        logger.info("Starting audio stream processing")
        frame_count = 0
        async for ev in audio_stream:
            frame_count += 1
            if frame_count % 100 == 0:  # Log every 100 frames to avoid spam
                logger.info(f"Processed {frame_count} audio frames")
            stt_stream.push_frame(ev.frame)

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.TrackPublication,
            participant: rtc.RemoteParticipant,
    ):
        logger.info(f"Track subscribed: {track.kind} from {participant.identity}")
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info("Starting audio track transcription")
            tasks.append(asyncio.create_task(transcribe_track(participant, track)))

    # Subscribe to chat events in the room
    @ctx.room.on("data_received")
    def handle_chat_message(data_packet):
        """Handles data received."""
        
        logger.info('data received')
        logger.info(data_packet)
        
        data_bytes = data_packet.data  # Direct attribute access
        data_str = data_bytes.decode('utf-8')  # Decode the binary data
        data_dict = json.loads(data_str)  # Parse the JSON string

        message = data_dict.get("message", "No message found")
        
        if message[0] == "[":
            return
        
        if agent:
            # Assuming the data packet contains text data
            asyncio.create_task(agent.say(f"{message}", allow_interruptions=True))

    # Optionally greet the room
    await agent.say("Hello! I’m ready to help.", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
