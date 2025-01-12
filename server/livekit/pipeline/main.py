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

load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("my-worker")
logger.setLevel(logging.INFO)

# We'll keep an 'agent' reference at the module level so it can be called later
agent: Optional[VoicePipelineAgent] = None
#
# async def _forward_transcription(
#     stt_stream: stt.SpeechStream,
#     stt_forwarder: transcription.STTSegmentsForwarder,
# ):
#     """Forward the transcription and log the transcript in the console"""
#     async for ev in stt_stream:
#         stt_forwarder.update(ev)
#         if ev.type == stt.SpeechEventType.INTERIM_TRANSCRIPT:
#             print(ev.alternatives[0].text, end="")
#         elif ev.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
#             print("\n")
#             print(" -> ", ev.alternatives[0].text)

async def entrypoint(ctx: JobContext):
    """
    This is your LiveKit job entrypoint. It sets up the VoicePipelineAgent, 
    connects to the room, and remains in the background. We'll store a reference
    to the agent in a global variable so we can access it in our FastAPI routes.
    """
    global agent

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

    # async def transcribe_track(participant: rtc.RemoteParticipant, track: rtc.Track):
    #     audio_stream = rtc.AudioStream(track)
    #     stt_forwarder = transcription.STTSegmentsForwarder(
    #         room=ctx.room, participant=participant, track=track
    #     )
    #     stt_stream = stt.stream()
    #     stt_task = asyncio.create_task(
    #         _forward_transcription(stt_stream, stt_forwarder)
    #     )
    #     tasks.append(stt_task)
    #
    #     async for ev in audio_stream:
    #         stt_stream.push_frame(ev.frame)

    # @ctx.room.on("track_subscribed")
    # def on_track_subscribed(
    #         track: rtc.Track,
    #         publication: rtc.TrackPublication,
    #         participant: rtc.RemoteParticipant,
    # ):
    #     if track.kind == rtc.TrackKind.KIND_AUDIO:
    #         tasks.append(asyncio.create_task(transcribe_track(participant, track)))

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
