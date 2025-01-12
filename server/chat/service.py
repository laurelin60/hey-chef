import datetime
import json
from dataclasses import dataclass
from pydantic import BaseModel

import yaml
from dotenv import load_dotenv

from openai import OpenAI

load_dotenv()


@dataclass
class Context:
    timestamp: datetime.datetime
    context: str

    def __dict__(self):
        seconds_ago = round((datetime.datetime.now() - self.timestamp).total_seconds())

        return {
            "timestamp": f"{seconds_ago} seconds ago",
            "context": self.context
        }


class ChatService:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model: str = model
        self.client: OpenAI = OpenAI()
        self.context_history: list[Context] = []

        with open("server/chat/prompts.yml", 'r') as file:
            self.prompts = yaml.safe_load(file)

    def context_string(self) -> str:
        return "\n".join([json.dumps(context.__dict__()) for context in self.context_history])

    def user_prompt(self, message: str, image: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": self.prompts["DEVELOPER_USER_PROMPT"]
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpg;base64,{image}",
                                "detail": "low"
                            },
                        },
                        {
                            "type": "text",
                            "text": self.prompts["CURRENT_CONTEXT_PROMPT"] + self.context_string()
                        },
                    ],
                }
            ],
        )

        prompt_context = Context(timestamp=datetime.datetime.now(), context="USER PROMPTED: " + message)
        self.context_history.append(prompt_context)

        response = completion.choices[0].message.content
        context = Context(timestamp=datetime.datetime.now(), context="DIRECT RESPONSE TO USER:" + response)
        self.context_history.append(context)

        return response

    def passive_prompt(self, image: str) -> str | None:
        class PassiveResponse(BaseModel):
            img: str
            passive_user_message: str


        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": self.prompts["PASSIVE_ACTION_PROMPT"]
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpg;base64,{image}",
                                "detail": "low"
                            },
                        },
                        {
                            "type": "text",
                            "text": self.prompts["CURRENT_CONTEXT_PROMPT"] + self.context_string()
                        },
                    ],
                }
            ],
            response_format=PassiveResponse
        )

        response_data: PassiveResponse | None = completion.choices[0].message.parsed

        if response_data is None:
            return None
        
        print(response_data)

        if response_data.img:
            img_context = Context(timestamp=datetime.datetime.now(), context="IMAGE CONTEXT: " + response_data.img)
            self.context_history.append(img_context)

        if response_data.passive_user_message.lower() == "n/a":
            return None

        prompt_context = Context(timestamp=datetime.datetime.now(), context="PASSIVE MESSAGE TO USER: " + response_data.passive_user_message)
        self.context_history.append(prompt_context)

        return response_data.passive_user_message