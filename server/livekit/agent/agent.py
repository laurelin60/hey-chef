from __future__ import annotations

import logging
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.multimodal import MultimodalAgent
from livekit.plugins import openai
from typing import Annotated

# https://stackoverflow.com/questions/50236117/scraping-ssl-certificate-verify-failed-error-for-http-en-wikipedia-org
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("my-worker")
logger.setLevel(logging.INFO)


# https://docs.livekit.io/agents/voice-agent/function-calling/
# first define a class that inherits from llm.FunctionContext
class AssistantFnc(llm.FunctionContext):
    # the llm.ai_callable decorator marks this function as a tool available to the LLM
    # by default, it'll use the docstring as the function's description
    @llm.ai_callable()
    async def stay_silent(
        self,
        # by using the Annotated type, arg description and type are available to the LLM
    ):
        """
        The tool to call when the audio is received but is not directly addressed to the assistant. 
        This function will return silence to the user, as intended.
        """
        logger.info(f"[TOOL USE] Staying silent.")
        
        return "[SYSTEM_INSTRUCTION] Send silence / empty string to the user"
     
async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()

    run_multimodal_agent(ctx, participant)

    logger.info("agent started")

fnc_ctx = AssistantFnc()

def run_multimodal_agent(ctx: JobContext, participant: rtc.RemoteParticipant):
    logger.info("starting multimodal agent")

    model = openai.realtime.RealtimeModel(
        instructions=(
            "You are a voice assistant created to assist users with their daily tasks. "
            "If you are not directly addressed or are told to remain silent, do not respond. "
            "In that case, call the 'stay_silent' function to produce no audio. "
            "ONLY RESPOND WITH AUDIO if directly addressed. "
            "Consider the user's prompt carefully. If it is not directed towards the assistant, i.e. could be referring to someone else, respond with the stay_silent function"
            "YOUR NAME IS 'AI'. stay_silent when comments are directed to others"
        ),
        modalities=["audio", "text"],
    )
    agent = MultimodalAgent(
        model=model,
        fnc_ctx=fnc_ctx,
    )
    agent.start(ctx.room, participant)

    session = model.sessions[0]
    # session.conversation.item.create(
    #     llm.ChatMessage(
    #         role="system",
    #         content="Do not respond unless the message begins with 'hey chef'. In that case, call stay_silent and stay silent.",
    #     )
    # )
    session.conversation.item.create(
        llm.ChatMessage(
            role="assistant",
            content="Please begin the interaction with the user in a manner consistent with your instructions. Do not respond unless addressed as 'chef'.",
        )
    )
    session.response.create(on_duplicate="cancel_existing")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
