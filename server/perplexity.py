from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

system_prompt = (
    "You are an assistant agent called upon when someone needs to search the web for additional information. \n"
    "Provide as much information as possible with as little fluff as possible. Cut the BS and get to the point. \n")


client = OpenAI(api_key=os.getenv("PERPLEXITY_API_KEY"), base_url="https://api.perplexity.ai")


def get_chat_response(prompt): 
    user_prompt = (
    "Add no additional information or follow up questions. \n"
    "Simply provide information you have found online so it can be processed. \n"
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

