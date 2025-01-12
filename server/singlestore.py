import singlestoredb as s2
import os
from dotenv import load_dotenv
import requests
import json

import numpy as np
from PIL import Image
from torchvision import models, transforms
import pickle
import torch

# Create a connection to the database

load_dotenv()

conn = None

def get_db_connection():
    global conn
    if conn is None:
      conn = s2.connect(os.getenv("SINGLESTORE_STUFF") + ":" + os.getenv("SINGLESTORE_PORT") + "/" + os.getenv("SINGLESTORE_DB"))
    return conn


def fetch_data_from_table(table_name):
    conn = get_db_connection()
    with conn.cursor() as cur:
        if cur.is_connected():
            print(f"fetching data from {table_name}")
            cur.execute(f"SELECT * FROM {table_name}")
            rows = cur.fetchall()
            return rows


def fetch_context_from_call_session(call_session_id):
    conn = get_db_connection()
    with conn.cursor() as cur:
        if cur.is_connected():
            print(f"fetching data from CallSessionContexts")
            cur.execute(f"SELECT * FROM CallSessionContexts WHERE CallSessionContexts.callId = {call_session_id}")
            rows = cur.fetchall()
            return rows


def vectorize_and_insert_image(PILimage):
    # Load a pre-trained model for vectorization
    
    model = models.resnet50(pretrained=True)
    model.eval()

    # Preprocess the image
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    input_tensor = transform(PILimage).unsqueeze(0)

    # Generate vector
    with torch.no_grad():
        vector = model(input_tensor).numpy().flatten()

    binary_vector = vector.tobytes()


    # Convert the binary data back to a NumPy array
    # vector = np.frombuffer(binary_vector, dtype=np.float32)
    # print(vector)
    conn = get_db_connection()
    with conn.cursor() as cur:
        if cur.is_connected():
            print(f"inserting image")
            sql = "INSERT INTO CallSessionImages (callId, vector) VALUES (%s, %s)"
            cur.execute(sql, (1, binary_vector))
            conn.commit()

def insert_new_call_session():
    conn = get_db_connection()
    with conn.cursor() as cur:
        if cur.is_connected():
            print(f"inserting new call session")
            cur.execute("INSERT INTO CallSessions (id, startDate) VALUES (DEFAULT, DEFAULT)")
            conn.commit()

def insert_new_call_session_context(callId, context):
    conn = get_db_connection()
    with conn.cursor() as cur:
        if cur.is_connected():
            print(f"inserting new call session context")
            cur.execute("INSERT INTO CallSessionContexts (contextData, callId) VALUES (%s, %s)", (context, callId))
            conn.commit()
