import streamlit as st
import pandas as pd
import os
import requests
from PIL import Image, ImageDraw
from io import BytesIO
import base64
#from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# ================= AUTO REFRESH =================
#st_autorefresh(interval=300000, key="refresh")

# ================= CONFIG =================
BACKEND_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Stress Dashboard", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# ================= CSS =================
st.markdown("""
<style>
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e3c72, #2a5298);
}
section[data-testid="stSidebar"] * {
    color: white !important;
}
.avatar-wrapper {
    position: relative;
    width:120px;
    height:120px;
    margin:20px auto;
}
.avatar-wrapper img {
    width:120px;
    height:120px;
    border-radius:50%;
    border:3px solid white;
    object-fit:cover;
}
.camera-icon {
    position:absolute;
    bottom:5px;
    right:5px;
    width:32px;
    height:32px;
    background:white;
    color:black;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:18px;
}
section[data-testid="stSidebar"] div[data-testid="stFileUploader"] {
    position:absolute !important;
    inset:0 !important;
    opacity:0 !important;
    z-index:10 !important;
    cursor:pointer;
}
section[data-testid="stSidebar"] div[data-testid="stFileUploader"] > div {
    display:none !important;
}
</style>
""", unsafe_allow_html=True)

# ================= SESSION =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = ""
    st.session_state.role = ""

# ================= API =================
@st.cache_data(ttl=300)
def fetch_user_data(user_id):
    try:
        r = requests.get(f"{BACKEND_URL}/dashboard/user/{user_id}", timeout=5)
        if r.status_code == 200:
            return pd.DataFrame(r.json().get("data", []))
    except:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_hr_data():
    try:
        r = requests.get(f"{BACKEND_URL}/dashboard/hr", timeout=5)
        if r.status_code == 200:
            return pd.DataFrame(r.json().get("data", []))
    except:
        pass
    return pd.DataFrame()

# ================= LOGIN =================
USERS = {
    "ADMIN": {"password": "emp123", "role": "employee"},
    "HR": {"password": "admin123", "role": "hr"},
}

def login_page():
    st.title("🔐 Login")

    u = st.text_input("Username").upper().strip()
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        st.cache_data.clear()

        if u in USERS and USERS[u]["password"] == p:
            st.session_state.logged_in = True
            st.session_state.user_id = u
            st.session_state.role = USERS[u]["role"]
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

if not st.session_state.logged_in:
    login_page()
    st.stop()

# ================= AVATAR =================
def generate_default_avatar(letter="U"):
    img = Image.new("RGB", (200, 200), "#4e73df")
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, 200, 200), fill="#4e73df")
    draw.text((80, 55), letter, fill="white")
    return img

def img_to_b64(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

user = st.session_state.user_id or "U"

avatar_path = os.path.join(ASSETS_DIR, f"{user}_avatar.png")

avatar_img = (
    Image.open(avatar_path)
    if os.path.exists(avatar_path)
    else generate_default_avatar(user[0])
)

# ================= SIDEBAR =================
with st.sidebar:

    uploaded = st.file_uploader(
        "",
        type=["png", "jpg", "jpeg"],
        key="avatar_upload",
        label_visibility="collapsed"
    )

    st.markdown(
        f"""
        <div class="avatar-wrapper">
            <img src="data:image/png;base64,{img_to_b64(avatar_img)}">
            <div class="camera-icon">📷</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if uploaded:
        Image.open(uploaded).resize((200, 200)).save(avatar_path)
        st.success("✅ Avatar updated")
        st.rerun()

    st.markdown(f"### {user}")
    st.markdown(f"🧑‍💼 {st.session_state.role.upper()}")

    if st.session_state.role == "employee":
        page = st.radio("📂 Navigation", ["Dashboard", "History"])
    else:
        page = st.radio("📂 Navigation", ["HR Dashboard"])

    st.markdown("---")
    st.markdown("### ⚙ System Status")

    st.success("🟢 Agent Running")
    st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = ""
        st.session_state.role = ""
        st.cache_data.clear()
        st.rerun()

# ================= LOAD DATA =================
if st.session_state.role == "employee":
    df = fetch_user_data(user)
else:
    df = fetch_hr_data()

# ================= USER DASHBOARD =================
if page == "Dashboard":

    st.title("📊 User Stress Dashboard")

    if df.empty:
        st.warning("⚠️ No stress data yet.")
        st.stop()

    latest = df.iloc[0]

    c1, c2, c3 = st.columns(3)

    c1.metric("User", latest.get("user_id", user))
    c2.metric("Backspace", int(latest.get("backspace_count", 0)))

    if "STRESS" in str(latest.get("prediction", "")):
        c3.error("🔴 STRESS")
    else:
        c3.success("🟢 NORMAL")

    m1, m2 = st.columns(2)
    m1.metric("Avg Dwell", round(float(latest.get("avg_dwell_time", 0)), 3))
    m2.metric("Avg Flight", round(float(latest.get("avg_flight_time", 0)), 3))

    recent = df.head(20).copy()
    recent["stress_flag"] = recent["prediction"].astype(str).str.contains("STRESS")
    recent["timestamp"] = pd.to_datetime(recent["timestamp"], errors="coerce")
    recent = recent.dropna(subset=["timestamp"]).set_index("timestamp")

    if not recent.empty:
        st.line_chart(recent["stress_flag"],height=400)

# ================= HISTORY =================
if page == "History":
    st.title("📜 History")
    st.dataframe(df, use_container_width=True)

# ================= HR DASHBOARD =================
if page == "HR Dashboard":

    st.title("👔 HR Dashboard")

    if df.empty:
        st.warning("⚠️ No records yet.")
        st.stop()

    c1, c2 = st.columns(2)

    c1.metric("Total Records", len(df))

    c2.metric(
        "Stressed Employees",
        df[df["prediction"].astype(str).str.contains("STRESS")]["user_id"].nunique(),
    )

    summary = (
        df.groupby("user_id")["prediction"]
        .apply(lambda x: x.astype(str).str.contains("STRESS").sum())
        .reset_index(name="Stress Count")
    )

    st.subheader("📊 Stress Summary")
    st.dataframe(summary, use_container_width=True)
