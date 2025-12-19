# db/session_repo.py
"""
FINAL SESSION REPOSITORY - 9-HOUR FAULT + FRIENDLY MESSAGES
Now uses INDIAN STANDARD TIME (IST) for all timestamps
"""

from pymongo.collection import Collection
from typing import Tuple, Dict, List, Any, Optional
from db.client import get_db
from rich.console import Console
from datetime import datetime, timedelta, timezone

# Use system local time throughout (no fixed timezone)
LOCAL_TZ = datetime.now().astimezone().tzinfo

def _to_local_naive(dt: datetime) -> datetime:
    """Convert any datetime to system local time and drop tzinfo (naive).
    Handles historical tz-aware values by converting to the local tz, then making naive.
    """
    if dt is None:
        return dt
    try:
        if isinstance(dt, datetime):
            if dt.tzinfo is not None:
                dt = dt.astimezone(LOCAL_TZ).replace(tzinfo=None)
            # If naive, assume it's already local
        return dt
    except Exception:
        return dt

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
    """Map duration to a day label per policy"""
    if duration_minutes is None:
        return None
    if duration_minutes >= 480:  # ≥8 hours
        return "Full Day"
    return "Half Day"  # <8 hours (including <4h and 4–8h)


def mark_session(user_id: str, name: str, email: str) -> Tuple[str, str]:
    """
    Called on every biometric scan (Face + Voice)
    All times now in IST
    """
    collection = get_sessions_collection()
    if collection is None:
        return "ERROR", "Database not available"

        # Use system local time (naive)
    now_local = datetime.now()
    today = now_local.date()
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
            "login_time": now_local,
            "logout_time": None,
            "duration_minutes": None,
            "status": "active",
            "date": today_str,
            "updated_at": now_local
        }
        collection.insert_one(record)
        login_str = now_local.strftime("%I:%M %p")
        console.print(f"[bold green]LOGIN → {name} at {login_str}[/bold green]")

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

    # Normalize any stored datetime to system local naive
    login_time = _to_local_naive(login_time)

    hours_passed = (now_local - login_time).total_seconds() / 3600.0

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
                "updated_at": now_ist
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
            "logout_time": now_local,
            "duration_minutes": duration_min,
            "day_label": day_label,
            "status": "present",
            "updated_at": now_local
        }}
    )
    logout_str = now_local.strftime("%I:%M %p")
    console.print(f"[bold magenta]LOGOUT → {name} after {duration_min} min → PRESENT[/bold magenta]")

    # SEND STRUCTURED ATTENDANCE EMAIL ON CHECKOUT
    try:
        checkin_time_str = login_time.strftime("%I:%M %p")
        checkout_time_str = now_local.strftime("%I:%M %p")
        formatted_date = today.strftime("%d/%m/%y")
        
        send_structured_attendance_email(
            name=name,
            email=email,
            date=formatted_date,
            in_time=checkin_time_str,
            out_time=checkout_time_str,
            status=f"Present - {day_label.replace(' ', '') if day_label else 'FullDay'}"
        )
        print(f"📧 Structured attendance email sent to {email}")
    except Exception as e:
        print(f"❌ Structured attendance email failed: {e}")

    return "LOGOUT", f"Goodbye! You are marked PRESENT ({duration_min} min)"


def get_today_status(user_id: str) -> Dict[str, Any]:
    """Used by reports — returns final status using IST"""
    collection = get_sessions_collection()
    if collection is None:
        return {"status": "absent", "reason": "DB error"}

    now_local = datetime.now()
    today_str = now_local.date().isoformat()

    session = collection.find_one({"user_id": user_id, "date": today_str})

    if not session:
        return {"status": "absent", "reason": "No login today"}

    # If already finalized
    if session.get("logout_time"):
        if session.get("status") == "absent_fault":
            return {"status": "absent", "reason": "Forgot logout ≥9h"}
        return {"status": "present", "reason": "Proper session"}

    # Still active — check time in IST
    login_time = session["login_time"]
    login_time = _to_local_naive(login_time)

    hours = (now_local - login_time).total_seconds() / 3600
    if hours >= 9:
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
                "updated_at": now_ist
            }}
        )
        return {"status": "absent", "reason": "Auto-absent ≥9h"}

    return {"status": "present", "reason": "Active session (<9h)"}


def get_report(date_str: str) -> List[Dict]:
    """Generate daily report using IST formatting"""
    collection = get_sessions_collection()
    if collection is None:
        console.print("[bold red]Report failed: DB unavailable[/bold red]")
        return []

    sessions = list(collection.find({"date": date_str}).sort("login_time", 1))
    result = []

    for s in sessions:
        # Convert times to system local for display
        login_time = _to_local_naive(s["login_time"]) if s.get("login_time") else None
        logout_time = _to_local_naive(s.get("logout_time")) if s.get("logout_time") else None

        login = login_time.strftime("%I:%M %p") if login_time else "—"
        logout = logout_time.strftime("%I:%M %p") if logout_time else "—"

        duration = f"{s.get('duration_minutes', 0)} min" if s.get('duration_minutes') is not None else "—"

        # FINAL STATUS LOGIC
        status = s.get("status", "active")

        if status == "present":
            display_status = "[bold green]Present[/bold green]"
        elif status == "absent_fault":
            display_status = "[bold red]Absent[/bold red] (Forgot Logout)"
        elif status == "active" and s.get("logout_time") is None:
            now_local = datetime.now()
            base_login = login_time or _to_local_naive(s["login_time"]) if s.get("login_time") else None
            if base_login:
                hrs = (now_local - base_login).total_seconds() / 3600
                display_status = "[bold red]Absent[/bold red] (Auto ≥9h)" if hrs >= 9 else "[yellow]Active[/yellow]"
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