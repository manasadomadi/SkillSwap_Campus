import streamlit as st
import streamlit.components.v1 as components
import base64
import os
import json
from datetime import datetime
from urllib.parse import quote
from sqlalchemy.orm import joinedload

from services.database import SessionLocal, init_db
from models.user import User, hash_password, verify_password
from models.skill import Skill, UserSkill
from models.swap import SwapRequest
from models.message import Message
from models.notification import Notification
from services.matching import calculate_match, get_common_skills
from services.ai import generate_match_explanation
from utils.helpers import normalize_email, normalize_skill, valid_email


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="SkillSwap Campus",
    page_icon="🔄",
    layout="wide"
)

init_db()


# ============================================================
# NAVY BLUE GRADIENT THEME
# ============================================================

st.markdown(
    """
    <style>
    /* Main application background */
    .stApp {
        background: linear-gradient(135deg, #020617 0%, #071a3d 38%, #0b2d5c 72%, #123f7a 100%);
        color: #f8fafc;
    }

    /* Main content readability */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #020617 0%, #071a3d 55%, #0b2d5c 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.18);
    }

    section[data-testid="stSidebar"] > div {
        background: transparent;
    }

    /* Headings */
    h1, h2, h3, h4 {
        color: #ffffff !important;
    }

    /* Normal text */
    p, label, .stMarkdown, .stText, .stCaption {
        color: #e2e8f0;
    }

    /* Cards / bordered containers */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(145deg, rgba(15, 35, 72, 0.88), rgba(7, 26, 61, 0.82));
        border: 1px solid rgba(96, 165, 250, 0.22);
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.22);
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #0b2d5c, #174ea6);
        color: white;
        border: 1px solid rgba(147, 197, 253, 0.35);
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #174ea6, #2563eb);
        border-color: #60a5fa;
        color: white;
        transform: translateY(-1px);
    }

    /* Primary buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #123f7a, #2563eb);
        border-color: #60a5fa;
    }

    /* Inputs - dark background = white text */
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    div[data-baseweb="select"] > div {
        background: rgba(2, 15, 38, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 10px;
        color: #ffffff;
    }

    input, textarea {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        caret-color: #ffffff !important;
    }

    input::placeholder, textarea::placeholder {
        color: #cbd5e1 !important;
        -webkit-text-fill-color: #cbd5e1 !important;
    }

    /* Registration form: white field background = black text */
    div[data-testid="stForm"] input,
    div[data-testid="stForm"] textarea,
    div[data-testid="stForm"] [data-baseweb="select"] *,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        caret-color: #000000 !important;
    }

    /* If a registration field uses a dark background, switch its text back to white */
    div[data-testid="stForm"] input[style*="background-color: rgb(2, 15, 38)"],
    div[data-testid="stForm"] textarea[style*="background-color: rgb(2, 15, 38)"] {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        caret-color: #ffffff !important;
    }

    /* Metrics */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(11, 45, 92, 0.85), rgba(18, 63, 122, 0.72));
        border: 1px solid rgba(96, 165, 250, 0.22);
        padding: 14px;
        border-radius: 14px;
    }

    /* Dividers */
    hr {
        border-color: rgba(148, 163, 184, 0.20);
    }

    /* Links */
    a {
        color: #93c5fd !important;
    }

    /* Alerts */
    div[data-testid="stAlert"] {
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "page" not in st.session_state:
    st.session_state.page = "Home"

if "chat_partner_id" not in st.session_state:
    st.session_state.chat_partner_id = None


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_current_user():
    """
    Returns:
        user, db_session

    The session remains open while the page is using
    SQLAlchemy relationships.
    """
    if not st.session_state.logged_in:
        return None, None

    db = SessionLocal()

    user = (
        db.query(User)
        .filter(User.id == st.session_state.user_id)
        .first()
    )

    if user is None:
        db.close()
        st.session_state.logged_in = False
        st.session_state.user_id = None
        return None, None

    return user, db


def get_user_skills(user_id, db):
    """
    IMPORTANT:
    This function returns ONLY normal Python strings.

    It NEVER returns UserSkill objects.
    """

    rows = (
        db.query(UserSkill)
        .options(joinedload(UserSkill.skill))
        .filter(UserSkill.user_id == user_id)
        .all()
    )

    teaching = []
    learning = []

    for row in rows:

        # Ignore broken database rows
        if row.skill is None:
            continue

        skill_name = str(row.skill.name).strip().title()

        if row.skill_type == "TEACH":
            teaching.append(skill_name)

        elif row.skill_type == "LEARN":
            learning.append(skill_name)

    return teaching, learning


def get_all_user_skills(user_id, db):
    """
    Returns a list of dictionaries containing only
    normal Python values.
    """

    rows = (
        db.query(UserSkill)
        .options(joinedload(UserSkill.skill))
        .filter(UserSkill.user_id == user_id)
        .all()
    )

    result = []

    for row in rows:

        if row.skill is None:
            continue

        result.append({
            "id": row.id,
            "skill_id": row.skill_id,
            "name": str(row.skill.name).strip().title(),
            "type": row.skill_type
        })

    return result


def get_skill_or_create(db, skill_name):
    """
    Find an existing skill or create a new one.
    """

    normalized = normalize_skill(skill_name)

    skill = (
        db.query(Skill)
        .filter(Skill.name == normalized)
        .first()
    )

    if skill is None:
        skill = Skill(
            name=normalized,
            category="Other"
        )

        db.add(skill)
        db.commit()
        db.refresh(skill)

    return skill


# ============================================================
# COMMUNICATION HELPERS
# ============================================================

def get_unread_notification_count(user_id, db):
    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
        .count()
    )


def get_unread_message_count(user_id, db):
    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.notification_type == "MESSAGE",
            Notification.is_read == False
        )
        .count()
    )


def create_notification(
    db,
    user_id,
    notification_type,
    title,
    body,
    related_id=None
):
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        related_id=related_id,
        is_read=False
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def mark_notification_read(notification_id, db):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .first()
    )

    if notification:
        notification.is_read = True
        db.commit()


def get_accepted_partners(user_id, db):
    """
    Returns students with whom the current user has an
    accepted swap request.
    """
    requests = (
        db.query(SwapRequest)
        .filter(
            SwapRequest.status == "Accepted",
            (
                (SwapRequest.sender_id == user_id)
                | (SwapRequest.receiver_id == user_id)
            )
        )
        .order_by(SwapRequest.id.desc())
        .all()
    )

    partners = {}
    for request in requests:
        partner_id = (
            request.receiver_id
            if request.sender_id == user_id
            else request.sender_id
        )

        if partner_id not in partners:
            partner = db.query(User).filter(
                User.id == partner_id
            ).first()

            if partner:
                partners[partner_id] = partner

    return list(partners.values())


def are_users_connected(user_id, other_user_id, db):
    """
    Chat/call access is available only after a swap request
    between the two users has been accepted.
    """
    return (
        db.query(SwapRequest)
        .filter(
            SwapRequest.status == "Accepted",
            (
                (
                    (SwapRequest.sender_id == user_id)
                    & (SwapRequest.receiver_id == other_user_id)
                )
                |
                (
                    (SwapRequest.sender_id == other_user_id)
                    & (SwapRequest.receiver_id == user_id)
                )
            )
        )
        .first()
        is not None
    )


def encode_voice_message(audio_bytes, mime_type):
    encoded = base64.b64encode(audio_bytes).decode("ascii")
    return f"VOICE|{mime_type}|{encoded}"


def decode_voice_message(content):
    if not content or not content.startswith("VOICE|"):
        return None

    try:
        _, mime_type, encoded = content.split("|", 2)
        return base64.b64decode(encoded), mime_type
    except Exception:
        return None


def call_server_url():
    """
    Change CALL_SERVER_URL in config.py when deploying.
    """
    try:
        from config import CALL_SERVER_URL
        return CALL_SERVER_URL.rstrip("/")
    except Exception:
        return "http://localhost:8000"


def call_url(room_id, mode):
    return (
        f"{call_server_url()}/call/"
        f"{quote(str(room_id), safe='')}"
        f"?mode={quote(mode)}"
    )


def render_call_buttons(user_id, partner_id):
    room_id = "-".join(
        str(x) for x in sorted([int(user_id), int(partner_id)])
    )

    voice_url = call_url(room_id, "audio")
    video_url = call_url(room_id, "video")

    st.markdown(
        f"""
        <div style="
            display:flex;
            gap:12px;
            flex-wrap:wrap;
            margin:10px 0 18px 0;
        ">
            <a href="{voice_url}" target="_blank"
               style="
                 text-decoration:none;
                 padding:10px 18px;
                 border-radius:10px;
                 background:#173b78;
                 color:white;
                 font-weight:600;
               ">
               📞 Voice Call
            </a>
            <a href="{video_url}" target="_blank"
               style="
                 text-decoration:none;
                 padding:10px 18px;
                 border-radius:10px;
                 background:#2456a6;
                 color:white;
                 font-weight:600;
               ">
               📹 Video Call
            </a>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# NOTIFICATIONS PAGE
# ============================================================

def notifications_page():
    user, db = get_current_user()

    if user is None:
        return

    try:
        st.title("🔔 Notifications")

        notifications = (
            db.query(Notification)
            .filter(Notification.user_id == user.id)
            .order_by(Notification.id.desc())
            .limit(50)
            .all()
        )

        pending_requests = (
            db.query(SwapRequest)
            .filter(
                SwapRequest.receiver_id == user.id,
                SwapRequest.status == "Pending"
            )
            .order_by(SwapRequest.id.desc())
            .all()
        )

        if pending_requests:
            st.subheader("🤝 Swap Requests")

            for request in pending_requests:
                sender = (
                    db.query(User)
                    .filter(User.id == request.sender_id)
                    .first()
                )

                if sender is None:
                    continue

                with st.container(border=True):
                    st.markdown(
                        f"### 📨 {sender.name} sent you a swap request"
                    )

                    if sender.college:
                        st.caption(f"🏫 {sender.college}")

                    st.write(
                        f"**They will teach:** {request.skill_offered}"
                    )
                    st.write(
                        f"**They want to learn:** {request.skill_requested}"
                    )

                    if request.message:
                        st.info(request.message)

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button(
                            "✅ Accept",
                            key=f"accept_{request.id}",
                            type="primary",
                            use_container_width=True
                        ):
                            request.status = "Accepted"

                            request_notifications = (
                                db.query(Notification)
                                .filter(
                                    Notification.user_id == user.id,
                                    Notification.notification_type == "SWAP_REQUEST",
                                    Notification.related_id == request.id
                                )
                                .all()
                            )

                            for item in request_notifications:
                                item.is_read = True

                            create_notification(
                                db,
                                request.sender_id,
                                "REQUEST_ACCEPTED",
                                "Swap request accepted",
                                (
                                    f"{user.name} accepted your swap "
                                    "request. You can now chat."
                                ),
                                request.id
                            )

                            db.commit()

                            st.success(
                                f"You are now connected with {sender.name}!"
                            )
                            st.rerun()

                    with col2:
                        if st.button(
                            "❌ Reject",
                            key=f"reject_{request.id}",
                            use_container_width=True
                        ):
                            request.status = "Rejected"

                            request_notifications = (
                                db.query(Notification)
                                .filter(
                                    Notification.user_id == user.id,
                                    Notification.notification_type == "SWAP_REQUEST",
                                    Notification.related_id == request.id
                                )
                                .all()
                            )

                            for item in request_notifications:
                                item.is_read = True

                            create_notification(
                                db,
                                request.sender_id,
                                "REQUEST_REJECTED",
                                "Swap request rejected",
                                f"{user.name} rejected your swap request.",
                                request.id
                            )

                            db.commit()

                            st.info("Swap request rejected.")
                            st.rerun()

        else:
            st.success("You have no pending swap requests.")

        st.divider()
        st.subheader("🔔 Recent Notifications")

        if not notifications:
            st.info("No notifications yet.")
            return

        for notification in notifications:
            if not notification.is_read:
                prefix = "🔵"
            else:
                prefix = "⚪"

            with st.container(border=True):
                col1, col2 = st.columns([5, 1])

                with col1:
                    st.markdown(
                        f"**{prefix} {notification.title}**"
                    )
                    st.write(notification.body)

                with col2:
                    if not notification.is_read:
                        if st.button(
                            "Mark read",
                            key=f"read_{notification.id}"
                        ):
                            mark_notification_read(
                                notification.id,
                                db
                            )
                            st.rerun()

    finally:
        db.close()


# ============================================================
# MESSAGES / CHAT PAGE
# ============================================================

def messages_page():
    user, db = get_current_user()

    if user is None:
        return

    try:
        st.title("💬 Messages")
        st.caption(
            "Private messaging is available after a swap request "
            "has been accepted."
        )

        partners = get_accepted_partners(user.id, db)

        if not partners:
            st.info(
                "No active chats yet. Accept a swap request to start "
                "chatting with another student."
            )
            return

        partner_options = {
            f"{partner.name} — {partner.college or 'Student'}": partner.id
            for partner in partners
        }

        labels = list(partner_options.keys())

        default_index = 0

        if st.session_state.chat_partner_id in partner_options.values():
            default_index = list(
                partner_options.values()
            ).index(st.session_state.chat_partner_id)

        selected_label = st.selectbox(
            "Select a conversation",
            labels,
            index=default_index
        )

        partner_id = partner_options[selected_label]
        st.session_state.chat_partner_id = partner_id

        partner = (
            db.query(User)
            .filter(User.id == partner_id)
            .first()
        )

        if partner is None:
            st.error("Student not found.")
            return

        st.divider()

        header_col1, header_col2 = st.columns([3, 2])

        with header_col1:
            st.subheader(f"💬 {partner.name}")

            if partner.course or partner.year:
                st.caption(
                    f"{partner.course or ''}"
                    f"{' • ' if partner.course and partner.year else ''}"
                    f"{partner.year or ''}"
                )

        with header_col2:
            render_call_buttons(user.id, partner.id)

        # Mark messages from this partner as read by removing their
        # unread-message notifications.
        unread_notifications = (
            db.query(Notification)
            .filter(
                Notification.user_id == user.id,
                Notification.notification_type == "MESSAGE",
                Notification.is_read == False
            )
            .all()
        )

        for notification in unread_notifications:
            if notification.related_id:
                message = (
                    db.query(Message)
                    .filter(Message.id == notification.related_id)
                    .first()
                )

                if message and message.sender_id == partner.id:
                    notification.is_read = True

        db.commit()

        messages = (
            db.query(Message)
            .filter(
                (
                    (Message.sender_id == user.id)
                    & (Message.receiver_id == partner.id)
                )
                |
                (
                    (Message.sender_id == partner.id)
                    & (Message.receiver_id == user.id)
                )
            )
            .order_by(Message.created_at.asc())
            .all()
        )

        # Chat area
        chat_box = st.container(height=430, border=True)

        with chat_box:
            if not messages:
                st.info(
                    "No messages yet. Say hello and start your skill exchange!"
                )

            for message in messages:
                is_me = message.sender_id == user.id

                if is_me:
                    label = "You"
                else:
                    label = partner.name

                voice = decode_voice_message(message.content)

                with st.chat_message(
                    "user" if is_me else "assistant"
                ):
                    st.markdown(
                        f"**{label}**  \n"
                        f"<small>{message.created_at.strftime('%d %b %Y, %I:%M %p')}</small>",
                        unsafe_allow_html=True
                    )

                    if voice:
                        audio_bytes, mime_type = voice
                        st.audio(
                            audio_bytes,
                            format=mime_type
                        )
                        st.caption("🎙️ Voice message")
                    else:
                        st.write(message.content)

        st.divider()

        st.subheader("✉️ Send a Message")

        text_message = st.text_area(
            "Text message",
            placeholder="Type your message...",
            key=f"text_message_{partner.id}",
            height=90
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "📨 Send Text",
                type="primary",
                use_container_width=True
            ):
                text_message = text_message.strip()

                if not text_message:
                    st.warning("Please type a message.")
                else:
                    new_message = Message(
                        sender_id=user.id,
                        receiver_id=partner.id,
                        content=text_message
                    )

                    db.add(new_message)
                    db.commit()
                    db.refresh(new_message)

                    create_notification(
                        db,
                        partner.id,
                        "MESSAGE",
                        f"💬 New message from {user.name}",
                        text_message[:150],
                        new_message.id
                    )

                    db.commit()
                    st.rerun()

        with col2:
            st.write("🎙️ **Voice Message**")

            if hasattr(st, "audio_input"):
                voice_recording = st.audio_input(
                    "Record your voice",
                    key=f"voice_{partner.id}"
                )

                if voice_recording is not None:
                    if st.button(
                        "🎙️ Send Voice Message",
                        use_container_width=True,
                        key=f"send_voice_{partner.id}"
                    ):
                        audio_bytes = voice_recording.getvalue()

                        voice_content = encode_voice_message(
                            audio_bytes,
                            voice_recording.type
                            or "audio/wav"
                        )

                        new_message = Message(
                            sender_id=user.id,
                            receiver_id=partner.id,
                            content=voice_content
                        )

                        db.add(new_message)
                        db.commit()
                        db.refresh(new_message)

                        create_notification(
                            db,
                            partner.id,
                            "MESSAGE",
                            f"🎙️ Voice message from {user.name}",
                            "You received a new voice message.",
                            new_message.id
                        )

                        db.commit()
                        st.rerun()
            else:
                st.warning(
                    "Voice recording requires Streamlit 1.40 or newer."
                )

        st.caption(
            "📞 Voice and 📹 video calls open in a secure browser call page. "
            "Your browser will ask for microphone/camera permission."
        )

    finally:
        db.close()


# ============================================================
# HOME PAGE
# ============================================================

def home_page():

    st.title("🔄 SkillSwap Campus")

    st.subheader("Learn. Teach. Connect.")

    st.write(
        "SkillSwap Campus is a peer-to-peer skill exchange "
        "platform where students can teach what they know "
        "and learn what they want."
    )

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🎓 Learn")
        st.write(
            "Find students who can teach you the skills "
            "you want to learn."
        )

    with col2:
        st.markdown("### 🧑‍🏫 Teach")
        st.write(
            "Share your knowledge and help other students "
            "develop new skills."
        )

    with col3:
        st.markdown("### 🤝 Connect")
        st.write(
            "Find compatible students using smart skill "
            "matching."
        )

    st.divider()

    if not st.session_state.logged_in:

        st.info(
            "Please register or login to start exchanging skills."
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "📝 Create Account",
                use_container_width=True
            ):
                st.session_state.page = "Register"
                st.rerun()

        with col2:
            if st.button(
                "🔐 Login",
                use_container_width=True
            ):
                st.session_state.page = "Login"
                st.rerun()


# ============================================================
# REGISTER PAGE
# ============================================================

def register_page():

    st.title("📝 Create Account")

    st.write("Create your SkillSwap Campus account.")

    name = st.text_input("Full Name")

    email = st.text_input("Email")

    password = st.text_input(
        "Password",
        type="password"
    )

    confirm_password = st.text_input(
        "Confirm Password",
        type="password"
    )

    college = st.text_input("College")

    course = st.text_input("Course")

    year = st.selectbox(
        "Year",
        [
            "1st Year",
            "2nd Year",
            "3rd Year",
            "4th Year"
        ]
    )

    bio = st.text_area("Short Bio")

    if st.button(
        "Create Account",
        type="primary",
        use_container_width=True
    ):

        name = name.strip()
        email = normalize_email(email)

        if not name:
            st.error("Please enter your name.")
            return

        if not valid_email(email):
            st.error("Please enter a valid email address.")
            return

        if len(password) < 6:
            st.error(
                "Password must contain at least 6 characters."
            )
            return

        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        db = SessionLocal()

        try:

            existing_user = (
                db.query(User)
                .filter(User.email == email)
                .first()
            )

            if existing_user:
                st.error(
                    "An account with this email already exists."
                )
                return

            new_user = User(
                name=name,
                email=email,
                password_hash=hash_password(password),
                college=college.strip(),
                course=course.strip(),
                year=year,
                bio=bio.strip()
            )

            db.add(new_user)
            db.commit()

            st.success(
                "Account created successfully! "
                "You can now login."
            )

        finally:
            db.close()


# ============================================================
# LOGIN PAGE
# ============================================================

def login_page():

    st.title("🔐 Login")

    email = st.text_input("Email")

    password = st.text_input(
        "Password",
        type="password"
    )

    if st.button(
        "Login",
        type="primary",
        use_container_width=True
    ):

        email = normalize_email(email)

        db = SessionLocal()

        try:

            user = (
                db.query(User)
                .filter(User.email == email)
                .first()
            )

            if user and verify_password(
                password,
                user.password_hash
            ):

                st.session_state.logged_in = True
                st.session_state.user_id = user.id
                st.session_state.page = "Dashboard"

                st.success("Login successful!")

                st.rerun()

            else:
                st.error(
                    "Invalid email or password."
                )

        finally:
            db.close()


# ============================================================
# PROFILE PAGE
# ============================================================

def profile_page():

    user, db = get_current_user()

    if user is None:
        return

    try:

        st.title("👤 My Profile")

        st.subheader(user.name)

        st.write(f"📧 **Email:** {user.email}")

        if user.college:
            st.write(
                f"🏫 **College:** {user.college}"
            )

        if user.course:
            st.write(
                f"📚 **Course:** {user.course}"
            )

        if user.year:
            st.write(
                f"🎓 **Year:** {user.year}"
            )

        st.divider()

        st.subheader("About Me")

        if user.bio:
            st.write(user.bio)
        else:
            st.info("No bio added yet.")

        st.divider()

        teaching, learning = get_user_skills(
            user.id,
            db
        )

        col1, col2 = st.columns(2)

        with col1:

            st.markdown("### 🧑‍🏫 Skills I Teach")

            if teaching:
                for skill in teaching:
                    st.write(f"• {skill}")
            else:
                st.info("No teaching skills added.")

        with col2:

            st.markdown("### 📖 Skills I Want to Learn")

            if learning:
                for skill in learning:
                    st.write(f"• {skill}")
            else:
                st.info("No learning skills added.")

    finally:
        db.close()


# ============================================================
# MY SKILLS PAGE
# ============================================================

def skills_page():

    user, db = get_current_user()

    if user is None:
        return

    try:

        st.title("🛠️ My Skills")

        st.write(
            "Add skills you can teach and skills you want to learn."
        )

        # ----------------------------------------------------
        # SHOW CURRENT SKILLS
        # ----------------------------------------------------

        teaching, learning = get_user_skills(
            user.id,
            db
        )

        col1, col2 = st.columns(2)

        with col1:

            st.subheader("🧑‍🏫 Skills I Teach")

            if teaching:

                for skill in teaching:
                    st.write(f"• {skill}")

            else:
                st.info("No teaching skills yet.")

        with col2:

            st.subheader("📖 Skills I Want to Learn")

            if learning:

                for skill in learning:
                    st.write(f"• {skill}")

            else:
                st.info("No learning skills yet.")

        st.divider()

        # ----------------------------------------------------
        # ADD SKILL
        # ----------------------------------------------------

        st.subheader("➕ Add a Skill")

        skill_name = st.text_input(
            "Skill Name",
            placeholder="Example: Python"
        )

        skill_type = st.radio(
            "I want to:",
            [
                "Teach",
                "Learn"
            ],
            horizontal=True
        )

        if st.button(
            "Add Skill",
            type="primary"
        ):

            skill_name = normalize_skill(skill_name)

            if not skill_name:
                st.error("Please enter a skill.")
                return

            existing_skill = (
                db.query(Skill)
                .filter(Skill.name == skill_name)
                .first()
            )

            if existing_skill is None:

                existing_skill = Skill(
                    name=skill_name,
                    category="Other"
                )

                db.add(existing_skill)
                db.commit()
                db.refresh(existing_skill)

            skill_type_db = (
                "TEACH"
                if skill_type == "Teach"
                else "LEARN"
            )

            already_exists = (
                db.query(UserSkill)
                .filter(
                    UserSkill.user_id == user.id,
                    UserSkill.skill_id == existing_skill.id,
                    UserSkill.skill_type == skill_type_db
                )
                .first()
            )

            if already_exists:

                st.warning(
                    "You already have this skill."
                )

            else:

                new_user_skill = UserSkill(
                    user_id=user.id,
                    skill_id=existing_skill.id,
                    skill_type=skill_type_db
                )

                db.add(new_user_skill)
                db.commit()

                st.success(
                    f"{skill_name.title()} added successfully!"
                )

                st.rerun()

        st.divider()

        # ----------------------------------------------------
        # REMOVE SKILL
        # ----------------------------------------------------

        st.subheader("🗑️ Remove a Skill")

        all_skills = get_all_user_skills(
            user.id,
            db
        )

        if all_skills:

            skill_options = []

            for item in all_skills:

                label = (
                    f"{item['name']} "
                    f"({'Teaching' if item['type'] == 'TEACH' else 'Learning'})"
                )

                skill_options.append(
                    (
                        label,
                        item["id"]
                    )
                )

            selected_label = st.selectbox(
                "Select a skill to remove",
                [item[0] for item in skill_options]
            )

            selected_id = None

            for label, row_id in skill_options:

                if label == selected_label:
                    selected_id = row_id
                    break

            if st.button("Remove Selected Skill"):

                row = (
                    db.query(UserSkill)
                    .filter(
                        UserSkill.id == selected_id,
                        UserSkill.user_id == user.id
                    )
                    .first()
                )

                if row:

                    db.delete(row)
                    db.commit()

                    st.success(
                        "Skill removed successfully."
                    )

                    st.rerun()

        else:

            st.info(
                "You don't have any skills to remove."
            )

    finally:
        db.close()


# ============================================================
# SMART MATCHES PAGE
# ============================================================

def matches_page():

    user, db = get_current_user()

    if user is None:
        return

    try:

        st.title("🤝 Smart Matches")

        st.write(
            "Find students whose skills match what you want to learn."
        )

        # ----------------------------------------------------
        # CURRENT USER SKILLS
        # ----------------------------------------------------

        teaching, learning = get_user_skills(
            user.id,
            db
        )

        col1, col2 = st.columns(2)

        with col1:

            st.markdown("### 🧑‍🏫 You Teach")

            if teaching:

                for skill in teaching:
                    st.write(f"• {skill}")

            else:
                st.info("Add some teaching skills.")

        with col2:

            st.markdown("### 📖 You Want to Learn")

            if learning:

                for skill in learning:
                    st.write(f"• {skill}")

            else:
                st.info("Add some learning skills.")

        if not teaching or not learning:

            st.warning(
                "Add at least one skill to teach and one skill "
                "to learn to get meaningful matches."
            )

            return

        st.divider()

        # ----------------------------------------------------
        # FIND OTHER USERS
        # ----------------------------------------------------

        other_users = (
            db.query(User)
            .filter(User.id != user.id)
            .all()
        )

        matches = []

        for other_user in other_users:

            score = calculate_match(
                user,
                other_user
            )

            if score > 0:

                common_skills = get_common_skills(
                    user,
                    other_user
                )

                matches.append(
                    (
                        score,
                        other_user,
                        common_skills
                    )
                )

        matches.sort(
            key=lambda x: x[0],
            reverse=True
        )

        # ----------------------------------------------------
        # DISPLAY MATCHES
        # ----------------------------------------------------

        if not matches:

            st.info(
                "No matching students found yet. "
                "Try adding more skills."
            )

            return

        st.subheader(
            f"🎯 {len(matches)} Match(es) Found"
        )

        for score, other_user, common_skills in matches:

            with st.container(border=True):

                col1, col2 = st.columns(
                    [3, 1]
                )

                with col1:

                    st.markdown(
                        f"### 👤 {other_user.name}"
                    )

                    if other_user.college:
                        st.write(
                            f"🏫 {other_user.college}"
                        )

                    if other_user.course:
                        st.write(
                            f"📚 {other_user.course}"
                        )

                    if common_skills:

                        st.write(
                            "🔗 **Common Skills:** "
                            + ", ".join(common_skills)
                        )

                    explanation = (
                        generate_match_explanation(
                            user.name,
                            other_user.name,
                            common_skills
                        )
                    )

                    st.caption(explanation)

                with col2:

                    st.metric(
                        "Match",
                        f"{score}%"
                    )

    finally:
        db.close()


# ============================================================
# SEND SWAP REQUEST PAGE
# ============================================================

def send_request_page():

    user, db = get_current_user()

    if user is None:
        return

    try:

        st.title("🤝 Send Swap Request")

        users = (
            db.query(User)
            .filter(User.id != user.id)
            .all()
        )

        if not users:

            st.info(
                "There are no other students registered yet."
            )

            return

        user_options = {}

        for other_user in users:

            label = (
                f"{other_user.name}"
            )

            if other_user.college:
                label += f" — {other_user.college}"

            user_options[label] = other_user.id

        selected_user_label = st.selectbox(
            "Select Student",
            list(user_options.keys())
        )

        receiver_id = user_options[
            selected_user_label
        ]

        teaching, learning = get_user_skills(
            user.id,
            db
        )

        receiver = (
            db.query(User)
            .filter(User.id == receiver_id)
            .first()
        )

        receiver_teaching, receiver_learning = (
            get_user_skills(
                receiver.id,
                db
            )
        )

        st.divider()

        st.subheader("Your Skills")

        col1, col2 = st.columns(2)

        with col1:

            st.write("🧑‍🏫 You can teach:")

            if teaching:
                for skill in teaching:
                    st.write(f"• {skill}")
            else:
                st.info("No teaching skills.")

        with col2:

            st.write("📖 You want to learn:")

            if learning:
                for skill in learning:
                    st.write(f"• {skill}")
            else:
                st.info("No learning skills.")

        st.divider()

        skill_offered = st.selectbox(
            "Skill You Will Teach",
            teaching if teaching else ["No teaching skills"]
        )

        skill_requested = st.selectbox(
            "Skill You Want to Learn",
            receiver_teaching
            if receiver_teaching
            else ["No teaching skills available"]
        )

        message = st.text_area(
            "Message",
            placeholder=(
                "Hi! I would like to exchange skills with you..."
            )
        )

        if st.button(
            "📨 Send Request",
            type="primary",
            use_container_width=True
        ):

            if not teaching:
                st.error(
                    "Please add a skill you can teach first."
                )
                return

            if not receiver_teaching:
                st.error(
                    "This student has no teaching skills yet."
                )
                return

            new_request = SwapRequest(
                sender_id=user.id,
                receiver_id=receiver.id,
                skill_offered=skill_offered,
                skill_requested=skill_requested,
                message=message.strip(),
                status="Pending"
            )

            db.add(new_request)
            db.commit()
            db.refresh(new_request)

            create_notification(
                db,
                receiver.id,
                "SWAP_REQUEST",
                f"🤝 New swap request from {user.name}",
                (
                    f"{user.name} wants to teach you "
                    f"{skill_offered} and learn {skill_requested}."
                ),
                new_request.id
            )

            db.commit()

            st.success(
                "Swap request sent successfully! "
                "The student has been notified."
            )

    finally:
        db.close()


# ============================================================
# DASHBOARD PAGE
# ============================================================

def dashboard_page():

    user, db = get_current_user()

    if user is None:
        return

    try:

        st.title("📊 Dashboard")

        st.markdown(
            f"### Welcome back, {user.name}! 👋"
        )

        # ----------------------------------------------------
        # GET SKILLS AS STRINGS ONLY
        # ----------------------------------------------------

        teaching, learning = get_user_skills(
            user.id,
            db
        )

        # ----------------------------------------------------
        # REQUEST COUNTS
        # ----------------------------------------------------

        sent_count = (
            db.query(SwapRequest)
            .filter(
                SwapRequest.sender_id == user.id
            )
            .count()
        )

        received_count = (
            db.query(SwapRequest)
            .filter(
                SwapRequest.receiver_id == user.id
            )
            .count()
        )

        st.divider()

        # ----------------------------------------------------
        # STATISTICS
        # ----------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "Skills I Teach",
                len(teaching)
            )

        with col2:

            st.metric(
                "Skills I Want",
                len(learning)
            )

        with col3:

            st.metric(
                "Requests Sent",
                sent_count
            )

        with col4:

            st.metric(
                "Requests Received",
                received_count
            )

        st.divider()

        # ----------------------------------------------------
        # SKILL DISPLAY
        # ----------------------------------------------------

        col1, col2 = st.columns(2)

        with col1:

            st.subheader("🧑‍🏫 Skills I Teach")

            if teaching:

                for skill_name in teaching:

                    # skill_name is guaranteed to be a STRING
                    st.write(f"• {skill_name}")

            else:

                st.info(
                    "You haven't added any teaching skills."
                )

        with col2:

            st.subheader("📖 Skills I Want to Learn")

            if learning:

                for skill_name in learning:

                    # skill_name is guaranteed to be a STRING
                    st.write(f"• {skill_name}")

            else:

                st.info(
                    "You haven't added any learning skills."
                )

        st.divider()

        # ----------------------------------------------------
        # QUICK ACTIONS
        # ----------------------------------------------------

        st.subheader("⚡ Quick Actions")

        col1, col2, col3 = st.columns(3)

        with col1:

            if st.button(
                "🛠️ Manage Skills",
                use_container_width=True
            ):

                st.session_state.page = "My Skills"
                st.rerun()

        with col2:

            if st.button(
                "🤝 Find Matches",
                use_container_width=True
            ):

                st.session_state.page = "Smart Matches"
                st.rerun()

        with col3:

            if st.button(
                "📨 Send Request",
                use_container_width=True
            ):

                st.session_state.page = "Send Swap Request"
                st.rerun()

    finally:
        db.close()


