# import streamlit as st
# import requests

# BACKEND_URL = "http://127.0.0.1:8000"

# st.title("💬 Lontarkan kata-kata anda buat pemerintah Indo! (Anonim)")

# def apply_styles():
#     st.markdown("""
#         <style>
#         .message-box {
#             border: 2px solid #ddd;
#             border-radius: 10px;
#             padding: 10px;
#             margin-bottom: 10px;
#             background-color: #f9f9f9;
#             color: black;
#         }
#         </style>
#     """, unsafe_allow_html=True)

# apply_styles()

# if "reacted_messages" not in st.session_state:
#     st.session_state.reacted_messages = {}

# def fetch_messages():
#     try:
#         response = requests.get(f"{BACKEND_URL}/messages")
#         return response.json() if response.status_code == 200 else []
#     except requests.exceptions.RequestException:
#         st.error("Gagal mengambil data dari server.")
#         return []

# def send_reaction(msg_id, emoji):
#     try:
#         reaction_response = requests.post(f"{BACKEND_URL}/react/{msg_id}", json={"emoji": emoji})

#         if reaction_response.status_code == 200:
#             response_data = reaction_response.json()
            
#             if response_data["message"] == "Reaction dihapus":
#                 if msg_id in st.session_state.reacted_messages:  # ✅ CEGAH KeyError
#                     del st.session_state.reacted_messages[msg_id]
#             else:
#                 st.session_state.reacted_messages[msg_id] = emoji  

#             st.rerun()
#         else:
#             error_message = reaction_response.json().get("detail", "❌ Gagal memberikan reaksi.")
#             st.warning(error_message)
#     except requests.exceptions.RequestException:
#         st.error("Gagal menghubungi server.")


# def send_message(username, message):
#     if not username or not message:
#         st.warning("⚠️ Harap isi username dan pesan!")
#         return

#     try:
#         response = requests.post(f"{BACKEND_URL}/messages", json={"username": username, "message": message})

#         if response.status_code == 200:
#             st.success("✅ Pesan berhasil dikirim!")
#             st.rerun()
#         else:
#             st.warning(response.json().get("detail", "❌ Gagal mengirim pesan."))
#     except requests.exceptions.RequestException:
#         st.error("Gagal menghubungi server.")
# # **Fungsi untuk mengambil leaderboard dari backend**
# def fetch_leaderboard():
#     response = requests.get(f"{BACKEND_URL}/leaderboard")
#     if response.status_code == 200:
#         return response.json()
#     else:
#         st.error("❌ Gagal mengambil leaderboard.")
#         return []

# with st.expander("📩 Kirim Pesan"):
#     username = st.text_input("Username (Anonim)")
#     message = st.text_area("Pesan Anda")

#     if st.button("Kirim Pesan"):
#         send_message(username, message)

# with st.expander("📢 Pesan dari Pengguna"):
#     messages = fetch_messages()
#     for msg in messages:
#         msg_id = msg["id"]
#         reactions = msg["reactions"]

#         st.markdown(f"""
#             <div class="message-box">
#                 <b>📝 {msg['username']}</b>: {msg['message']}<br>
#                 👍 {reactions['👍']} 😂 {reactions['😂']} 😡 {reactions['😡']} 😍 {reactions['😍']} 😱 {reactions['😱']}
#             </div>
#         """, unsafe_allow_html=True)

#         cols = st.columns(5)
#         for i, emoji in enumerate(["👍", "😂", "😡", "😍", "😱"]):
#             with cols[i]:
#                 if st.button(emoji, key=f"{emoji}_{msg_id}"):
#                     send_reaction(msg_id, emoji)

# # **UI Leaderboard**
# leaderboard = fetch_leaderboard()

# if leaderboard:  # ✅ Hanya tampilkan jika ada data
#     with st.expander("🏆 Leaderboard (Top 5 Reactions)"):
#         for rank, msg in enumerate(leaderboard, start=1):
#             st.markdown(f"""
#                 <div class="message-box">
#                     <b>🥇 {rank}. {msg['username']}</b>: {msg['message']}<br>
#                     👍 {msg['reactions']['👍']} 😂 {msg['reactions']['😂']} 😡 {msg['reactions']['😡']} 😍 {msg['reactions']['😍']} 😱 {msg['reactions']['😱']}
#                 </div>
#             """, unsafe_allow_html=True)


