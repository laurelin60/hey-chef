import json
from typing import List, Dict, Any, Optional, cast, Callable
import yaml
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionSystemMessageParam, \
    ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam
from pydantic import BaseModel
import os

load_dotenv()


class PassiveResponse(BaseModel):
    passive_user_message: Optional[str] = None


class ChatService:
    MAX_IMAGES = 3  # Maximum number of images to keep in context

    def __init__(self, model: str = "gpt-4o-mini", send_message: Callable | None = None):
        self.model: str = model
        self.client: AsyncOpenAI = AsyncOpenAI()
        self.messages: List[ChatCompletionMessageParam] = []
        self.image_message_indices: List[int] = []  # Keep track of messages containing images
        self.send_message = send_message

        prompts_path = os.path.join(os.path.dirname(__file__), "prompts.yml")
        with open(prompts_path, "r") as file:
            self.prompts = yaml.safe_load(file)

        # Initialize with master system prompt
        system_message: Dict[str, Any] = {
            "role": "system",
            "content": self.prompts["MASTER_SYSTEM_PROMPT"]
        }
        self.messages.append(cast(ChatCompletionSystemMessageParam, system_message))

    def _manage_image_context(self, new_image_idx: int) -> None:
        """Maintain a sliding window of recent images, replacing older ones with markers."""
        self.image_message_indices.append(new_image_idx)

        # If we have more images than allowed, replace the oldest ones
        while len(self.image_message_indices) > self.MAX_IMAGES:
            oldest_idx = self.image_message_indices.pop(0)
            self._replace_image_with_marker(oldest_idx)

    def _replace_image_with_marker(self, message_idx: int) -> None:
        """Replace image content with a marker to save context space."""
        if message_idx >= len(self.messages):
            return

        message = self.messages[message_idx]
        if not isinstance(message, dict) or "content" not in message:
            return

        content = message["content"]
        if isinstance(content, list):
            new_content = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "image_url":
                    new_content.append({
                        "type": "text",
                        "text": "[Previous image content removed to save context]"
                    })
                else:
                    new_content.append(item)
            # Cast the message to allow content modification
            message_dict = cast(Dict[str, Any], message)
            message_dict["content"] = new_content

    async def user_prompt(self, message: str, image: Optional[str] = None) -> str:
        # Add user instructions for direct questions
        system_message: Dict[str, Any] = {
            "role": "system",
            "content": self.prompts["USER_PROMPT"]
        }
        self.messages.append(cast(ChatCompletionSystemMessageParam, system_message))

        # Add user message with image
        if image:
            content: List[Dict[str, Any]] = [
                {
                    "type": "text",
                    "text": message
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpg;base64,{image}",
                        "detail": "low"
                    }
                }
            ]
        else:
            content = [{
                "type": "text",
                "text": message
            }]

        user_message: Dict[str, Any] = {
            "role": "user",
            "content": content
        }
        message_idx = len(self.messages)
        self.messages.append(cast(ChatCompletionUserMessageParam, user_message))
        self._manage_image_context(message_idx)

        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages
        )

        response = completion.choices[0].message.content
        if response is None:
            response = "I apologize, but I couldn't generate a response at this time."

        # Add assistant's response
        assistant_message: Dict[str, Any] = {
            "role": "assistant",
            "content": response
        }
        self.messages.append(cast(ChatCompletionAssistantMessageParam, assistant_message))

        return response

    async def passive_prompt(self, image: Optional[str] = None) -> Optional[str]:
        # Add system instructions for passive observation
        system_message: Dict[str, Any] = {
            "role": "system",
            "content": self.prompts["PASSIVE_PROMPT"]
        }
        self.messages.append(cast(ChatCompletionSystemMessageParam, system_message))

        # Add user message with new image
        if image:
            content: List[Dict[str, Any]] = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpg;base64,{image}",
                        "detail": "low"
                    }
                }
            ]
        else:
            content = []  # Empty content for passive prompt without image

        user_message: Dict[str, Any] = {
            "role": "user",
            "content": content
        }
        message_idx = len(self.messages)
        self.messages.append(cast(ChatCompletionUserMessageParam, user_message))
        self._manage_image_context(message_idx)

        completion = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=self.messages,
            response_format=PassiveResponse
        )

        response_data = completion.choices[0].message.parsed
        if not isinstance(response_data, PassiveResponse) or response_data.passive_user_message is None:
            return None

        if response_data.passive_user_message.lower() != "n/a":
            assistant_message: Dict[str, Any] = {
                "role": "assistant",
                "content": response_data.passive_user_message
            }
            self.messages.append(cast(ChatCompletionAssistantMessageParam, assistant_message))

            if self.send_message and response_data.passive_user_message:
                await self.send_message(response_data.passive_user_message)

            return response_data.passive_user_message

        return None
