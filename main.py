from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import os

app = FastAPI(title="Stress Typing Backend")

# ================= CORS =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= DATABASE =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "stress.db")

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def create_table():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stress_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            timestamp TEXT,
            avg_dwell_time REAL,
            avg_flight_time REAL,
            backspace_count INTEGER,
            prediction TEXT
        )
    """)
    conn.commit()
    conn.close()

create_table()

# ================= MODEL =================
class StressData(BaseModel):
    user_id: str
    timestamp: str | None = None
    avg_dwell_time: float
    avg_flight_time: float
    backspace_count: int
    prediction: str

# ================= ROOT =================
@app.get("/")
def root():
    return {"status": "Backend running"}

# ================= AGENT → BACKEND =================
@app.post("/agent/send-data")
def receive_data(data: StressData):
    ts = data.timestamp or datetime.now().isoformat()
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO stress_logs
            (user_id, timestamp, avg_dwell_time, avg_flight_time, backspace_count, prediction)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.user_id,
            ts,
            data.avg_dwell_time,
            data.avg_flight_time,
            data.backspace_count,
            data.prediction
        ))
        conn.commit()
        conn.close()
        return {"message": "Data stored successfully"}
    except Exception as e:
        return {"error": str(e)}

# ================= USER DASHBOARD =================
@app.get("/dashboard/user/{user_id}")
def user_dashboard(user_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM stress_logs WHERE user_id = ? ORDER BY timestamp DESC",
        (user_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return {
        "user_id": user_id,
        "count": len(rows),
        "data": [dict(r) for r in rows]
    }

# ================= HR DASHBOARD =================
@app.get("/dashboard/hr")
def hr_dashboard():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM stress_logs ORDER BY timestamp DESC")
    rows = cur.fetchall()
    conn.close()
    return {
        "total_records": len(rows),
        "data": [dict(r) for r in rows]
    }

# ================= COMPAT ROUTE =================
@app.get("/stress-logs")
def stress_logs_alias():
    return hr_dashboard()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)
