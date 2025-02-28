# from fastapi import FastAPI, HTTPException, Request
# from pydantic import BaseModel, constr
# import uuid
# import time
# import hashlib
# from fastapi.responses import JSONResponse
# from collections import defaultdict
# from fastapi.middleware.cors import CORSMiddleware

# user_reactions = defaultdict(dict)  # ✅ Mencegah KeyError jika session kosong

# api = FastAPI()

# api.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Bisa dibatasi ke domain tertentu
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# messages_data = []  # Simpan daftar pesan

# last_message = {}  # Menyimpan hash username dan waktu pesan terakhirnya

# MESSAGE_COOLDOWN = 30  

# class Message(BaseModel):
#     username: constr(strip_whitespace=True, min_length=1, max_length=50) # type: ignore
#     message: constr(strip_whitespace=True, min_length=1, max_length=500) # type: ignore

# class Reaction(BaseModel):
#     emoji: str

# def hash_username(username: str) -> str:
#     return hashlib.sha256(username.encode()).hexdigest()

# @api.post("/messages")
# async def add_message(msg: Message, request: Request):
#     client_ip = request.client.host  
#     hashed_username = hash_username(msg.username)  

#     if hashed_username in last_message:
#         last_time = last_message[hashed_username]
#         elapsed_time = time.time() - last_time
#         if elapsed_time < MESSAGE_COOLDOWN:
#             raise HTTPException(
#                 status_code=429, 
#                 detail=f"Tunggu {int(MESSAGE_COOLDOWN - elapsed_time)} detik sebelum mengirim pesan lagi."
#             )

#     new_message = {
#         "id": uuid.uuid4().hex,
#         "username": hashed_username[:10],  
#         "message": msg.message,
#         "reactions": {"👍": 0, "😂": 0, "😡": 0, "😍": 0, "😱": 0},
#         "timestamp": time.time()
#     }
#     messages_data.append(new_message)
#     last_message[hashed_username] = time.time()

#     return JSONResponse(content={"status": "success", "message": "Pesan berhasil dikirim", "data": new_message})

# @api.post("/react/{message_id}")
# async def react_message(message_id: str, reaction: Reaction, request: Request):
#     client_ip = request.client.host  

#     for msg in messages_data:
#         if msg["id"] == message_id:
#             if message_id not in user_reactions:
#                 user_reactions[message_id] = {}

#             # Jika pengguna sudah react sebelumnya dengan reaction yang sama, batalkan reaction
#             if client_ip in user_reactions[message_id]:
#                 old_reaction = user_reactions[message_id][client_ip]
                
#                 if old_reaction == reaction.emoji:
#                     msg["reactions"][old_reaction] -= 1  # Kurangi reaction
#                     del user_reactions[message_id][client_ip]  # Hapus data user dari daftar reaction
#                     return JSONResponse(content={"message": "Reaction dihapus", "reactions": msg["reactions"]})

#                 # Jika reaction berbeda, ganti reaction lama ke baru
#                 msg["reactions"][old_reaction] -= 1  

#             # Tambahkan reaction baru
#             user_reactions[message_id][client_ip] = reaction.emoji
#             msg["reactions"][reaction.emoji] += 1  

#             return JSONResponse(content={"message": "Reaction berhasil diberikan atau diganti", "reactions": msg["reactions"]})

#     raise HTTPException(status_code=404, detail="Pesan tidak ditemukan")

# @api.get("/messages")
# async def get_messages():
#     return messages_data

# @api.get("/leaderboard")
# def get_leaderboard():
#     # Filter hanya pesan dengan minimal 1 reaction
#     filtered_messages = [msg for msg in messages_data if sum(msg["reactions"].values()) > 0]

#     # Urutkan berdasarkan total jumlah reaction (dari terbesar ke terkecil)
#     sorted_messages = sorted(filtered_messages, key=lambda x: sum(x["reactions"].values()), reverse=True)

#     # Ambil top 5 pesan dengan reaction tertinggi
#     return JSONResponse(content=sorted_messages[:5], status_code=200)
