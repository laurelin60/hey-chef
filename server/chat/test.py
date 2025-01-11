import glob
import base64
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
    chat.store_context(images[0])
    print(time.perf_counter() - start)
    print(chat.context_string())

    start = time.perf_counter()
    print(chat.user_prompt("I'm hungry, what can I make here?") )
    print(time.perf_counter() - start)

    start = time.perf_counter()
    for i in range(1, 8, 2):
        chat.store_context(images[i])
        print(time.perf_counter() - start)
        print(chat.context_string())

    start = time.perf_counter()
    print(chat.user_prompt("What's the next step?"))
    print(time.perf_counter() - start)