
# Import Required Modules
import streamlit as st
import whisper
import os
import tempfile
from deep_translator import GoogleTranslator
from subtitle_generator import get_font_for_text, export_srt, render_subtitles_on_video
from pymongo import MongoClient
import bcrypt
import gridfs
from bson import ObjectId
from urllib.parse import quote_plus
import certifi
from admin_panel import admin_panel


# MongoDB Connection
def get_connection():
    username = os.getenv("MONGODB_USERNAME", "rudra")
    password = quote_plus(os.getenv("MONGODB_PASSWORD", "Rudra@123"))
    cluster_url = os.getenv("MONGODB_CLUSTER_URL", "cluster0.ucw0onm.mongodb.net")
    database_name = os.getenv("MONGODB_DATABASE", "subtitleApp")
    
    uri = f"mongodb+srv://{username}:{password}@{cluster_url}/{database_name}?retryWrites=true&w=majority"
    
    try:
        client = MongoClient(uri, tls=True, serverSelectionTimeoutMS=5000)
        # Test the connection
        client.admin.command('ping')
        db = client[database_name]
        return db
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
        st.error("Please check your MongoDB credentials and network connection.")
        return None

# Store new file versions and keep only 3 per user
def save_to_gridfs(username, video_path, srt_path):
    db = get_connection()
    if db is None:
        st.error("❌ Cannot save files: Database connection failed")
        return False
    
    try:
        fs = gridfs.GridFS(db)

        with open(video_path, "rb") as v, open(srt_path, "rb") as s:
            video_id = fs.put(v, filename=os.path.basename(video_path))
            srt_id = fs.put(s, filename=os.path.basename(srt_path))

        db["users"].update_one(
            {"username": username},
            {"$push": {
                "history": {
                    "$each": [{
                        "video_file_id": video_id,
                        "srt_file_id": srt_id,
                        "video_name": os.path.basename(video_path),
                        "srt_name": os.path.basename(srt_path)
                    }],
                    "$slice": -3
                }
            }}
        )
        return True
    except Exception as e:
        st.error(f"❌ Failed to save files to database: {str(e)}")
        return False

def load_recent_history_from_mongo(username, db):
    if db is None:
        st.warning("⚠️ Cannot load history: Database connection failed")
        return
    
    try:
        fs = gridfs.GridFS(db)
        user = db["users"].find_one({"username": username})
        
        if not user:
            st.warning(f"⚠️ User '{username}' not found in database")
            return
            
        st.session_state.history = []
        history_items = user.get("history", [])[::-1]

        for entry in history_items:
            try:
                video_data = fs.get(ObjectId(entry['video_file_id'])).read()
                srt_data = fs.get(ObjectId(entry['srt_file_id'])).read()
                st.session_state.history.append({
                    "video_name": entry['video_name'],
                    "srt_name": entry['srt_name'],
                    "video_data": video_data,
                    "srt_data": srt_data
                })
            except Exception as e:
                st.warning(f"⚠️ Failed to load history item: {str(e)}")
                continue
    except Exception as e:
        st.error(f"❌ Failed to load user history: {str(e)}")

