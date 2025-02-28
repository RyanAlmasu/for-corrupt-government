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

class Reply(BaseModel):
    username: constr(strip_whitespace=True, min_length=1, max_length=50)  # type: ignore
    reply_message: constr(strip_whitespace=True, min_length=1, max_length=500)  # type: ignore
    
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

with st.expander("📩 Kirim Pesan"):
    username = st.text_input("Username (Opsional)", key="username_input")
    message = st.text_area("Pesan Anda")

    if st.button("Kirim Pesan"):
        # Jika username kosong, gunakan "Anonim"
        if not username:
            username = "Anonim"
        send_message(username, message)
        
        
# ========== FRONTEND (Update tampilan pesan) ==========
with st.expander("📢 Pesan dari Pengguna"):
    messages = fetch_messages()
    for msg in messages:
        msg_id = msg["id"]
        reactions = msg["reactions"]

        # Tampilkan pesan utama
        st.markdown(f"""
            <div class="message-box">
                <b>📝 {msg['username']}</b>: {msg['message']}<br>
                👍 {reactions['👍']} 😂 {reactions['😂']} 😡 {reactions['😡']} 😍 {reactions['😍']} 😱 {reactions['😱']}
            </div>
        """, unsafe_allow_html=True)

        # Tombol reaksi
        cols = st.columns(5)
        for i, emoji in enumerate(["👍", "😂", "😡", "😍", "😱"]):
            with cols[i]:
                if st.button(emoji, key=f"{emoji}_{msg_id}"):
                    send_reaction(msg_id, emoji)

        # Tombol "Buka Reply" untuk menampilkan/menyembunyikan balasan
        show_replies = st.checkbox("Buka Reply", key=f"show_replies_{msg_id}")
        
        if st.button("Beri Komentar", key=f"reply_btn_{msg_id}"):
            st.session_state[f"show_reply_form_{msg_id}"] = True  # Buka form reply
        
        # Jika form reply sedang terbuka, tampilkan tombol "Hide Beri Komentar"
        if st.session_state.get(f"show_reply_form_{msg_id}", False):
            if st.button("Hide Beri Komentar", key=f"hide_reply_btn_{msg_id}"):
                st.session_state[f"show_reply_form_{msg_id}"] = False  # Sembunyikan form reply
                st.rerun()


        # Form untuk balasan (muncul hanya jika form reply terbuka)
        if st.session_state.get(f"show_reply_form_{msg_id}", False):
            with st.form(key=f"reply_form_{msg_id}"):
                reply_message = st.text_area("Balasan Anda", key=f"reply_msg_{msg_id}")
                if st.form_submit_button("Kirim Balasan"):
                    # Ambil username dari session state atau gunakan "Anonim"
                    reply_username = st.session_state.get("username_input", "Anonim")
                    send_reply(msg_id, reply_username, reply_message)
                    st.session_state[f"show_reply_form_{msg_id}"] = False  # Sembunyikan form setelah mengirim
                    st.rerun()

        # Tampilkan balasan jika "Buka Reply" dicentang
        if show_replies and msg["replies"]:
            reply_container = st.container()
            with reply_container:
                st.markdown("<div style='margin-left: 30px;'>", unsafe_allow_html=True)
                for reply in msg["replies"]:
                    st.markdown(f"""
                        <div class="message-box" style="background-color: #e8f4f8;">
                            <b>↪️ {reply['username']}</b>: {reply['reply']}
                            <div style="font-size: 0.8em; color: #666;">
                                {time.strftime('%Y-%m-%d %H:%M', time.localtime(reply['timestamp']))}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                    
leaderboard = fetch_leaderboard()

if leaderboard:
    with st.expander("🏆 Leaderboard (Top 5 Reactions)"):
        for rank, msg in enumerate(leaderboard, start=1):
            st.markdown(f"🥇 {rank}. {msg['username']}: {msg['message']}")  
