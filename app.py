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
import uvicorn
import os
from fastapi.staticfiles import StaticFiles
import base64
import numpy as np
import soundfile as sf
from io import BytesIO
import streamlit.components.v1 as components
import base64

# Deklarasi komponen
abs_path = os.path.abspath("./frontend/dist")
audio_recorder = components.declare_component(
    "audio_recorder",
    path=abs_path
)
# ========== BACKEND (FastAPI) ==========
api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

messages_data = []
user_reactions = defaultdict(dict)
last_message = {}

MESSAGE_COOLDOWN = 30

# Model Pydantic
class Reply(BaseModel):
    username: constr(strip_whitespace=True, min_length=1, max_length=50) # type: ignore
    reply_message: constr(strip_whitespace=True, min_length=1, max_length=500) # type: ignore

class Message(BaseModel):
    username: constr(strip_whitespace=True, min_length=1, max_length=50) # type: ignore
    message: constr(strip_whitespace=True, min_length=1, max_length=500) # type: ignore

class Reaction(BaseModel):
    emoji: str
    
class AudioMessage(BaseModel):
    username: constr(strip_whitespace=True, min_length=1, max_length=50)  # type: ignore
    audio_file: str

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
        "replies": [],  # <-- Tambahkan ini untuk menyimpan reply
        "timestamp": time.time()
    }
    messages_data.append(new_message)
    last_message[hashed_username] = time.time()

    return JSONResponse(content={"status": "success", "message": "Pesan berhasil dikirim", "data": new_message})

@api.post("/react/{message_id}")
async def react_message(message_id: str, reaction: Reaction):
    for msg in messages_data:
        if msg["id"] == message_id:
            # Tambahkan reaksi tanpa batas, tidak peduli apakah sudah ada sebelumnya
            msg["reactions"][reaction.emoji] += 1
            return JSONResponse(
                content={
                    "message": "Reaction berhasil ditambahkan",
                    "reactions": msg["reactions"]
                }
            )
    
    raise HTTPException(status_code=404, detail="Pesan tidak ditemukan")

@api.get("/messages")
async def get_messages():
    return messages_data

@api.post("/reply/{message_id}")
async def add_reply(message_id: str, reply: Reply):
    for msg in messages_data:
        if msg["id"] == message_id:
            hashed_username = hash_username(reply.username)
            new_reply = {
                "id": uuid.uuid4().hex,
                "username": hashed_username[:10],
                "reply": reply.reply_message,
                "timestamp": time.time()
            }
            msg["replies"].append(new_reply)
            return JSONResponse(content={"status": "success", "reply": new_reply})
    
    raise HTTPException(status_code=404, detail="Pesan tidak ditemukan")

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
# Initializations
BACKEND_URL = "http://127.0.0.1:8000"

