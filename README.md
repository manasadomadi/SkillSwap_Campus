# SkillSwap Campus - Communication Upgrade

This version keeps the existing SkillSwap Campus functionality and adds:

- Swap request notifications
- Accept / Reject swap requests
- Private chat after a request is accepted
- Text messages
- Message notifications
- Browser voice recording and voice messages
- Browser voice calls
- Browser video calls

## 1. Install

Windows:

```bat
venv\Scripts\activate
pip install -r requirements.txt
```

If you do not have a virtual environment:

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Start Streamlit

Terminal 1:

```bat
venv\Scripts\activate
streamlit run app.py
```

## 3. Start the call server

Terminal 2:

```bat
venv\Scripts\activate
uvicorn call_server:app --host 0.0.0.0 --port 8000
```

Open:

http://localhost:8501

## How communication works

1. Student A sends a swap request.
2. Student B sees a notification.
3. Student B opens Notifications.
4. Student B chooses Accept or Reject.
5. If accepted, both students can open Messages.
6. Text and voice messages are stored in the existing SQLite database.
7. Voice/video calls open through the WebRTC call server.

## Deployment note

For public deployment, browser microphone/camera access normally requires HTTPS.
The call server should therefore be deployed behind HTTPS and CALL_SERVER_URL
in config.py should be changed from localhost to the deployed call-server URL.

For a production application, add user authentication to the call server and
use a TURN server for networks where direct peer-to-peer WebRTC connectivity
does not work.
