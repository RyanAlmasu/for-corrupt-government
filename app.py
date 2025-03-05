import streamlit as st
import requests
import threading
import time
import hashlib
import uuid
from datetime import datetime
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, constr
import uvicorn
import random
from threading import Lock

st.set_page_config(
    page_title="Suara Rakyat", 
    layout="wide"
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
messages_lock = Lock()

MESSAGE_COOLDOWN = 30

class HonestyTest:
    def __init__(self):
        self.all_questions = [
            {
                "question": "💰 Dapat uang 1 miliar secara misterius, apa yang kamu lakukan?",
                "options": [
                    {"text": "Lapor ke KPK", "score": 0},
                    {"text": "Transfer ke rekening keluarga dulu", "score": 5},
                    {"text": "Bilang 'nggak tahu, tau-tau ada'", "score": 10}
                ]
            },
            {
                "question": "🏗️ Proyek infrastruktur desa menganggur 2 tahun, kamu?",
                "options": [
                    {"text": "Audit transparan", "score": 0},
                    {"text": "Buat laporan fiktif", "score": 5},
                    {"text": "Salakan ke kontraktor", "score": 10}
                ]
            },
            {
                "question": "🎁 Dapat hadiah mobil dari rekanan, responmu?",
                "options": [
                    {"text": "Tolak tegas", "score": 0},
                    {"text": "Terima tapi laporkan", "score": 5}, 
                    {"text": "Parkir di rumah kedua", "score": 10}
                ]
            },
            {
                "question": "📉 Ada kebocoran APBD, tindakanmu?",
                "options": [
                    {"text": "Investigasi internal", "score": 0},
                    {"text": "Bentuk tim khusus (tapi ga kerja)", "score": 5},
                    {"text": "Salahkan sistem lama", "score": 10}
                ]
            },
            {
                "question": "👮♀️ KPK datang ke kantormu, kamu?",
                "options": [
                    {"text": "Sambut hangat", "score": 0},
                    {"text": "Pura-pura rapat diluar", "score": 5},
                    {"text": "Tutup semua berkas", "score": 10}
                ]
            },
            {
                "question": "💸 Dana bansos mau dicairkan, kamu?",
                "options": [
                    {"text": "Distribusi merata", "score": 0},
                    {"text": "Prioritaskan pendukung", "score": 5},
                    {"text": "Tahan buat modal usaha", "score": 10}
                ]
            },
            {
                "question": "📱 Chat berisi bukti suap muncul, kamu?",
                "options": [
                    {"text": "Forward ke KPK", "score": 0},
                    {"text": "Delete chat secepatnya", "score": 5},
                    {"text": "Buat grup 'Family Group'", "score": 10}
                ]
            },
            {
                "question": "✈️ Mau dinas luar negeri, kamu?",
                "options": [
                    {"text": "Tolak demi efisiensi", "score": 0},
                    {"text": "Ajukan budget standar", "score": 5},
                    {"text": "Minta perjalanan first class", "score": 10}
                ]
            },
            {
                "question": "📊 Laporan keuangan ada selisih, kamu?",
                "options": [
                    {"text": "Transparan ke publik", "score": 0},
                    {"text": "Cari akun kreatif", "score": 5},
                    {"text": "Bakar arsip lama", "score": 10}
                ]
            },
            {
                "question": "🎯 Target proyek tidak tercapai, kamu?",
                "options": [
                    {"text": "Evaluasi proses", "score": 0},
                    {"text": "Buat laporan pencapaian 120%", "score": 5},
                    {"text": "Salahkan cuaca dan Tuhan", "score": 10}
                ]
            },
            # 20 Pertanyaan Baru
            {
                "question": "🛢️ Ada kebocoran pipa minyak, kamu?",
                "options": [
                    {"text": "Perbaiki segera", "score": 0},
                    {"text": "Tutupi dengan karung", "score": 5},
                    {"text": "Jual minyak bocoran", "score": 10}
                ]
            },
            {
                "question": "📚 Dana pendidikan dipotong, tindakanmu?",
                "options": [
                    {"text": "Protes ke DPRD", "score": 0},
                    {"text": "Cari sponsor swasta", "score": 5},
                    {"text": "Buat program fiktif", "score": 10}
                ]
            },
            {
                "question": "🏥 Ada warga miskin butuh operasi, kamu?",
                "options": [
                    {"text": "Bantu sepenuhnya", "score": 0},
                    {"text": "Buat penggalangan dana", "score": 5},
                    {"text": "Sarankan pinjam rentenir", "score": 10}
                ]
            },
            {
                "question": "🌳 Hutan lindung mau dikonversi, kamu?",
                "options": [
                    {"text": "Tolak tegas", "score": 0},
                    {"text": "Minta studi AMDAL", "score": 5},
                    {"text": "Kasih izin khusus", "score": 10}
                ]
            },
            {
                "question": "🕵️♂️ Ada whistleblower di kantormu, kamu?",
                "options": [
                    {"text": "Lindungi identitasnya", "score": 0},
                    {"text": "Pindahkan jabatan", "score": 5},
                    {"text": "Bocorkan ke preman", "score": 10}
                ]
            },
            {
                "question": "💼 Ada proyek 'siluman' di LPJ, kamu?",
                "options": [
                    {"text": "Audit khusus", "score": 0},
                    {"text": "Revisi laporan", "score": 5},
                    {"text": "Legalisasikan sebagai dana taktis", "score": 10}
                ]
            },
            {
                "question": "🎙️ Dihadang wartawan investigasi, kamu?",
                "options": [
                    {"text": "Jawab transparan", "score": 0},
                    {"text": "Alihkan topik", "score": 5},
                    {"text": "Kirim bodyguard", "score": 10}
                ]
            },
            {
                "question": "📅 Ada acara seremonial penting, kamu?",
                "options": [
                    {"text": "Hadir tepat waktu", "score": 0},
                    {"text": "Kirim staf sebagai perwakilan", "score": 5},
                    {"text": "Minta uang jalan dulu", "score": 10}
                ]
            },
            {
                "question": "🛠️ Alat proyek rusak parah, kamu?",
                "options": [
                    {"text": "Perbaiki profesional", "score": 0},
                    {"text": "Beli baru tapi markup", "score": 5},
                    {"text": "Sewa alat seken", "score": 10}
                ]
            },
            {
                "question": "🌐 Ada demo buruh besar-besaran, kamu?",
                "options": [
                    {"text": "Dengar keluhan", "score": 0},
                    {"text": "Janji komisi tripartit", "score": 5},
                    {"text": "Kerahkan preman bayaran", "score": 10}
                ]
            },
            {
                "question": "📜 Aturan baru merugikan rakyat, kamu?",
                "options": [
                    {"text": "Cabut peraturan", "score": 0},
                    {"text": "Buat pengecualian", "score": 5},
                    {"text": "Terbitkan PERDA tambahan", "score": 10}
                ]
            },
            {
                "question": "🛑 Ada kasus narkoba di lingkunganmu, kamu?",
                "options": [
                    {"text": "Laporkan ke polisi", "score": 0},
                    {"text": "Bersihkan internal dulu", "score": 5},
                    {"text": "Jadikan alat tekanan", "score": 10}
                ]
            },
            {
                "question": "📡 Internet desa lambat tapi dana habis, kamu?",
                "options": [
                    {"text": "Audit penyedia", "score": 0},
                    {"text": "Minta tambahan anggaran", "score": 5},
                    {"text": "Salahkan frekuensi 5G", "score": 10}
                ]
            },
            {
                "question": "🌧️ Banjir besar terjadi, kamu?",
                "options": [
                    {"text": "Turun langsung bantu", "score": 0},
                    {"text": "Bentuk posko darurat", "score": 5},
                    {"text": "Salurkan ke rekening bencana", "score": 10}
                ]
            },
            {
                "question": "📛 Ada pejabat nakal di timmu, kamu?",
                "options": [
                    {"text": "Lapor atasan", "score": 0},
                    {"text": "Pindahkan jabatan", "score": 5},
                    {"text": "Jadikan mitra bisnis", "score": 10}
                ]
            },
            {
                "question": "🛒 Ada proyek pengadaan barang fiktif, kamu?",
                "options": [
                    {"text": "Bongkar skema", "score": 0},
                    {"text": "Revisi kontrak", "score": 5},
                    {"text": "Naikkan nilai proyek", "score": 10}
                ]
            },
            {
                "question": "🎓 Beasiswa tidak tepat sasaran, kamu?",
                "options": [
                    {"text": "Evaluasi sistem", "score": 0},
                    {"text": "Perbaiki data manual", "score": 5},
                    {"text": "Salahkan algoritma", "score": 10}
                ]
            },
            {
                "question": "⚖️ Ada konflik tanah dengan warga, kamu?",
                "options": [
                    {"text": "Dengar kedua pihak", "score": 0},
                    {"text": "Bentuk tim mediasi", "score": 5},
                    {"text": "Kirim aparat keamanan", "score": 10}
                ]
            },
            {
                "question": "🔍 BPK temukan indikasi korupsi, kamu?",
                "options": [
                    {"text": "Buka data seluasnya", "score": 0},
                    {"text": "Minta waktu verifikasi", "score": 5},
                    {"text": "Tuntut ganti rugi", "score": 10}
                ]
            },
            {
                "question": "🌇 Ada pembangunan mal di tanah warga, kamu?",
                "options": [
                    {"text": "Hentikan proyek", "score": 0},
                    {"text": "Negosiasi ulang", "score": 5},
                    {"text": "Dukung full dengan APBD", "score": 10}
                ]
            }
        ]
        
        # Acak pertanyaan dan ambil 10 pertama
        random.shuffle(self.all_questions)
        self.questions = self.all_questions[:10]
        
        # Acak urutan opsi jawaban untuk setiap pertanyaan
        for q in self.questions:
            random.shuffle(q['options'])
            
        self.total_score = 0
        self.current_question = 0

class Reply(BaseModel):
    username: constr(strip_whitespace=True, min_length=1, max_length=50)  # type: ignore
    reply_message: constr(strip_whitespace=True, min_length=1, max_length=500)  # type: ignore

class Message(BaseModel):
    username: constr(strip_whitespace=True, min_length=1, max_length=50)  # type: ignore
    message: constr(strip_whitespace=True, min_length=1, max_length=500)  # type: ignore

class Reaction(BaseModel):
    emoji: str

def hash_username(username: str) -> str:
    return hashlib.sha256(username.encode()).hexdigest()


@api.post("/messages")
async def add_message(msg: Message, request: Request):
    hashed_username = hash_username(msg.username)
    
    with messages_lock:
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
            "replies": [],
            "timestamp": time.time()
        }
        messages_data.append(new_message)
        last_message[hashed_username] = time.time()

    return JSONResponse(content={"status": "success", "message": "Pesan berhasil dikirim", "data": new_message})

