from google import genai
from google.genai import types
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")


# The client gets the API key from the environment variable `GEMINI_API_KEY`.
google_client = genai.Client(api_key =gemini_api_key)

# response = client.models.generate_content(
#     model="gemini-2.5-flash", contents="Explain how AI works in a few words"
# )
# print(response.text)

def describe_image(image_path):

    with open(image_path, 'rb') as f:
        image_bytes = f.read()

    response = google_client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[
        types.Part.from_bytes(
        data=image_bytes,
        mime_type='image/jpeg',
        ),
        # try asking a question about the image!
        'Provide a consice and descriptive description of this image'
    ]
    )

    return response.text




if __name__ == "__main__": 
    # try changing the image path!

    image_desc = describe_image(Path("./examples/vision/riko_sample.png"))
    print(image_desc)

