import datetime
import json
from dataclasses import dataclass

from dotenv import load_dotenv

from openai import OpenAI

load_dotenv("../.env")


@dataclass
class Context:
    timestamp: datetime.datetime
    context: str

    def __dict__(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }


class ChatService:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model: str = model
        self.client: OpenAI = OpenAI()
        self.context_history: list[Context] = []

        with open("./prompts.json") as f:
            self.prompts = json.load(f)

    def context_string(self) -> str:
        return "\n".join([json.dumps(context.__dict__()) for context in self.context_history])

    def store_context(self, image: str) -> None:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": self.prompts["DEVELOPER_CONTEXT_PROMPT"]
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
                            }
                        },
                        {
                            "type": "text",
                            "text": self.prompts["PROVIDED_CONTEXT_PROMPT"] + self.context_string()
                        }
                    ],
                }
            ],
        )

        response = completion.choices[0].message.content
        context = Context(timestamp=datetime.datetime.now(), context=response)

        self.context_history.append(context)

    def user_prompt(self, message: str) -> str:
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
                            "type": "text",
                            "text": self.prompts["CURRENT_CONTEXT_PROMPT"] + self.context_string()
                        }
                    ],
                }
            ],
        )

        return completion.choices[0].message.content
