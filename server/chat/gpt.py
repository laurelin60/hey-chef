from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv("../.env")

class ChatService:
    def __init__(self):
        self.client = OpenAI()

        with open("./prompts.json") as f:
            self.prompts = json.load(f)

    def respond(self, message: str, image: str):
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
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
                            }
                        },
                    ],
                }
            ],
        )

if __name__ == "__main__":
    chat = ChatService()