# OpenAI tool calling with history 
### Uses a sample function
import yaml
import gradio as gr
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

with open('character_config.yaml', 'r') as f:
    char_config = yaml.safe_load(f)


client = OpenAI(api_key=openai_api_key)

# Constants
HISTORY_FILE = char_config['history_file']
MODEL = char_config['model']
SYSTEM_PROMPT =  [
        {
            "role": "system",
            "content": [
                {
                    "type": "input_text",
                    "text": char_config['presets']['default']['system_prompt']  
                }
            ]
        }
    ]

# Load/save chat history
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return SYSTEM_PROMPT

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)



def get_riko_response_no_tool(messages):

    # Call OpenAI with system prompt + history
    response = client.responses.create(
        model=MODEL,
        input= messages,
        temperature=1,
        top_p=1,
        max_output_tokens=2048,
        stream=False,
        text={
            "format": {
            "type": "text"
            }
        },
    )

    return response


def llm_response(user_input):

    messages = load_history()

    # Append user message to memory
    messages.append({
        "role": "user",
        "content": [
            {"type": "input_text", "text": user_input}
        ]
    })


    riko_test_response = get_riko_response_no_tool(messages)

    # just append assistant message to regular response. 
    messages.append({
    "role": "assistant",
    "content": [
        {"type": "output_text", "text": riko_test_response.output_text}
    ]
    })

    save_history(messages)
    return riko_test_response.output_text

# respond with Long-term memory 
def llm_response_with_memory(user_input, context_memory):

    messages = load_history()
    # modify the system prompt here with the context memory 

       # Safely modify the system prompt (assumes it's always first)
    if messages and messages[0]['role'] == 'system':
        base_content = char_config['presets']['default']['system_prompt']
        messages[0]['content'] = [
            {
                "type": "input_text",
                "text": f"{base_content}\n\nThe following memories may or may not be relevent information from past conversations. If it is not relevent to this conversation, ignore it:\n{context_memory}"
            }
        ]
    else:
        # Fallback in case system prompt is missing for some reason
        messages.insert(0, {
            "role": "system",
            "content": [
                {
                    "type": "input_text",
                    "text": f"{char_config['presets']['default']['system_prompt']}\n\n[Memory]\n{context_memory}"
                }
            ]
        })

    # Append user message to memory
    messages.append({
        "role": "user",
        "content": [
            {"type": "input_text", "text": user_input}
        ]
    })


    riko_test_response = get_riko_response_no_tool(messages)

    # just append assistant message to regular response. 
    messages.append({
    "role": "assistant",
    "content": [
        {"type": "output_text", "text": riko_test_response.output_text}
    ]
    })

    save_history(messages)
    return riko_test_response.output_text



import faiss
import os
import pickle
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Optional
from pathlib import Path



class MemoryManager:
    def __init__(self, model_name="all-MiniLM-L12-v2", faiss_path=os.path.join("faiss_cache", "memory.index"), metadata_path=os.path.join("faiss_cache", "memory_meta.pkl")):
        self.embedder = SentenceTransformer(model_name)
        self.faiss_path = faiss_path
        self.metadata_path = metadata_path
        self.dim = self.embedder.get_sentence_embedding_dimension()

        # Ensure cache dir exists
        os.makedirs(os.path.dirname(self.faiss_path), exist_ok=True)

        
        # Initialize or load FAISS index
        if os.path.exists(faiss_path) and os.path.exists(metadata_path):
            self.index = faiss.read_index(faiss_path)
            with open(metadata_path, "rb") as f:
                self.metadata = pickle.load(f)
        else:
            self.index = faiss.IndexFlatL2(self.dim)
            self.metadata = []

    def add_memory(self, text: str, metadata: Optional[dict] = None):
        vector = self.embedder.encode([text])
        self.index.add(np.array(vector).astype("float32"))
        self.metadata.append({
            "text": text,
            "metadata": metadata or {}
        })

    def query(self, text: str, top_k: int = 5) -> List[dict]:
        if self.index.ntotal == 0:
            return []
        
        query_vec = self.embedder.encode([text])
        D, I = self.index.search(np.array(query_vec).astype("float32"), top_k)
        
        results = []
        for idx in I[0]:
            if idx < len(self.metadata):
                results.append(self.metadata[idx])
        return results

    def get_context_block(self, text: str, top_k: int = 5) -> str:
        memories = self.query(text, top_k=top_k)
        if not memories:
            return ""
        lines = [f"- {m['text']}" for m in memories]
        return "Riko Memory:\n" + "\n".join(lines) + "\n"

    def save_index(self):
        faiss.write_index(self.index, self.faiss_path)
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.metadata, f)


if __name__ == "__main__":

    memory = MemoryManager()


    while True:

        print("enter your message: ")
        user_input = input()

        # grab context memory 
        #1. search for memory 

        context = memory.get_context_block(user_input)
        print(context)


        waifu_response = llm_response_with_memory(user_input, context)

        print("WAIFU RESPONSE: ", waifu_response)


