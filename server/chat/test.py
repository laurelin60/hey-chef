import glob
import base64
import time
from colorama import init, Fore, Style
from server.chat.service import ChatService

init()  # Initialize colorama

def read_images(frames_dir):
    base64_strings = []

    for filepath in glob.glob(f"{frames_dir}/*.jpg"):
        with open(filepath, "rb") as file:
            encoded_string = base64.b64encode(file.read()).decode("utf-8")
            base64_strings.append(encoded_string)

    return base64_strings

def print_timing(duration):
    print(f"{Fore.CYAN}Time taken: {duration:.2f} seconds{Style.RESET_ALL}")

def print_section(title):
    print(f"\n{Fore.GREEN}{'='*50}")
    print(f"{title}")
    print(f"{'='*50}{Style.RESET_ALL}")

if __name__ == "__main__":
    chat = ChatService()
    images = read_images("server/_data/frames")

    print_section("Initial Context")
    start = time.perf_counter()
    chat.store_context(images[0])
    print_timing(time.perf_counter() - start)
    print(f"{Fore.YELLOW}{chat.context_string()}{Style.RESET_ALL}")

    print_section("First User Query")
    start = time.perf_counter()
    response = chat.user_prompt("I'm hungry, what can I make here?")
    print_timing(time.perf_counter() - start)
    print(f"{Fore.MAGENTA}User: I'm hungry, what can I make here?")
    print(f"{Fore.WHITE}{response}{Style.RESET_ALL}")

    print_section("Processing Additional Images")
    for i in range(1, 8, 2):
        print(f"\n{Fore.BLUE}Processing image {i}/8{Style.RESET_ALL}")
        start = time.perf_counter()
        chat.store_context(images[i])
        # print_timing(time.perf_counter() - start)
        # print(f"{Fore.YELLOW}{chat.context_string()}{Style.RESET_ALL}")

    print_section("Follow-up Query")
    start = time.perf_counter()
    response = chat.user_prompt("What's the next step?")
    print_timing(time.perf_counter() - start)
    print(f"{Fore.MAGENTA}User: What's the next step?")
    print(f"{Fore.WHITE}{response}{Style.RESET_ALL}")