# db/user_repo.py
"""
User repository - CRUD operations for users
Collection: users
"""

from pymongo.collection import Collection
from pymongo.results import InsertOneResult
from db.client import get_db
from rich.console import Console
from typing import Dict, Any, List

console = Console()

def get_users_collection() -> Collection | None:
    """Get users collection"""
    db = get_db()
    if db is None:
        return None
    return db.users

def save_user(user_data: Dict[str, Any]) -> InsertOneResult | None:
    """
    Save new user with face + voice embeddings + user type information
    Returns InsertOneResult or None
    """
    collection = get_users_collection()
    if collection is None:
        console.print("[red]Database not available[/red]")
        return None

    try:
        # === FACE EMBEDDINGS (unchanged) ===
        if "face_embeddings" in user_data:
            user_data["face_embeddings"] = [
                emb if isinstance(emb, list) else emb.tolist()
                for emb in user_data["face_embeddings"]
            ]

        # === VOICE EMBEDDING (ECAPA-TDNN 192D) ===
        if "voice_embedding" in user_data:
            emb = user_data["voice_embedding"]
            if not isinstance(emb, list):
                emb = emb.tolist()
            user_data["voice_embedding"] = emb  # 192D list (ECAPA-TDNN)
        
        # === NEW: Save voice backup paths for future model compatibility ===
        if "voice_backup_paths" in user_data:
            console.print(f"[green]Voice backups saved: {len(user_data['voice_backup_paths'])} files[/green]")
        
        # === NEW: Save backup user ID for file organization ===
        if "backup_user_id" in user_data:
            console.print(f"[cyan]Backup user ID: {user_data['backup_user_id']}[/cyan]")
        
        # === NEW: Legacy voice audio path support ===
        if "voice_audio_path" in user_data:
            console.print(f"[yellow]Legacy voice file: {user_data['voice_audio_path']}[/yellow]")

        # === USER TYPE & PHONE/CLASS VALIDATION ===
        user_type = user_data.get("user_type", "student")  # Default to student
        if user_type not in ["student", "faculty"]:
            console.print(f"[red]Invalid user_type: {user_type}. Must be 'student' or 'faculty'[/red]")
            return None
        
        # Validate phone number (required for all users)
        phone = user_data.get("phone")
        if not phone or len(str(phone).strip()) < 10:
            console.print(f"[red]Phone number is required for all users (minimum 10 digits)[/red]")
            return None
        
        # Validate student class if user is a student
        if user_type == "student":
            student_class = user_data.get("student_class")
            valid_classes = ["M.Sc in AI", "M.Sc in CS", "M.Sc in BA", "M.Tech in AI", "M.Tech in CS"]
            if student_class not in valid_classes:
                console.print(f"[red]Invalid student_class: {student_class}. Must be one of {valid_classes}[/red]")
                return None

        result = collection.insert_one(user_data)
        console.print(f"[green]User saved with ID: {result.inserted_id}[/green]")
        return result

    except Exception as e:
        console.print(f"[red]Failed to save user: {e}[/red]")
        return None

def find_user_by_email(email: str) -> Dict | None:
    """Find user by email"""
    collection = get_users_collection()
    if collection is None:
        return None

    try:
        user = collection.find_one({"email": email})
        return user
    except Exception as e:
        console.print(f"[red]Query error: {e}[/red]")
        return None

def get_all_users() -> List[Dict] | None:
    """Get all registered users WITH face + voice embeddings + user info"""
    collection = get_users_collection()
    if collection is None:
        return None

    try:
        users = list(collection.find({}, {
            "name": 1,
            "email": 1,
            "phone": 1,                # ← NEW (required for all users)
            "user_type": 1,            # ← NEW (student/faculty)
            "student_class": 1,        # ← NEW (for students only)
            "photo_count": 1,
            "voice_clips": 1,
            "registered_at": 1,
            "face_embeddings": 1,
            "voice_embedding": 1,
            "_id": 1
        }))
        console.print(f"[cyan]Loaded {len(users)} users[/cyan]")
        return users
    except Exception as e:
        console.print(f"[red]Failed to load users: {e}[/red]")
        return None

def get_user_embeddings(user_id: str) -> Dict[str, Any] | None:
    """Get face + voice embeddings for a user"""
    collection = get_users_collection()
    if collection is None:
        return None

    try:
        user = collection.find_one(
            {"_id": user_id},
            {
                "face_embeddings": 1,
                "voice_embedding": 1
            }
        )
        if user:
            return {
                "face_embeddings": user.get("face_embeddings", []),
                "voice_embedding": user.get("voice_embedding")
            }
        return None
    except Exception as e:
        console.print(f"[red]Failed to get embeddings: {e}[/red]")
        return None