@api.post("/react/{message_id}")
async def react_message(message_id: str, reaction: Reaction):
    with messages_lock:
        for msg in messages_data:
            if msg["id"] == message_id:
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
    with messages_lock:
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
    with messages_lock:
        filtered_messages = [msg for msg in messages_data if sum(msg["reactions"].values()) > 0]
        sorted_messages = sorted(filtered_messages, key=lambda x: sum(x["reactions"].values()), reverse=True)
        return JSONResponse(content=sorted_messages[:5], status_code=200)

# ========== BACKEND (Threading) ==========
def run_api():
    uvicorn.run(api, host="127.0.0.1", port=8000)

thread = threading.Thread(target=run_api, daemon=True)
thread.start()

# ========== FRONTEND (Streamlit) ==========
BACKEND_URL = "http://127.0.0.1:8000"

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
        .username-input {
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

apply_styles()

if "reacted_messages" not in st.session_state:
    st.session_state.reacted_messages = {}
    
if 'test' not in st.session_state:
    st.session_state.test = None
if 'test_started' not in st.session_state:
    st.session_state.test_started = False
if 'test_completed' not in st.session_state:
    st.session_state.test_completed = False

def send_reaction(msg_id, emoji):
    try:
        reaction_response = requests.post(
            f"{BACKEND_URL}/react/{msg_id}", 
            json={"emoji": emoji}
        )
        if reaction_response.status_code == 200:
            st.rerun()
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
    if not message:
        st.warning("⚠️ Harap isi pesan!")
        return

    username = username or "Anonim"
    
    try:
        response = requests.post(
            f"{BACKEND_URL}/messages", 
            json={"username": username, "message": message}
        )

        if response.status_code == 200:
            st.success("✅ Pesan berhasil dikirim!")
            st.rerun()
        else:
            st.warning(f"❌ Error: {response.json().get('detail', 'Unknown error')}")
    except requests.exceptions.RequestException:
        st.error("Gagal menghubungi server.")

def send_reply(message_id, username, reply):
    username = username or "Anonim"
    
    if not reply:
        st.warning("⚠️ Harap isi balasan!")
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
            st.warning(f"❌ Gagal mengirim balasan: {response.json().get('detail', 'Unknown error')}")
    except requests.exceptions.RequestException:
        st.error("Gagal menghubungi server.")

def fetch_leaderboard():
    try:
        response = requests.get(f"{BACKEND_URL}/leaderboard")
        return response.json() if response.status_code == 200 else []
    except requests.exceptions.RequestException:
        st.error("Gagal mengambil leaderboard.")
        return []

st.title("💬 Suara Untuk Negeri")
st.write("Sampaikan pendapat Anda kepada pemerintah secara anonim")

with st.expander("📩 Kirim Pesan"):
    username = st.text_input("Username (Opsional)", key="username_input")
    message = st.text_area("Pesan Anda")

    if st.button("Kirim Pesan"):
        send_message(username, message)
        
with st.expander("📢 Pesan dari Pengguna", expanded=True):
    messages = fetch_messages()
    for msg in messages:
        msg_id = msg["id"]
        reactions = msg["reactions"]

        st.markdown(f"""
            <div class="message-box" style="border: 2px solid #4CAF50; border-radius: 10px; padding: 15px; margin-bottom: 20px; background-color: #E8F5E9;">
                <b>📝 {msg['username']}</b>: {msg['message']}<br>
                <div style="margin-top: 10px;">
                    👍 {reactions['👍']} 😂 {reactions['😂']} 😡 {reactions['😡']} 😍 {reactions['😍']} 😱 {reactions['😱']}
                </div>
            </div>
        """, unsafe_allow_html=True)

        cols = st.columns([1, 1, 1, 1, 1])
        for i, emoji in enumerate(["👍", "😂", "😡", "😍", "😱"]):
            with cols[i]:
                if st.button(emoji, key=f"{emoji}_{msg_id}"):
                    send_reaction(msg_id, emoji)

        show_replies = st.checkbox("📩 Tampilkan Balasan", key=f"show_replies_{msg_id}")
        
        if st.button("💬 Beri Komentar", key=f"reply_btn_{msg_id}"):
            st.session_state[f"show_reply_form_{msg_id}"] = True
        
        if st.session_state.get(f"show_reply_form_{msg_id}", False):
            if st.button("❌ Tutup Form Balasan", key=f"hide_reply_btn_{msg_id}"):
                st.session_state[f"show_reply_form_{msg_id}"] = False
                st.rerun()

        if st.session_state.get(f"show_reply_form_{msg_id}", False):
            with st.form(key=f"reply_form_{msg_id}"):
                reply_message = st.text_area("Balasan Anda", key=f"reply_msg_{msg_id}")
                submit_cols = st.columns([1, 1])
                with submit_cols[0]:
                    if st.form_submit_button("🚀 Kirim Balasan"):
                        reply_username = st.session_state.get("username_input") or "Anonim"
                        send_reply(msg_id, reply_username, reply_message)
                        st.session_state[f"show_reply_form_{msg_id}"] = False
                        st.rerun()
                with submit_cols[1]:
                    if st.form_submit_button("❌ Batal"):
                        st.session_state[f"show_reply_form_{msg_id}"] = False
                        st.rerun()

        if show_replies and msg["replies"]:
            with st.container():
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
if leaderboard:
    with st.expander("🏆 Leaderboard (Top 5 Reactions)", expanded=True):
        for rank, msg in enumerate(leaderboard, start=1):
            medal = "🥇" if rank == 1 else ("🥈" if rank == 2 else ("🥉" if rank == 3 else "🎖️"))
            st.markdown(f"""
                <div style="border: 2px solid #FFD700; border-radius: 10px; padding: 10px; margin-bottom: 10px; background-color: #FFF3E0; color: black;">
                    <b>{medal} Peringkat {rank}: {msg['username']}</b><br>
                    {msg['message']}<br>
                    <div style="font-size: 0.9em; color: #666;">
                        Total Reaksi: {sum(msg['reactions'].values())}
                    </div>
                </div>
            """, unsafe_allow_html=True)

with st.expander("🧪 Test Kejujuran: Berapa Persen Mirip Pejabat?", expanded=True):
    if not st.session_state.test_started:
        st.write("""
        ### Uji Mental Koruptor dalam 10 Pertanyaan!
        Jawab dengan jujur (atau tidak) dan lihat seberapa mirip kamu dengan pejabat!
        """)
        if st.button("Mulai Test"):
            st.session_state.test = HonestyTest()
            st.session_state.test_started = True
            st.session_state.test_completed = False
            st.rerun()
    else:
        test = st.session_state.test
        if not st.session_state.test_completed:
            # Progress bar
            progress = test.current_question / len(test.questions)
            st.progress(progress)
            
            # Tampilkan pertanyaan
            q = test.questions[test.current_question]
            st.subheader(f"Pertanyaan {test.current_question + 1}")
            st.markdown(f"#### {q['question']}")
            
            # Tampilkan opsi
            cols = st.columns(3)
            for option in q['options']:
                    if st.button(
                        option['text'], 
                        key=f"q{test.current_question}_opt{option['score']}",  # Key unik berdasarkan skor
                        use_container_width=True
                    ):
                        test.total_score += option['score']
                        test.current_question += 1
                        
                        if test.current_question >= len(test.questions):
                            st.session_state.test_completed = True
                        st.rerun()
        else:
            # Hitung hasil
            total_score = min(test.total_score, 100)  # Maksimal 100
            similarity = total_score
            
            # Tampilkan hasil dengan animasi
            st.balloons()
            st.subheader("🕵️♂️ Hasil Test Kejujuran Kamu!")
            st.markdown(f"""
                <div style="text-align: center; padding: 20px; border-radius: 10px; 
                            background: {'#4CAF50' if similarity < 30 else '#FFC107' if similarity < 70 else '#F44336'};
                            color: white;">
                    <h1>{similarity}% Mirip Pejabat!</h1>
                </div>
            """, unsafe_allow_html=True)
            
            if similarity < 30:
                st.success("""
                🎉 **Anda Rakyat Biasa!**  
                Masih terlalu jujur untuk jadi pejabat. Disarankan banyak belajar 'ilmu administrasi kreatif'
                """)
            elif similarity < 70:
                st.warning("""
                ⚠️ **Potensi Pejabat!**  
                Sudah mulai paham 'tata kelola anggaran', tapi masih perlu belajar 'manajemen bukti fisik'
                """)
            else:
                st.error("""
                🔥 **Calon Koruptor!**  
                Jiwa kepemimpinan kuat! Direkomendasikan jadi ketua panitia proyek strategis nasional
                """)
                
            # Tombol reset
            if st.button("🔄 Coba Lagi"):
                st.session_state.test = None
                st.session_state.test_started = False
                st.session_state.test_completed = False
                st.rerun()