# Session Initialization
for key, value in {
    'authenticated': False,
    'username': "",
    'page': 'main',  # Default to main page
    'processing_done': False,
    'srt_file': None,
    'video_file': None,
    'uploaded_file': None,
    'spoken_lang': 'Auto',
    'target_lang': 'English',
    'show_dropdown': False,
    'device': 'CPU',
    'model_size': 'tiny',
    'history': [],
    'is_processing': False,
    'role': None,
    'model_loaded': {}
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Ensure page is always set to main if not authenticated
if not st.session_state.authenticated and st.session_state.page not in ['login', 'signup', 'reset_password']:
    st.session_state.page = 'main'

if 'SUPPORTED_LANGS' not in st.session_state:
    langs = GoogleTranslator().get_supported_languages(as_dict=True)
    st.session_state.LANG_DICT = {name.title(): code for name, code in langs.items()}

#os.makedirs('output', exist_ok=True)

@st.cache_resource(show_spinner="🔄 Loading Whisper model...")
def load_whisper_model(model_size="tiny", device="cpu"):
    os.environ["WHISPER_CACHE_DIR"] = os.path.expanduser("~/.cache/whisper")
    return whisper.load_model(model_size, device=device)

def get_or_load_model():
    key = f"{st.session_state.model_size}_{st.session_state.device}"
    if key not in st.session_state.model_loaded:
        with st.spinner(""):
            st.session_state.model_loaded[key] = load_whisper_model(
                model_size=st.session_state.model_size,
                device="cuda" if st.session_state.device == "GPU (CUDA)" else "cpu"
            )
    return st.session_state.model_loaded[key]

def signup():
    st.title("📝 Sign Up")

    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        if not full_name or not email or not username or not password:
            st.error("⚠️ All fields are required.")
            return

        if "@" not in email or "." not in email:
            st.error("⚠️ Please enter a valid email address.")
            return

        if len(username) < 3:
            st.error("⚠️ Username must be at least 3 characters long.")
            return

        if len(password) < 6:
            st.error("⚠️ Password must be at least 6 characters long.")
            return

        db = get_connection()
        if db is None:
            st.error("❌ Cannot create account: Database connection failed.")
            return

        users = db["users"]

        if users.find_one({"username": username}):
            st.error("⚠️ Username already exists.")
            return

        if users.find_one({"email": email}):
            st.error("⚠️ Email already registered.")
            return

        # ------------------ CREATE USER ------------------
        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        users.insert_one({
            "full_name": full_name,
            "email": email,
            "username": username,
            "password": hashed_pw,
            "is_admin": False,
            "is_blocked": False,
            "history": []
        })

        st.success("🎉 Account created! Please log in.")
        st.session_state.page = "login"
        st.rerun()

    if st.button("⬅️ Go Back"):
        st.session_state.page = "main"
        st.rerun()

    st.markdown("---")
    st.markdown("Already have an account?")
    if st.button("🔐 Login Here"):
        st.session_state.page = "login"
        st.rerun()


def reset_password():
    st.title("🔑 Reset Password")
    username = st.text_input("Enter your username")
    new_password = st.text_input("Enter new password", type="password")
    confirm_password = st.text_input("Confirm new password", type="password")

    if st.button("✅ Reset Password"):
        if not username or not new_password or not confirm_password:
            st.warning("Please fill in all fields.")
        elif new_password != confirm_password:
            st.error("Passwords do not match!")
        else:
            db = get_connection()
            users = db["users"]
            user = users.find_one({"username": username})
            if not user:
                st.error("❌ Username not found.")
            else:
                hashed_pw = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
                users.update_one({"username": username}, {"$set": {"password": hashed_pw}})
                st.success("🎉 Password reset successfully! Please log in.")
                st.session_state.page = "login"
                st.rerun()

    if st.button("⬅️ Back to Login"):
        st.session_state.page = "login"
        st.rerun()


def login():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        # --- Required Field Check ---
        if not username or not password:
            st.error("⚠️ Please enter both username and password.")
            return

        db = get_connection()
        if db is None:
            st.error("❌ Cannot login: Database connection failed")
            return

        users = db["users"]
        user = users.find_one({"username": username})

        # --- Username Check ---
        if not user:
            st.error("❌ Username does not exist.")
            return

        # --- Blocked Account Check ---
        if user.get("is_blocked"):
            st.error("🚫 Your account has been blocked by the admin.")
            return

        # --- Password Check ---
        if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            st.error("❌ Incorrect password.")
            return

        # Successful Login
        st.session_state.authenticated = True
        st.session_state.username = username
        st.session_state.role = "admin" if user.get("is_admin") else "user"
        st.session_state.page = "main"

        # Load recent history
        load_recent_history_from_mongo(username, db)

        st.success("✅ Logged in successfully!")
        st.rerun()

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝 Sign Up"):
            st.session_state.page = "signup"
            st.rerun()

    with col2:
        if st.button("🔑 Forgot Password"):
            st.session_state.page = "reset_password"
            st.rerun()

def logout():
    st.session_state.clear()
    st.session_state.page = "login"
    st.rerun()

def profile_page():
    st.title("🧾 Profile")
    new_username = st.text_input("New Username", value=st.session_state.username)
    new_password = st.text_input("New Password", type="password")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📏 Update"):
            db = get_connection()
            users = db["users"]
            hashed_pw = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
            users.update_one({"username": st.session_state.username}, {"$set": {"username": new_username, "password": hashed_pw}})
            st.session_state.username = new_username
            st.success("Profile updated!")

    with col2:
        if st.button("🏠 Back to Home"):
            st.session_state.page = "main"
            st.rerun()

def estimate_total_time(duration_sec, model_size="medium"):
    speed = {"tiny": 1.0, "base": 1.5, "small": 2.0, "medium": 3.5, "large": 5.0}
    return int(duration_sec * speed.get(model_size, 2))

def format_eta(seconds):
    return f"{seconds // 60}m {seconds % 60}s" if seconds >= 60 else f"{seconds}s"

def save_subtitle_history(username, original_language, translated_language, filename):
    video_path = os.path.join("output", filename)
    srt_path = video_path.replace("_subtitled.mp4", ".srt")
    save_to_gridfs(username, video_path, srt_path)

def process_video():
    try:
        st.session_state.is_processing = True
        file = st.session_state.uploaded_file
        spoken_lang = st.session_state.spoken_lang
        target_lang = st.session_state.target_lang
        ext = os.path.splitext(file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(file.read())
            temp_path = temp_file.name

        duration = whisper.audio.load_audio(temp_path).shape[0] / whisper.audio.SAMPLE_RATE
        st.markdown(f"🕒 **Estimated time:** `{format_eta(estimate_total_time(duration, st.session_state.model_size))}`")

        progress_bar = st.progress(0)
        progress = 0

        model = get_or_load_model()
        progress_bar.progress(progress := 20)

        # transcription step
        transcription = model.transcribe(
            temp_path,
            language=None if spoken_lang == "Auto" else st.session_state.LANG_DICT[spoken_lang]
        )
        progress_bar.progress(progress := 45)

        segments = transcription['segments']
        translated_segments = []
        for seg in segments:
            try:
                translated = GoogleTranslator(
                    source='auto',
                    target=st.session_state.LANG_DICT[target_lang]
                ).translate(seg['text'])
            except Exception:
                translated = "[Translation Failed]"
            translated_segments.append({
                'start': seg['start'],
                'end': seg['end'],
                'text': translated
            })
        progress_bar.progress(progress := 70)

        base = os.path.splitext(os.path.basename(temp_path))[0]
        srt_path = f"output/{base}.srt"
        video_output_path = f"output/{base}_subtitled.mp4"
        font_path = get_font_for_text(translated_segments[0]['text'] if translated_segments else '')

        export_srt(translated_segments, srt_path)
        progress_bar.progress(progress := 85)

        render_subtitles_on_video(temp_path, translated_segments, video_output_path, font_path)
        progress_bar.progress(100)

        st.session_state.processing_done = True
        st.session_state.srt_file = srt_path
        st.session_state.video_file = video_output_path
        st.session_state.is_processing = False

        with open(srt_path, "rb") as f1, open(video_output_path, "rb") as f2:
            st.session_state.history.insert(0, {
                "video_name": os.path.basename(video_output_path),
                "srt_name": os.path.basename(srt_path),
                "video_data": f2.read(),
                "srt_data": f1.read()
            })
            st.session_state.history = st.session_state.history[:3]

        if not save_subtitle_history(
            st.session_state.username, spoken_lang, target_lang, os.path.basename(video_output_path)
        ):
            #st.warning("⚠️ Files processed successfully but could not be saved to database history.")
            pass

    except Exception as e:
        # 🔴 Friendly error instead of ugly traceback
        import traceback
        traceback.print_exc()  # logs full error in console (for developer)
        st.error("❌ Something went wrong while processing your video. Please try again with a different file.")
        st.session_state.is_processing = False


    with open(srt_path, "rb") as f1, open(video_output_path, "rb") as f2:
        st.session_state.history.insert(0, {
            "video_name": os.path.basename(video_output_path),
            "srt_name": os.path.basename(srt_path),
            "video_data": f2.read(),
            "srt_data": f1.read()
        })
        st.session_state.history = st.session_state.history[:3]

    # Save to database with error handling
    if not save_subtitle_history(st.session_state.username, spoken_lang, target_lang, os.path.basename(video_output_path)):
        #st.warning("⚠️ Files processed successfully but could not be saved to database history.")
        pass

def main_page():
    st.markdown("## 🎨 Subtitle Generator")
    st.write(f"👋 Welcome, **{st.session_state.username}**")
    st.markdown("---")

    
    with st.sidebar:
        if st.session_state.get("role") == "admin":
            admin_choice = st.radio("🛠️ Admin Menu", ["Main Page", "Admin Panel"], key="admin_menu_radio")

            if admin_choice == "Admin Panel" and st.session_state.page != "admin":
                st.session_state.page = "admin"
                st.rerun()

            elif admin_choice == "Main Page" and st.session_state.page != "main":
                st.session_state.page = "main"
                st.rerun()
        avatar_letter = st.session_state.username[:1].upper()
        if st.button(avatar_letter, key="avatar_btn"):
            if not st.session_state.is_processing:
                st.session_state.show_dropdown = not st.session_state.show_dropdown
        if st.session_state.show_dropdown:
            if st.button("🧾 Profile") and not st.session_state.is_processing:
                st.session_state.page = "profile"
                st.session_state.show_dropdown = False
                st.rerun()
            if st.button("🚪 Logout") and not st.session_state.is_processing:
                logout()

        st.markdown("## 📥 Recent Downloads")
        if st.session_state.history:
            exp = st.expander("⬇️ View Recent Files")
            with exp:
                for idx, item in enumerate(st.session_state.history):
                    st.markdown(f"**🎮 {item['video_name']}**", unsafe_allow_html=True)
                    st.download_button("📄 Subtitle", item['srt_data'], file_name=item['srt_name'], key=f"srt_{idx}")
                    st.download_button("🎮 Video", item['video_data'], file_name=item['video_name'], key=f"vid_{idx}")
        else:
            st.info("No recent files yet.")

        with st.expander("❓ How to Use"):
            st.markdown("""
1. Upload a video/audio  
2. Choose the spoken language  
3. Pick model 🐆/🐬/🐋  
4. Choose subtitle language  
5. Click ▶️ Start  
6. Download results
            """)
        
        st.markdown("### 👤 Account")
        if not st.session_state.authenticated:
            if st.button("🔐 Login"):
                st.session_state.page = "login"
                st.rerun()
            if st.button("📝 Signup"):
                st.session_state.page = "signup"
        else:
            st.markdown(f"✅ Logged in as `{st.session_state.username}`")

    st.markdown("### 📤 Upload Audio/Video")
    st.session_state.uploaded_file = st.file_uploader("Choose a file", type=["mp4", "wav", "m4a"])
    st.session_state.spoken_lang = st.selectbox("🗣️ Spoken Language", ["Auto"] + list(st.session_state.LANG_DICT.keys()))

    st.markdown("### ⚙️ Transcription Mode")
    model_map = {
        "tiny": ("🐆 Cheetah", "Fastest But Less Accurate"),
        "medium": ("🐬 Dolphin", "Balanced In Both Accuracy And Speed"),
        "large": ("🐋 Whale", "Most Accurate But Very Slow")
    }
    cols = st.columns(3)
    for i, (key, (emoji, label)) in enumerate(model_map.items()):
        with cols[i]:
            if st.button(f"{emoji} {label}", key=key):
                st.session_state.model_size = key
    selected_emoji, selected_label = model_map[st.session_state.model_size]
    st.markdown(f"<div style='margin-top:10px;padding:8px;border-radius:6px;background-color:#004225;color:white;font-weight:bold;display:inline-block;'>✅ Selected: {selected_label} Mode ({selected_emoji})</div>", unsafe_allow_html=True)

    st.markdown("### 🌐 Subtitle Language")
    st.session_state.target_lang = st.selectbox("Select subtitle output language:", list(st.session_state.LANG_DICT.keys()))

    if st.button("▶️ Start Processing"):
        if not st.session_state.authenticated:
            st.warning("Login required.")
            st.session_state.page = "login"
            st.rerun()
        elif not st.session_state.uploaded_file:
            st.warning("Please upload a file.")
        else:
            process_video()

    if st.session_state.processing_done:
        st.success("✅ Subtitles generated!")
        col1, col2 = st.columns(2)
        with col1:
            with open(st.session_state.srt_file, "rb") as srt:
                st.download_button("📄 Download Subtitle", srt, file_name=os.path.basename(st.session_state.srt_file))
        with col2:
            with open(st.session_state.video_file, "rb") as vid:
                st.download_button("🎮 Download Video", vid, file_name=os.path.basename(st.session_state.video_file))



def main():
    if st.session_state.authenticated:
        db = get_connection()
        user_data = db["users"].find_one({"username": st.session_state.username})
        st.session_state.role = "admin" if user_data.get("is_admin") else "user"

    if st.session_state.page == "admin":
        admin_panel()
        return
    if st.session_state.page == "login":
        login()
        return

    if st.session_state.page == "signup":
        signup()
        return

    if st.session_state.page == "profile":
        profile_page()
        return
    
    if st.session_state.page == "reset_password":
        reset_password()
        return


    # Load history if not already loaded
    if st.session_state.authenticated and not st.session_state.history:
        db = get_connection()
        load_recent_history_from_mongo(st.session_state.username, db)

    # Default to main page
    main_page()


if __name__ == "__main__":
    main()
    
