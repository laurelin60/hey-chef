from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv("../.env")


class ChatService:
    def __init__(self):
        self.client = OpenAI()
        self.context_history = []

        with open("./prompts.json") as f:
            self.prompts = json.load(f)

    def respond(self, message: str, image_base64: str):
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "text",
                            "text": self.prompts["DEVELOPER_PROMPT"],
                        }
                    ]
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": message},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_base64,
                            }
                        },
                    ],
                }
            ],
        )

        response = completion.choices[0].message.content
        self.context_history.append(response)


if __name__ == "__main__":
    chat = ChatService()
