# db/session_repo.py
"""
FINAL SESSION REPOSITORY - 9-HOUR FAULT + FRIENDLY MESSAGES
Rules:
• First scan → LOGIN
• Second scan within <9h → LOGOUT → PRESENT
• No second scan + ≥9h → AUTO ABSENT (user fault)
• Multiple scans after logout → "LOGIN/LOGOUT for the day is completed"

Day Label policy (per user selection):
< 4 hrs → Half Day
4–8 hrs → Half Day
≥ 8 hrs → Full Day

We compute and store `day_label` on session finalization (logout and auto-absent).
"""

from pymongo.collection import Collection
from pymongo.results import InsertOneResult, UpdateResult
from db.client import get_db
from rich.console import Console
from typing import Tuple, Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
import pytz

# Indian Standard Time timezone
IST = pytz.timezone('Asia/Kolkata')
from utils.email import send_attendance_email, send_structured_attendance_email

console = Console()

def get_sessions_collection() -> Collection | None:
    db = get_db()
    if db is None:
        console.print("[bold red]MongoDB connection failed![/bold red]")
        return None
    return db.sessions

# -----------------------------
# Day Label computation helper
# -----------------------------

def compute_day_label(duration_minutes: Optional[int]) -> Optional[str]:
    """Map duration to a day label per policy A.
    Returns one of: "Half Day", "Full Day", or None if duration is None.
    Policy:
      - < 240 min (4h) → Half Day
      - 240–479 min (4–8h) inclusive of 4h but below 8h → Half Day
      - ≥ 480 min (8h) → Full Day
    """
    if duration_minutes is None:
        return None
    if duration_minutes >= 480:
        return "Full Day"
    # Both <4h and 4–8h → Half Day per requirement
    return "Half Day"


def mark_session(user_id: str, name: str, email: str) -> Tuple[str, str]:
    """
    Called on every biometric scan (Face + Voice)
    Returns: (action, message)
    Actions: LOGIN | LOGOUT | COMPLETED | ABSENT_AUTO | ERROR
    NOW SENDS EMAIL ON LOGOUT & AUTO-ABSENT
    """
    collection = get_sessions_collection()
    if collection is None:
        return "ERROR", "Database not available"

    # Use UTC timezone-aware datetime
    now = datetime.now(timezone.utc)
    today = now.date()
    today_str = today.isoformat()

    # Find today's session
    session = collection.find_one({
        "user_id": user_id,
        "date": today_str
    })

    # CASE 1: First time today → LOGIN
    if not session:
        record = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "login_time": now,
            "logout_time": None,
            "duration_minutes": None,
            "status": "active",
            "date": today_str,
            "updated_at": now
        }
        collection.insert_one(record)
        login_str = now.strftime("%I:%M %p")
        console.print(f"[bold green]LOGIN → {name} at {login_str}[/bold green]")

        # NO EMAIL ON LOGIN
        print(f"✅ Check-in recorded - Email will be sent on check-out")

        return "LOGIN", f"Welcome! Logged in at {login_str}"

    # CASE 2: Already logged out today → "LOGIN/LOGOUT for the day is completed"
    if session.get("logout_time") is not None:
        if session.get("status") == "absent_fault":
            console.print(f"[bold yellow]LOGIN/LOGOUT for the day is completed — {name} marked ABSENT[/bold yellow]")
            return "COMPLETED", "LOGIN/LOGOUT for the day is completed (marked ABSENT)"
        else:
            console.print(f"[bold yellow]LOGIN/LOGOUT for the day is completed — {name} marked PRESENT[/bold yellow]")
            return "COMPLETED", "LOGIN/LOGOUT for the day is completed (marked PRESENT)"

    # CASE 3: Still active → LOGOUT
    login_time = session["login_time"]
    
    # Handle timezone-naive login_time from database
    if login_time.tzinfo is None:
        login_time = login_time.replace(tzinfo=timezone.utc)
    
    hours_passed = (now - login_time).total_seconds() / 3600.0

    # SUBCASE 3A: ≥9 hours → Auto ABSENT
    if hours_passed >= 9:
        auto_logout = login_time + timedelta(hours=9)
        duration_min = 540
        day_label = compute_day_label(duration_min)
        collection.update_one(
            {"_id": session["_id"]},
            {"$set": {
                "logout_time": auto_logout,
                "duration_minutes": duration_min,
                "day_label": day_label,
                "status": "absent_fault",
                "updated_at": now
            }}
        )
        console.print(f"[bold red]AUTO ABSENT → {name} (no logout for ≥9 hours)[/bold red]")

        # SEND AUTO-ABSENT EMAIL
        try:
            timestamp = auto_logout.strftime("%d %b %Y • %H:%M:%S")
            send_attendance_email(name, email, "ABSENT_AUTO", timestamp=timestamp)
            print(f"📧 Auto-absent email sent to {email}")
        except Exception as e:
            print(f"❌ Auto-absent email failed: {e}")

        return "ABSENT_AUTO", "Marked ABSENT — forgot to logout"

    # SUBCASE 3B: Normal logout (<9h)
    duration_min = int(hours_passed * 60)
    day_label = compute_day_label(duration_min)
    collection.update_one(
        {"_id": session["_id"]},
        {"$set": {
            "logout_time": now,
            "duration_minutes": duration_min,
            "day_label": day_label,
            "status": "present",
            "updated_at": now
        }}
    )
    logout_str = now.strftime("%I:%M %p")
    console.print(f"[bold magenta]LOGOUT → {name} after {duration_min} min → PRESENT[/bold magenta]")

    # SEND STRUCTURED ATTENDANCE EMAIL ON CHECKOUT
    try:
        checkin_time_str = login_time.strftime("%I:%M %p")
        checkout_time_str = now.strftime("%I:%M %p")
        formatted_date = today.strftime("%d/%m/%y")
        
        send_structured_attendance_email(
            name=name,
            email=email,
            date=formatted_date,
            in_time=checkin_time_str,
            out_time=checkout_time_str,
            status="Present"
        )
        print(f"📧 Structured attendance email sent to {email}")
    except Exception as e:
        print(f"❌ Structured attendance email failed: {e}")

    return "LOGOUT", f"Goodbye! You are marked PRESENT ({duration_min} min)"

