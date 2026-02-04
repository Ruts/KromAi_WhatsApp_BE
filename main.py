from fastapi import FastAPI, Request, HTTPException
import requests
import os

app = FastAPI()

# --- Environment Variables ---
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")  # Your long Bearer token
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")  # e.g. "972855682579158"
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_verify_token")  # Arbitrary string you set
ASK_API_URL = os.getenv("ASK_API_URL", "http://127.0.0.1:8000/ask")  # Your /ask endpoint

# --- 1. Webhook Verification ---
@app.get("/webhook")
async def verify_webhook(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params["hub.challenge"])
    return {"error": "Verification failed"}

# --- 2. Handle Incoming Messages ---
@app.post("/webhook")
async def handle_webhook(request: Request):
    body = await request.json()
    print("Incoming webhook:", body)

    try:
        entry = body["entry"][0]["changes"][0]["value"]
        if "messages" in entry:
            message = entry["messages"][0]
            sender = message["from"]  # WhatsApp number of sender
            text = message.get("text", {}).get("body", "")

            print(f"Message from {sender}: {text}")

            # --- 3. Call your /ask API ---
            payload = {
                "question": text,
                "ai_model": "KROM Foods",   # or whichever model name you want
                "userId": sender                # use WhatsApp number as userId
            }
            ask_response = requests.post(ASK_API_URL, json=payload)

            if ask_response.status_code != 200:
                raise HTTPException(status_code=ask_response.status_code, detail="LLM call failed")

            answer = ask_response.json().get("answer", "Sorry, I couldn't process that.")

            # --- 4. Send reply back to WhatsApp ---
            send_message(sender, answer)

    except Exception as e:
        print("Error handling webhook:", e)

    return {"status": "ok"}

# --- 5. Function to Send Replies ---
def send_message(to: str, text: str):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }

    response = requests.post(url, headers=headers, json=data)
    print("Reply response:", response.json())
    return response.json()
