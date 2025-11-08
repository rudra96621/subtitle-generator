import streamlit as st
import streamlit.components.v1 as components
from pymongo import MongoClient
from urllib.parse import quote_plus
from bson import ObjectId
import gridfs

def get_connection():
    username = "rudra"
    password = quote_plus("Rudra@123")
    uri = f"mongodb+srv://{username}:{password}@cluster0.ucw0onm.mongodb.net/subtitleApp?retryWrites=true&w=majority"
    client = MongoClient(uri, tls=True)
    db = client["subtitleApp"]
    return db

def render_tag(text, bg_color):
    html = f"""
    <span style='
        background-color: {bg_color};
        color: white;
        padding: 4px 8px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 0.85rem;
        margin-right: 5px;
    '>{text}</span>
    """
    components.html(html, height=35)

def admin_panel():
    st.markdown("## 🛠️ Admin Dashboard")
    st.markdown("Manage users, roles, history, and more.")
    st.markdown("---")
    with st.sidebar:
        avatar_letter = st.session_state.username[:1].upper()

        if st.button(avatar_letter, key="avatar_btn_admin"):
            if not st.session_state.is_processing:
                st.session_state.show_dropdown = not st.session_state.show_dropdown

        if st.session_state.show_dropdown:
            if st.button("🧾 Profile") and not st.session_state.is_processing:
                st.session_state.page = "profile"
                st.session_state.show_dropdown = False
                st.rerun()
            if st.button("🚪 Logout") and not st.session_state.is_processing:
                from app import logout  # make sure this doesn't cause circular import
                logout()

        st.markdown("## 📥 Recent Downloads")
        if st.session_state.history:
            exp = st.expander("⬇️ View Recent Files")
            with exp:
                for idx, item in enumerate(st.session_state.history):
                    st.markdown(f"**🎮 {item['video_name']}**", unsafe_allow_html=True)
                    st.download_button("📄 Subtitle", item['srt_data'], file_name=item['srt_name'], key=f"srt_admin_{idx}")
                    st.download_button("🎮 Video", item['video_data'], file_name=item['video_name'], key=f"vid_admin_{idx}")
        else:
            st.info("No recent files yet.")

        st.markdown("### 👤 Account")
        if not st.session_state.authenticated:
            if st.button("🔐 Login"):
                st.session_state.page = "login"
            if st.button("📝 Signup"):
                st.session_state.page = "signup"
        else:
            st.markdown(f"✅ Logged in as `{st.session_state.username}`")

    if st.button("🏠 Back to Main Page"):
        st.session_state.page = "main"
        st.rerun()

    db = get_connection()
    users = db["users"]
    fs = gridfs.GridFS(db)

    search_query = st.text_input("🔍 Search by username or email:")

    if search_query:
        query = {"$or": [
            {"username": {"$regex": search_query, "$options": "i"}},
            {"email": {"$regex": search_query, "$options": "i"}}
        ]}
    else:
        query = {}

    user_list = list(users.find(query))

    if not user_list:
        st.info("No users found.")
        return

    for user in user_list:
        username = user.get("username", "N/A")
        full_name = user.get("full_name", "N/A")
        email = user.get("email", "N/A")
        is_admin = user.get("is_admin", False)
        is_blocked = user.get("is_blocked", False)

        with st.expander(f"👤 {username} ({full_name})"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**📧 Email:** {email}")
                render_tag("🛡️ Admin" if is_admin else "👤 User", "#4CAF50" if is_admin else "#2196F3")
                render_tag("⛔ Blocked" if is_blocked else "✅ Active", "#e53935" if is_blocked else "#43A047")

            with col2:
                # 🔁 Toggle Role
                if st.button(f"🔁 {'Demote to User' if is_admin else 'Promote to Admin'}", key=f"role_{username}"):
                    users.update_one({"username": username}, {"$set": {"is_admin": not is_admin}})
                    st.success(f"{'Promoted' if not is_admin else 'Demoted'} successfully.")
                    st.rerun()

                # ⛔ Block/Unblock
                if st.button(f"{'✅ Unblock' if is_blocked else '⛔ Block'} User", key=f"block_{username}"):
                    users.update_one({"username": username}, {"$set": {"is_blocked": not is_blocked}})
                    st.success(f"{'Unblocked' if is_blocked else 'Blocked'} successfully.")
                    st.rerun()

                # 🗑️ Delete User
                if st.button("🗑️ Delete User", key=f"delete_{username}"):
                    users.delete_one({"username": username})
                    st.warning(f"{username} deleted.")
                    st.rerun()

            st.markdown("---")
            st.markdown("### 📜 History")

            history = user.get("history", [])
            if history:
                for idx, h in enumerate(history):
                    st.markdown(f"📄 `{h['srt_name']}` | 🎥 `{h['video_name']}`")
                    if st.button("🗑️ Delete This History", key=f"del_hist_{username}_{idx}"):
                        users.update_one({"username": username}, {"$pull": {"history": h}})
                        st.success("History entry deleted.")
                        st.rerun()
            else:
                st.info("No subtitle history found.")