# Custom CSS untuk tampilan yang lebih baik
def apply_styles():
    st.markdown("""
        <style>
        .main {
            max-width: 800px;
            padding: 2rem;
        }
        .message-box {
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            background-color: #ffffff;
            color: black;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        }
        .record-button {
            background-color: #4CAF50 !important;
            color: white !important;
            padding: 0.8rem 1.5rem;
            border-radius: 25px;
            border: none;
            margin: 0.5rem;
        }
        .stop-button {
            background-color: #f44336 !important;
            color: white !important;
            padding: 0.8rem 1.5rem;
            border-radius: 25px;
            border: none;
            margin: 0.5rem;
        }
        .audio-preview {
            margin: 1rem 0;
        }
        .username-input {
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

apply_styles()

                    



                    
if "reacted_messages" not in st.session_state:
    st.session_state.reacted_messages = {}
    


def send_reaction(msg_id, emoji):
    try:
        # Kirim request POST setiap kali tombol diklik
        reaction_response = requests.post(
            f"{BACKEND_URL}/react/{msg_id}", 
            json={"emoji": emoji}
        )
        if reaction_response.status_code == 200:
            st.rerun()  # Refresh untuk update reaksi terbaru
        else:
            st.warning("❌ Tunggu dulu 30 detik, jangan spam.")
    except requests.exceptions.RequestException:
        st.error("Gagal menghubungi server.")

def fetch_messages():
    try:
        response = requests.get(f"{BACKEND_URL}/messages")
        return response.json() if response.status_code == 200 else []
    except requests.exceptions.RequestException:
        st.error("Gagal mengambil data dari server.")
        return []

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
            st.warning("❌ Tunggu dulu 30 detik, jangan spam.")
    except requests.exceptions.RequestException:
        st.error("Gagal menghubungi server.")

def send_reply(message_id, username, reply):
    if not username or not reply:
        st.warning("⚠️ Harap isi username dan balasan!")
        return

    try:
        response = requests.post(
            f"{BACKEND_URL}/reply/{message_id}",
            json={"username": username, "reply_message": reply}
        )
        if response.status_code == 200:
            st.success("✅ Balasan berhasil dikirim!")
            st.rerun()
        else:
            st.warning("❌ Gagal mengirim balasan.")
    except requests.exceptions.RequestException:
        st.error("Gagal menghubungi server.")

def fetch_leaderboard():
    response = requests.get(f"{BACKEND_URL}/leaderboard")
    return response.json() if response.status_code == 200 else []


# Tampilkan komponen rekam audio
st.title("💬 Suara Untuk Negeri")
st.write("Sampaikan pendapat Anda kepada pemerintah secara anonim")

st.title("🎤 Audio Recorder")

# Gunakan komponen
audio_data = audio_recorder()

# Proses data audio
if audio_data and isinstance(audio_data, str) and audio_data not in ["", "ERROR: Microphone access denied"]:
    try:
        # Decode base64 ke bytes
        audio_bytes = base64.b64decode(audio_data)
        
        # Tampilkan audio
        st.audio(audio_bytes, format="audio/wav")
        st.success("🎉 Audio berhasil direkam!")
        
        # Simpan ke file (opsional)
        with open("recorded_audio.wav", "wb") as f:
            f.write(audio_bytes)
        st.info("💾 Audio disimpan sebagai 'recorded_audio.wav'")
        
    except Exception as e:
        st.error(f"Gagal memproses audio: {str(e)}")
elif audio_data == "ERROR: Microphone access denied":
    st.error("❌ Akses mikrofon ditolak. Silakan izinkan akses mikrofon.")
else:
    st.info("🔈 Tekan tombol 'Mulai Rekam' untuk merekam audio.")







with st.expander("📩 Kirim Pesan"):
    username = st.text_input("Username (Opsional)", key="username_input")
    message = st.text_area("Pesan Anda")

    if st.button("Kirim Pesan"):
        # Jika username kosong, gunakan "Anonim"
        if not username:
            username = "Anonim"
        send_message(username, message)
        
        
with st.expander("📢 Pesan dari Pengguna", expanded=True):  # Expanded by default
    messages = fetch_messages()
    for msg in messages:
        msg_id = msg["id"]
        reactions = msg["reactions"]

        # Tampilkan pesan utama dengan styling yang lebih baik
        st.markdown(f"""
            <div class="message-box" style="border: 2px solid #4CAF50; border-radius: 10px; padding: 15px; margin-bottom: 20px; background-color: #E8F5E9;">
                <b>📝 {msg['username']}</b>: {msg['message']}<br>
                <div style="margin-top: 10px;">
                    👍 {reactions['👍']} 😂 {reactions['😂']} 😡 {reactions['😡']} 😍 {reactions['😍']} 😱 {reactions['😱']}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Tombol reaksi dengan tooltip dan styling yang lebih baik
        cols = st.columns([1, 1, 1, 1, 1])
        for i, emoji in enumerate(["👍", "😂", "😡", "😍", "😱"]):
            with cols[i]:
                if st.button(
                    emoji, 
                    key=f"{emoji}_{msg_id}",
                    help=f"Klik untuk memberikan reaksi {emoji}"
                ):
                    send_reaction(msg_id, emoji)

        # Tombol "Buka Reply" dengan styling yang lebih baik
        show_replies = st.checkbox(
            "📩 Tampilkan Balasan", 
            key=f"show_replies_{msg_id}",
            help="Klik untuk melihat balasan"
        )
        
        # Tombol "Beri Komentar" dengan styling yang lebih baik
        if st.button(
            "💬 Beri Komentar", 
            key=f"reply_btn_{msg_id}",
            help="Klik untuk membalas pesan ini"
        ):
            st.session_state[f"show_reply_form_{msg_id}"] = True  # Buka form reply
        
        # Jika form reply sedang terbuka, tampilkan tombol "Hide Beri Komentar"
        if st.session_state.get(f"show_reply_form_{msg_id}", False):
            if st.button(
                "❌ Tutup Form Balasan", 
                key=f"hide_reply_btn_{msg_id}",
                help="Klik untuk menyembunyikan form balasan"
            ):
                st.session_state[f"show_reply_form_{msg_id}"] = False  # Sembunyikan form reply
                st.rerun()

        # Form untuk balasan (muncul hanya jika form reply terbuka)
        if st.session_state.get(f"show_reply_form_{msg_id}", False):
            with st.form(key=f"reply_form_{msg_id}"):
                reply_message = st.text_area(
                    "Balasan Anda", 
                    key=f"reply_msg_{msg_id}",
                    placeholder="Ketik balasan Anda di sini..."
                )
                
                # Tombol submit untuk form reply (horizontal)
                submit_cols = st.columns([1, 1])
                with submit_cols[0]:
                    if st.form_submit_button("🚀 Kirim Balasan"):
                        # Ambil username dari session state atau gunakan "Anonim"
                        reply_username = st.session_state.get("username_input", "Anonim")
                        send_reply(msg_id, reply_username, reply_message)
                        st.session_state[f"show_reply_form_{msg_id}"] = False  # Sembunyikan form setelah mengirim
                        st.rerun()
                with submit_cols[1]:
                    if st.form_submit_button("❌ Batal"):
                        st.session_state[f"show_reply_form_{msg_id}"] = False  # Sembunyikan form
                        st.rerun()

        # Tampilkan balasan jika "Buka Reply" dicentang
        if show_replies and msg["replies"]:
            reply_container = st.container()
            with reply_container:
                st.markdown("<div style='margin-left: 30px;'>", unsafe_allow_html=True)
                for reply in msg["replies"]:
                    st.markdown(f"""
                        <div class="message-box" style="border: 1px solid #BBDEFB; border-radius: 8px; padding: 10px; margin-bottom: 10px; background-color: #E3F2FD;">
                            <b>↪️ {reply['username']}</b>: {reply['reply']}
                            <div style="font-size: 0.8em; color: #666;">
                                {time.strftime('%Y-%m-%d %H:%M', time.localtime(reply['timestamp']))}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                    
leaderboard = fetch_leaderboard()

# Leaderboard dengan styling yang lebih menarik
if leaderboard:
    with st.expander("🏆 Leaderboard (Top 5 Reactions)", expanded=True):
        for rank, msg in enumerate(leaderboard, start=1):
            medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else "🎖️"))
            st.markdown(f"""
                <div class="leaderboard-box" style="border: 2px solid #FFD700; border-radius: 10px; padding: 10px; margin-bottom: 10px; background-color: #FFF3E0; color: black;">
                    <b>{medal} Peringkat {rank}: {msg['username']}</b><br>
                    {msg['message']}<br>
                    <div style="font-size: 0.9em; color: #666;">
                        Total Reaksi: {sum(msg['reactions'].values())}
                    </div>
                </div>
            """, unsafe_allow_html=True)

