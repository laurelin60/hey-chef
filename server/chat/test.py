import glob
import base64
import json
import time

from server.chat.service import ChatService

def read_images(frames_dir):
    base64_strings = []

    for filepath in glob.glob(f"{frames_dir}/*.jpg"):
        with open(filepath, "rb") as file:
            encoded_string = base64.b64encode(file.read()).decode("utf-8")
            base64_strings.append(encoded_string)

    return base64_strings

if __name__ == "__main__":
    chat = ChatService()

    images = read_images("../_data/frames")

    start = time.perf_counter()

    for i in range(0, 21, 5):
        print(i)
        chat.store_context(images[i])

    print(f"Time taken: {time.perf_counter() - start:.2f}s")

    print(chat.context_string())

    res = chat.user_prompt("What can I make with the ingredients here?")
    print(res)
