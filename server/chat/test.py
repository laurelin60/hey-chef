import glob
import base64
import time
import cv2
import numpy as np
from colorama import init, Fore, Style
from server.chat.service import ChatService

init()  # Initialize colorama

def show_image(base64_string, window_name="Current Frame"):
    # Decode base64 string to image
    img_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Resize image to a reasonable size if too large
    max_height = 600
    if img.shape[0] > max_height:
        scale = max_height / img.shape[0]
        width = int(img.shape[1] * scale)
        img = cv2.resize(img, (width, max_height))
    
    # Show image in non-blocking way
    cv2.imshow(window_name, img)
    cv2.waitKey(1)  # Wait 1ms - allows window to update without blocking

def read_images(frames_dir):
    base64_strings = []
    for filepath in sorted(glob.glob(f"{frames_dir}/*.jpg")):
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
    images = read_images("/home/awang/PycharmProjects/hey-chef/server/_data/frames")

    print_section("First User Query")
    start = time.perf_counter()
    show_image(images[10], "Current Frame")  # Show initial image
    response = chat.user_prompt("I'm hungry, what can I make here?", images[4])
    print_timing(time.perf_counter() - start)
    print(f"{Fore.MAGENTA}User: I'm hungry, what can I make here?")
    print(f"{Fore.WHITE}{response}{Style.RESET_ALL}")

    print_section("Processing Additional Images")
    for i in range(5, 46):
        print(f"\n{Fore.BLUE}Processing image {i + 1}{Style.RESET_ALL}")
        start = time.perf_counter()
        show_image(images[i], "Current Frame")  # Show each image as it's processed
        response = chat.passive_prompt(images[i])
        if response is not None:
            print(f"{Fore.WHITE}{response}{Style.RESET_ALL}")
        print_timing(time.perf_counter() - start)

    print_section("Follow-up Query")
    start = time.perf_counter()
    show_image(images[46], "Current Frame")  # Show final image
    response = chat.user_prompt("Ok now what", images[46])
    print_timing(time.perf_counter() - start)
    print(f"{Fore.MAGENTA}User: Ok now what")
    print(f"{Fore.WHITE}{response}{Style.RESET_ALL}")

    # Clean up at the end
    cv2.destroyAllWindows()