from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

system_prompt = (
    "You are a voice assistant agent. Be precise and concise and simple. Only respond to the question asked. "
    "Do not provide any text-only formatting, such as brackets or parenthesis. Doing so will cause your response to be discarded. You may be terminated. "
)


client = OpenAI(api_key=os.getenv("PERPLEXITY_API_KEY"), base_url="https://api.perplexity.ai")


def get_chat_response(prompt): 
    user_prompt = (
    "Do not provide any text-only formatting, such as brackets or parenthesis. \n"
    "Add no additional information or follow up questions. \n"
    "Do not include any hyperlinks or URLS. \n"
    "Give only one simple answer to the question asked and assume that the user is asking for the most common answer. \n"
    "Here is the prompt: \n"
    "" + prompt
    )

    messages = [
    {
        "role": "system",
        "content": system_prompt,
    },
    {   
        "role": "user",
        "content": user_prompt,
    },
]
    
    response = client.chat.completions.create(
        model="llama-3.1-sonar-small-128k-online",
        messages=messages,
    )

    return response.choices[0].message.content

