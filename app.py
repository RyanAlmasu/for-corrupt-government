import streamlit as st
import requests
import threading
import time
import hashlib
import uuid
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr
from starlette.middleware.wsgi import WSGIMiddleware
import uvicorn

# ========== BACKEND (FastAPI) ==========
api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Bisa dibatasi ke domain tertentu
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

messages_data = []  # Simpan daftar pesan
user_reactions = defaultdict(dict)  # Mencegah KeyError jika session kosong
last_message = {}  # Simpan timestamp pesan terakhir per user

MESSAGE_COOLDOWN = 30  # Cooldown per user (detik)

class Message(BaseModel):
    username: constr(strip_whitespace=True, min_length=1, max_length=50) # type: ignore
    message: constr(strip_whitespace=True, min_length=1, max_length=500) # type: ignore

class Reaction(BaseModel):
    emoji: str

def hash_username(username: str) -> str:
    return hashlib.sha256(username.encode()).hexdigest()

@api.post("/messages")
async def add_message(msg: Message, request: Request):
    hashed_username = hash_username(msg.username)  

    if hashed_username in last_message:
        last_time = last_message[hashed_username]
        elapsed_time = time.time() - last_time
        if elapsed_time < MESSAGE_COOLDOWN:
            raise HTTPException(
                status_code=429, 
                detail=f"Tunggu {int(MESSAGE_COOLDOWN - elapsed_time)} detik sebelum mengirim pesan lagi."
            )

    new_message = {
        "id": uuid.uuid4().hex,
        "username": hashed_username[:10],  
        "message": msg.message,
        "reactions": {"👍": 0, "😂": 0, "😡": 0, "😍": 0, "😱": 0},
        "timestamp": time.time()
    }
    messages_data.append(new_message)
    last_message[hashed_username] = time.time()

    return JSONResponse(content={"status": "success", "message": "Pesan berhasil dikirim", "data": new_message})

@api.post("/react/{message_id}")
async def react_message(message_id: str, reaction: Reaction, request: Request):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID diperlukan untuk memberi reaksi")

    for msg in messages_data:
        if msg["id"] == message_id:
            if message_id not in user_reactions:
                user_reactions[message_id] = {}

            # Jika user sudah pernah react sebelumnya
            if session_id in user_reactions[message_id]:
                old_reaction = user_reactions[message_id][session_id]
                
                if old_reaction == reaction.emoji:
                    msg["reactions"][old_reaction] -= 1  # Hapus reaksi jika sama
                    del user_reactions[message_id][session_id]
                    return JSONResponse(content={"message": "Reaction dihapus", "reactions": msg["reactions"]})

                # Ganti reaction lama dengan yang baru
                msg["reactions"][old_reaction] -= 1  

            # Tambahkan reaction baru
            user_reactions[message_id][session_id] = reaction.emoji
            msg["reactions"][reaction.emoji] += 1  

            return JSONResponse(content={"message": "Reaction berhasil diberikan atau diganti", "reactions": msg["reactions"]})

    raise HTTPException(status_code=404, detail="Pesan tidak ditemukan")


@api.get("/messages")
async def get_messages():
    return messages_data

@api.get("/leaderboard")
def get_leaderboard():
    filtered_messages = [msg for msg in messages_data if sum(msg["reactions"].values()) > 0]
    sorted_messages = sorted(filtered_messages, key=lambda x: sum(x["reactions"].values()), reverse=True)
    return JSONResponse(content=sorted_messages[:5], status_code=200)

# ========== BACKEND (Threading) ==========
def run_api():
    uvicorn.run(api, host="127.0.0.1", port=8000)

# Jalankan backend di thread terpisah
thread = threading.Thread(target=run_api, daemon=True)
thread.start()

# ========== FRONTEND (Streamlit) ==========
BACKEND_URL = "http://127.0.0.1:8000"

st.title("💬 Lontarkan kata-kata anda buat pemerintah Indo! (Anonim)")

def apply_styles():
    st.markdown("""
        <style>
        .message-box {
            border: 2px solid #ddd;
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 10px;
            background-color: #f9f9f9;
            color: black;
        }
        </style>
    """, unsafe_allow_html=True)

apply_styles()

if "reacted_messages" not in st.session_state:
    st.session_state.reacted_messages = {}

def fetch_messages():
    try:
        response = requests.get(f"{BACKEND_URL}/messages")
        return response.json() if response.status_code == 200 else []
    except requests.exceptions.RequestException:
        st.error("Gagal mengambil data dari server.")
        return []

# Generate session ID unik jika belum ada
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

def send_reaction(msg_id, emoji):
    try:
        reaction_response = requests.post(
            f"{BACKEND_URL}/react/{msg_id}",
            json={"emoji": emoji},
            headers={"X-Session-ID": st.session_state.session_id}  # Kirim session ID
        )

        if reaction_response.status_code == 200:
            response_data = reaction_response.json()
            
            if response_data["message"] == "Reaction dihapus":
                if msg_id in st.session_state.reacted_messages:
                    del st.session_state.reacted_messages[msg_id]
            else:
                st.session_state.reacted_messages[msg_id] = emoji  

            st.rerun()
        else:
            st.warning("❌ Gagal memberikan reaksi.")
    except requests.exceptions.RequestException:
        st.error("Gagal menghubungi server.")

def send_message(username, message):
    if not username or not message:
        st.warning("⚠️ Harap isi username dan pesan!")
        return

    try:
        response = requests.post(f"{BACKEND_URL}/messages", json={"username": username, "message": message})

        if response.status_code == 200:
            st.success("✅ Pesan berhasil dikirim!")
            st.rerun()
        else:
            st.warning("❌ Gagal mengirim pesan.")
    except requests.exceptions.RequestException:
        st.error("Gagal menghubungi server.")

def fetch_leaderboard():
    response = requests.get(f"{BACKEND_URL}/leaderboard")
    return response.json() if response.status_code == 200 else []

with st.expander("📩 Kirim Pesan"):
    username = st.text_input("Username (Anonim)")
    message = st.text_area("Pesan Anda")

    if st.button("Kirim Pesan"):
        send_message(username, message)

with st.expander("📢 Pesan dari Pengguna"):
    messages = fetch_messages()
    for msg in messages:
        msg_id = msg["id"]
        reactions = msg["reactions"]

        st.markdown(f"""
            <div class="message-box">
                <b>📝 {msg['username']}</b>: {msg['message']}<br>
                👍 {reactions['👍']} 😂 {reactions['😂']} 😡 {reactions['😡']} 😍 {reactions['😍']} 😱 {reactions['😱']}
            </div>
        """, unsafe_allow_html=True)

        cols = st.columns(5)
        for i, emoji in enumerate(["👍", "😂", "😡", "😍", "😱"]):
            with cols[i]:
                if st.button(emoji, key=f"{emoji}_{msg_id}"):
                    send_reaction(msg_id, emoji)

leaderboard = fetch_leaderboard()

if leaderboard:
    with st.expander("🏆 Leaderboard (Top 5 Reactions)"):
        for rank, msg in enumerate(leaderboard, start=1):
            st.markdown(f"🥇 {rank}. {msg['username']}: {msg['message']}")  