# ============================================================
# SIDEBAR
# ============================================================

def sidebar():

    with st.sidebar:

        st.title("🔄 SkillSwap")

        st.divider()

        if st.session_state.logged_in:

            if st.button(
                "📊 Dashboard",
                use_container_width=True
            ):
                st.session_state.page = "Dashboard"
                st.rerun()

            if st.button(
                "👤 Profile",
                use_container_width=True
            ):
                st.session_state.page = "Profile"
                st.rerun()

            if st.button(
                "🛠️ My Skills",
                use_container_width=True
            ):
                st.session_state.page = "My Skills"
                st.rerun()

            if st.button(
                "🤝 Smart Matches",
                use_container_width=True
            ):
                st.session_state.page = "Smart Matches"
                st.rerun()

            if st.button(
                "📨 Send Swap Request",
                use_container_width=True
            ):
                st.session_state.page = "Send Swap Request"
                st.rerun()

            # Communication
            db = SessionLocal()
            try:
                notification_count = get_unread_notification_count(
                    st.session_state.user_id,
                    db
                )

                message_count = get_unread_message_count(
                    st.session_state.user_id,
                    db
                )
            finally:
                db.close()

            notification_label = (
                f"🔔 Notifications"
                f"{f' ({notification_count})' if notification_count else ''}"
            )

            message_label = (
                f"💬 Messages"
                f"{f' ({message_count})' if message_count else ''}"
            )

            if st.button(
                notification_label,
                use_container_width=True
            ):
                st.session_state.page = "Notifications"
                st.rerun()

            if st.button(
                message_label,
                use_container_width=True
            ):
                st.session_state.page = "Messages"
                st.rerun()

            st.divider()

            if st.button(
                "🚪 Logout",
                use_container_width=True
            ):

                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.page = "Home"

                st.rerun()

        else:

            if st.button(
                "🏠 Home",
                use_container_width=True
            ):
                st.session_state.page = "Home"
                st.rerun()

            if st.button(
                "📝 Register",
                use_container_width=True
            ):
                st.session_state.page = "Register"
                st.rerun()

            if st.button(
                "🔐 Login",
                use_container_width=True
            ):
                st.session_state.page = "Login"
                st.rerun()


# ============================================================
# MAIN ROUTER
# ============================================================

sidebar()


if st.session_state.page == "Home":

    home_page()

elif st.session_state.page == "Register":

    register_page()

elif st.session_state.page == "Login":

    login_page()

elif st.session_state.page == "Profile":

    profile_page()

elif st.session_state.page == "My Skills":

    skills_page()

elif st.session_state.page == "Smart Matches":

    matches_page()

elif st.session_state.page == "Send Swap Request":

    send_request_page()

elif st.session_state.page == "Dashboard":

    dashboard_page()

elif st.session_state.page == "Notifications":

    notifications_page()

elif st.session_state.page == "Messages":

    messages_page()

else:

    home_page()