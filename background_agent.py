from pynput import keyboard
import time
import pandas as pd
import joblib
import os
import sys
from datetime import datetime
import getpass
from win10toast import ToastNotifier
import winsound
import requests

# ================== CONFIG ==================
BACKEND_URL = "http://127.0.0.1:8000/agent/send-data"
WINDOW_TIME = 60
STRESS_THRESHOLD = 5

# ================== USER ==================
USER_ID = getpass.getuser()
print("Agent running for user:", USER_ID)

# ================== TOAST SETUP ==================
toaster = ToastNotifier()

# ================== PYINSTALLER SAFE PATH ==================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS   # temp folder when exe runs
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# ================== LOAD MODEL ==================
model_path = resource_path("stress_model.pkl")
scaler_path = resource_path("scaler.pkl")

print("Loading model from:", model_path)
print("Loading scaler from:", scaler_path)

model = joblib.load(model_path)
scaler = joblib.load(scaler_path)

# ================== VARIABLES ==================
keystroke_times = []
backspace_count = 0
stress_counter = 0
alert_sent = False

# ================== KEY LISTENER ==================
def on_press(key):
    global backspace_count
    keystroke_times.append(time.time())
    if key == keyboard.Key.backspace:
        backspace_count += 1

listener = keyboard.Listener(on_press=on_press)
listener.daemon = True
listener.start()

print("✅ Background Stress Agent Running...")

# ================== FEATURE FUNCTION ==================
def extract_features(times):
    if len(times) < 2:
        return 0, 0

    flights = [times[i] - times[i - 1] for i in range(1, len(times))]
    avg_flight = sum(flights) / len(flights)
    avg_dwell = avg_flight

    return avg_dwell, avg_flight

# ================== MAIN LOOP ==================
while True:
    time.sleep(WINDOW_TIME)

    prediction = "INSUFFICIENT_DATA"
    avg_dwell, avg_flight = 0, 0

    if len(keystroke_times) >= 5:
        avg_dwell, avg_flight = extract_features(keystroke_times)

        X_df = pd.DataFrame([{
            "avg_dwell_time": avg_dwell,
            "avg_flight_time": avg_flight,
            "backspace_count": backspace_count
        }])

        X_scaled = scaler.transform(X_df)
        raw_pred = model.predict(X_scaled)[0]

        if raw_pred == 1:
            stress_counter += 1
        else:
            stress_counter = 0
            alert_sent = False

        prediction = "STRESS_CONFIRMED" if stress_counter >= STRESS_THRESHOLD else "NORMAL"
    else:
        stress_counter = 0
        alert_sent = False

    # ================== ALERT ==================
    if stress_counter >= STRESS_THRESHOLD and not alert_sent:
        toaster.show_toast(
            "⚠️ Stress Alert",
            "Continuous stress detected.\nPlease take a short break.",
            duration=10,
            threaded=True
        )
        winsound.Beep(1000, 700)
        alert_sent = True

    # ================== SEND TO BACKEND ==================
    payload = {
        "user_id": USER_ID,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "avg_dwell_time": round(avg_dwell, 4),
        "avg_flight_time": round(avg_flight, 4),
        "backspace_count": backspace_count,
        "prediction": prediction
    }

    try:
        r = requests.post(BACKEND_URL, json=payload, timeout=5)
        if r.status_code == 200:
            print("📤 Data sent to backend")
        else:
            print("❌ Backend error:", r.text)
    except Exception as e:
        print("❌ Backend not reachable:", e)

    keystroke_times.clear()
    backspace_count = 0