def create_user(user_data: Dict[str, Any]) -> str | None:
    """Create a new user and return user ID"""
    collection = get_users_collection()
    if collection is None:
        console.print("[red]Database not available[/red]")
        return None

    try:
        result = collection.insert_one(user_data)
        console.print(f"[green]User created with ID: {result.inserted_id}[/green]")
        return str(result.inserted_id)
    except Exception as e:
        console.print(f"[red]Failed to create user: {e}[/red]")
        return None

def get_user_by_id(user_id: str) -> Dict | None:
    """Get user by ObjectId"""
    collection = get_users_collection()
    if collection is None:
        return None

    try:
        from bson import ObjectId
        user = collection.find_one({"_id": ObjectId(user_id)})
        return user
    except Exception as e:
        console.print(f"[red]Failed to get user by ID: {e}[/red]")
        return None

def update_user_face_data(user_id: str, face_embeddings: List, photo_count: int) -> bool:
    """Update user's face embeddings and photo count"""
    collection = get_users_collection()
    if collection is None:
        return False

    try:
        from bson import ObjectId
        result = collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "face_embeddings": face_embeddings,
                    "photo_count": photo_count
                }
            }
        )
        success = result.modified_count > 0
        if success:
            console.print(f"[green]Updated face data for user {user_id}[/green]")
        return success
    except Exception as e:
        console.print(f"[red]Failed to update face data: {e}[/red]")
        return False

def update_user_voice_data(user_id: str, voice_embedding: List, voice_clips: int) -> bool:
    """Update user's voice embedding and voice clips count"""
    collection = get_users_collection()
    if collection is None:
        return False

    try:
        from bson import ObjectId
        result = collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "voice_embedding": voice_embedding,
                    "voice_clips": voice_clips
                }
            }
        )
        success = result.modified_count > 0
        if success:
            console.print(f"[green]Updated voice data for user {user_id}[/green]")
        return success
    except Exception as e:
        console.print(f"[red]Failed to update voice data: {e}[/red]")
        return False

def update_user_registration_status(user_id: str, registration_complete: bool) -> bool:
    """Mark user registration as complete"""
    collection = get_users_collection()
    if collection is None:
        return False

    try:
        from bson import ObjectId
        result = collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "registration_complete": registration_complete
                }
            }
        )
        success = result.modified_count > 0
        if success:
            console.print(f"[green]Registration completed for user {user_id}[/green]")
        return success
    except Exception as e:
        console.print(f"[red]Failed to update registration status: {e}[/red]")
        return False

def search_users_by_name_email(query: str) -> List[Dict]:
    """Search users by name or email containing query string"""
    collection = get_users_collection()
    if collection is None:
        return []
    
    try:
        # Create regex pattern for case-insensitive search
        regex_pattern = {"$regex": query, "$options": "i"}
        
        # Search in both name and email fields
        cursor = collection.find({
            "$or": [
                {"name": regex_pattern},
                {"email": regex_pattern}
            ]
        }).limit(20)  # Limit results to prevent too many matches
        
        users = list(cursor)
        console.print(f"[cyan]Found {len(users)} users matching '{query}'[/cyan]")
        return users
        
    except Exception as e:
        console.print(f"[red]Error searching users: {e}[/red]")
        return []

def delete_user_by_id(user_id: str) -> bool:
    """Delete user by ObjectId"""
    collection = get_users_collection()
    if collection is None:
        return False

    try:
        from bson import ObjectId
        result = collection.delete_one({"_id": ObjectId(user_id)})
        success = result.deleted_count > 0
        if success:
            console.print(f"[green]User {user_id} deleted successfully[/green]")
        else:
            console.print(f"[yellow]User {user_id} not found for deletion[/yellow]")
        return success
    except Exception as e:
        console.print(f"[red]Failed to delete user: {e}[/red]")
        return False

def get_user_by_email(email):
    """Get user by email address"""
    try:
        db = get_db()
        if db is None:
            console.print("[red]Database connection failed[/red]")
            return None
        
        user = db.users.find_one({"email": email.lower().strip()})
        return user
        
    except Exception as e:
        console.print(f"[red]Failed to get user by email: {e}[/red]")
        return None

def get_user_by_phone(phone):
    """Get user by phone number"""
    try:
        db = get_db()
        if db is None:
            console.print("[red]Database connection failed[/red]")
            return None
        
        # Clean phone number for search (remove spaces, dashes, parentheses)
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Search for phone in various formats
        user = db.users.find_one({
            "$or": [
                {"phone": phone},
                {"phone": clean_phone},
                {"additional_data.phone": phone},
                {"additional_data.phone": clean_phone}
            ]
        })
        return user
        
    except Exception as e:
        console.print(f"[red]Failed to get user by phone: {e}[/red]")
        return None