def get_today_status(user_id: str) -> Dict[str, Any]:
    """Used by reports — returns final status"""
    collection = get_sessions_collection()
    if collection is None:
        return {"status": "absent", "reason": "DB error"}

    today_str = datetime.now(timezone.utc).date().isoformat()
    session = collection.find_one({"user_id": user_id, "date": today_str})

    if not session:
        return {"status": "absent", "reason": "No login today"}

    # If already finalized
    if session.get("logout_time"):
        if session.get("status") == "absent_fault":
            return {"status": "absent", "reason": "Forgot logout ≥9h"}
        return {"status": "present", "reason": "Proper session"}

    # Still active — check time
    login_time = session["login_time"]
    if login_time.tzinfo is None:
        login_time = login_time.replace(tzinfo=timezone.utc)
    hours = (datetime.now(timezone.utc) - login_time).total_seconds() / 3600
    if hours >= 9:
        auto_logout = session["login_time"] + timedelta(hours=9)
        duration_min = 540
        day_label = compute_day_label(duration_min)
        collection.update_one(
            {"_id": session["_id"]},
            {"$set": {
                "logout_time": auto_logout,
                "duration_minutes": duration_min,
                "day_label": day_label,
                "status": "absent_fault",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        return {"status": "absent", "reason": "Auto-absent ≥9h"}

    return {"status": "present", "reason": "Active session (<9h)"}


def get_report(date_str: str) -> List[Dict]:
    """Generate beautiful daily report with correct Present/Absent"""
    collection = get_sessions_collection()
    if collection is None:
        console.print("[bold red]Report failed: DB unavailable[/bold red]")
        return []

    sessions = list(collection.find({"date": date_str}).sort("login_time", 1))
    result = []

    for s in sessions:
        login = s["login_time"].strftime("%I:%M %p") if s.get("login_time") else "—"
        logout = s["logout_time"].strftime("%I:%M %p") if s.get("logout_time") else "—"
        duration = f"{s.get('duration_minutes', 0)} min" if s.get('duration_minutes') is not None else "—"

        # FINAL STATUS LOGIC — ALWAYS TRUST "status" FIELD
        status = s.get("status", "active")

        if status == "present":
            display_status = "[bold green]Present[/bold green]"
        elif status == "absent_fault":
            display_status = "[bold red]Absent[/bold red] (Forgot Logout)"
        elif status == "active" and s.get("logout_time") is None:
            login_time = s["login_time"]
            if login_time.tzinfo is None:
                login_time = login_time.replace(tzinfo=timezone.utc)
            hrs = (datetime.now(timezone.utc) - login_time).total_seconds() / 3600
            if hrs >= 9:
                display_status = "[bold red]Absent[/bold red] (Auto ≥9h)"
            else:
                display_status = "[yellow]Active[/yellow]"
        else:
            display_status = "[dim]Unknown[/dim]"

        result.append({
            "name": s["name"],
            "email": s["email"],
            "login": login,
            "logout": logout,
            "duration": duration,
            "duration_minutes": s.get('duration_minutes'),
            "day_label": s.get('day_label') or compute_day_label(s.get('duration_minutes')),
            "status": display_status
        })

    return result