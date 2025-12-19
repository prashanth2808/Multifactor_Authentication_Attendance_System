# services/registration_service.py
"""
UNIFIED REGISTRATION SERVICE - Single Source of Truth
Shared by both CLI and Flask interfaces for consistent registration logic
"""

import os
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from rich.console import Console

# Import existing services
from services.embedding import get_face_embedding
from services.voice_embedding import record_and_embed_three_times
from db.user_repo import save_user
from db.client import get_db

console = Console()

class RegistrationService:
    """Unified registration service used by both CLI and Flask interfaces"""
    
    def __init__(self):
        self.console = console
    
    def register_user(self, name: str, email: str, face_data: Any, voice_data: Any, 
                     source: str = "unknown", additional_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Unified user registration function
        
        Args:
            name: User's full name
            email: User's email address
            face_data: Face images (format depends on source)
            voice_data: Voice data (format depends on source)
            source: "cli" or "flask" for different input handling
            
        Returns:
            Dict with success status and user info
        """
        try:
            self.console.print(f"[bold blue]🚀 Starting unified registration for:[/bold blue] {name} ({email})")
            self.console.print(f"[dim]Source: {source}[/dim]")
            
            # Step 1: Validate input data
            validation_result = self._validate_registration_data(name, email)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "stage": "validation"
                }
            
            # Step 2: Check if user already exists
            existing_check = self._check_existing_user(email)
            if not existing_check["available"]:
                return {
                    "success": False,
                    "error": f"User with email {email} already registered",
                    "stage": "duplicate_check",
                    "existing_user_id": existing_check.get("user_id")
                }
            
            # Step 3: Create user folder
            user_folder = self._create_user_folder(name)
            
            # Step 4: Process face data (unified processing)
            face_result = self._process_face_data(face_data, source, user_folder, name)
            if not face_result["success"]:
                return {
                    "success": False,
                    "error": face_result["error"],
                    "stage": "face_processing"
                }
            
            # Step 5: Process voice data (unified processing)
            voice_result = self._process_voice_data(voice_data, source, name)
            if not voice_result["success"]:
                return {
                    "success": False,
                    "error": voice_result["error"],
                    "stage": "voice_processing"
                }
            
            # Step 6: Save to database (unified data structure)
            user_db_data = {
                "name": name,
                "email": email,
                "face_embeddings": face_result["embeddings"],
                "voice_embedding": voice_result["embedding"],
                "photo_count": len(face_result["embeddings"]),
                "voice_clips": voice_result["clips_used"],
                "registered_at": datetime.now(),
                "photo_folder": user_folder,
                "registration_source": source
            }
            
            # Add ECAPA-TDNN voice backup data if available
            if "voice_audio_path" in voice_result:
                user_db_data["voice_audio_path"] = voice_result["voice_audio_path"]
            if "voice_backup_paths" in voice_result:
                user_db_data["voice_backup_paths"] = voice_result["voice_backup_paths"]
            if "backup_user_id" in voice_result:
                user_db_data["backup_user_id"] = voice_result["backup_user_id"]
            
            # Add additional user data (user type, class, phone)
            if additional_data:
                user_db_data.update(additional_data)
                self.console.print(f"[dim]📋 Additional data included: {list(additional_data.keys())}[/dim]")
            
            db_result = self._save_user_to_database(user_db_data)
            
            if not db_result["success"]:
                return {
                    "success": False,
                    "error": db_result["error"],
                    "stage": "database_save"
                }
            
            # Success!
            self.console.print(f"[bold green]✅ REGISTRATION SUCCESSFUL![/bold green]")
            self.console.print(f"User ID: [bold cyan]{db_result['user_id']}[/bold cyan]")
            self.console.print(f"Photos: [bold magenta]{len(face_result['embeddings'])} x 512D[/bold magenta]")
            self.console.print(f"Voice: [bold magenta]1 x 256D[/bold magenta]")
            
            return {
                "success": True,
                "user_id": db_result["user_id"],
                "face_embeddings_count": len(face_result["embeddings"]),
                "voice_embedding_dimension": len(voice_result["embedding"]),
                "photo_folder": user_folder,
                "stage": "complete"
            }
            
        except Exception as e:
            self.console.print(f"[bold red]❌ Registration failed: {e}[/bold red]")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "stage": "exception"
            }
    
    def _validate_registration_data(self, name: str, email: str) -> Dict[str, Any]:
        """Unified validation logic"""
        if not name or not name.strip():
            return {"valid": False, "error": "Name is required"}
        
        if not email or not email.strip():
            return {"valid": False, "error": "Email is required"}
        
        # Basic email validation
        if "@" not in email or "." not in email:
            return {"valid": False, "error": "Invalid email format"}
        
        return {"valid": True}
    
    def _check_existing_user(self, email: str) -> Dict[str, Any]:
        """Check if user already exists in database"""
        try:
            db = get_db()
            if db is None:
                return {"available": False, "error": "Database connection failed"}
            
            existing = db.users.find_one({"email": email.strip().lower()})
            
            if existing:
                return {
                    "available": False,
                    "user_id": str(existing.get("_id")),
                    "name": existing.get("name")
                }
            
            return {"available": True}
            
        except Exception as e:
            return {"available": False, "error": f"Database check failed: {str(e)}"}
    
    def _create_user_folder(self, name: str) -> str:
        """Create standardized user folder for photos"""
        safe_name = "".join(c for c in name if c.isalnum() or c in " _-")
        safe_name = safe_name.strip().replace(" ", "_")
        user_folder = os.path.join("captured_images", safe_name)
        os.makedirs(user_folder, exist_ok=True)
        
        self.console.print(f"[cyan]📁 Created user folder: {user_folder}/[/cyan]")
        return user_folder
    
    def _process_face_data(self, face_data: Any, source: str, user_folder: str, name: str) -> Dict[str, Any]:
        """
        Unified face processing for both CLI and Flask
        
        Args:
            face_data: Either OpenCV images (CLI) or base64 images (Flask)
            source: "cli" or "flask"
            user_folder: Path to save photos
            name: User name for logging
        """
        try:
            self.console.print(f"[yellow]🔍 Processing face data from {source}...[/yellow]")
            
            if source == "cli":
                return self._process_face_data_cli(face_data, user_folder)
            elif source == "flask":
                return self._process_face_data_flask(face_data, user_folder)
            else:
                return {"success": False, "error": f"Unknown source: {source}"}
                
        except Exception as e:
            return {"success": False, "error": f"Face processing failed: {str(e)}"}
    
    def _process_face_data_cli(self, face_images: List[np.ndarray], user_folder: str) -> Dict[str, Any]:
        """Process face images from CLI (OpenCV format)"""
        if not face_images or len(face_images) != 3:
            return {"success": False, "error": "Exactly 3 face images required"}
        
        embeddings = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, img in enumerate(face_images):
            # Save photo
            photo_name = f"{timestamp}_{i+1}.jpg"
            photo_path = os.path.join(user_folder, photo_name)
            cv2.imwrite(photo_path, img)
            
            # Generate embedding
            embedding = get_face_embedding(img)
            if embedding is None:
                return {"success": False, "error": f"Failed to generate embedding for photo {i+1}"}
            
            embeddings.append(embedding.tolist())
            self.console.print(f"[green]✅ Processed photo {i+1}/3[/green]")
        
        return {
            "success": True,
            "embeddings": embeddings,
            "photos_saved": len(face_images)
        }
    
    def _process_face_data_flask(self, face_data: Dict, user_folder: str) -> Dict[str, Any]:
        """Process face images from Flask (base64 format)"""
        face_embeddings = face_data.get('faceEmbeddings', [])
        face_images = face_data.get('faceImages', [])
        
        if len(face_embeddings) != 3:
            return {"success": False, "error": "Exactly 3 face embeddings required"}
        
        if len(face_images) != 3:
            return {"success": False, "error": "Exactly 3 face images required"}
        
        # Save images in standardized format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, image_data in enumerate(face_images):
            try:
                # Decode base64 image
                if ',' in image_data:
                    image_data = image_data.split(',')[1]
                
                import base64
                img_data = base64.b64decode(image_data)
                photo_name = f"{timestamp}_{i+1}.jpg"
                photo_path = os.path.join(user_folder, photo_name)
                
                with open(photo_path, 'wb') as f:
                    f.write(img_data)
                
                self.console.print(f"[green]✅ Saved photo {i+1}/3[/green]")
                
            except Exception as e:
                return {"success": False, "error": f"Failed to save photo {i+1}: {str(e)}"}
        
        return {
            "success": True,
            "embeddings": face_embeddings,
            "photos_saved": len(face_images)
        }
    
    def _process_voice_data(self, voice_data: Any, source: str, name: str) -> Dict[str, Any]:
        """
        Unified voice processing for both CLI and Flask
        
        Args:
            voice_data: Either None (CLI records live) or processed embedding (Flask)
            source: "cli" or "flask"
            name: User name for voice prompt
        """
        try:
            self.console.print(f"[yellow]🎤 Processing voice data from {source}...[/yellow]")
            
            if source == "cli":
                return self._process_voice_data_cli(name)
            elif source == "flask":
                return self._process_voice_data_flask(voice_data)
            else:
                return {"success": False, "error": f"Unknown source: {source}"}
                
        except Exception as e:
            return {"success": False, "error": f"Voice processing failed: {str(e)}"}
    
    def _process_voice_data_cli(self, name: str) -> Dict[str, Any]:
        """Process voice data from CLI (live recording) - UPGRADED TO ECAPA-TDNN"""
        self.console.print(f"[cyan]🎤 Say clearly: \"Hello, My name is {name}\"[/cyan]")
        
        try:
            # Generate temporary user_id for backup purposes (use name as base)
            import hashlib
            temp_user_id = hashlib.md5(name.encode()).hexdigest()[:8]
            
            # Use UPGRADED ECAPA-TDNN system with backup support
            voice_embedding, best_audio_clip, audio_backup_paths = record_and_embed_three_times(
                duration_per_clip=7.0,
                user_id=temp_user_id,
                user_name=name
            )
            
            if voice_embedding is None:
                return {"success": False, "error": "Voice recording failed"}
            
            # Save best voice clip as legacy .wav file
            from datetime import datetime
            import soundfile as sf
            import os
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
            voice_filename = f"{safe_name}_{timestamp}_voice.wav"
            voice_path = os.path.join("captured_voices", voice_filename)
            
            # Ensure directory exists
            os.makedirs("captured_voices", exist_ok=True)
            
            # Save legacy voice file
            sf.write(voice_path, best_audio_clip, samplerate=16000)
            self.console.print(f"[green]✅ Voice file saved: {voice_path}[/green]")
            
            self.console.print("[green]✅ Voice embedding generated (192D ECAPA-TDNN)[/green]")
            
            return {
                "success": True,
                "embedding": voice_embedding.tolist(),
                "clips_used": 3,
                "voice_audio_path": voice_path,
                "voice_backup_paths": audio_backup_paths,
                "backup_user_id": temp_user_id
            }
            
        except Exception as e:
            return {"success": False, "error": f"Voice enrollment failed: {str(e)}"}
    
    def _process_voice_data_flask(self, voice_data: Dict) -> Dict[str, Any]:
        """Process voice data from Flask (pre-processed embedding)"""
        voice_embedding = voice_data.get('voiceEmbedding')
        
        if not voice_embedding:
            return {"success": False, "error": "Voice embedding required"}
        
        # Validate embedding format
        if not isinstance(voice_embedding, list) or len(voice_embedding) == 0:
            return {"success": False, "error": "Invalid voice embedding format"}
        
        self.console.print("[green]✅ Voice embedding validated (192D ECAPA-TDNN)[/green]")
        
        return {
            "success": True,
            "embedding": voice_embedding,
            "clips_used": 3  # Flask processes 3 clips into final embedding
        }
    
    def _save_user_to_database(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Unified database saving logic"""
        try:
            self.console.print("[yellow]💾 Saving user to database...[/yellow]")
            
            result = save_user(user_data)
            
            if result and result.inserted_id:
                self.console.print("[green]✅ User saved to database[/green]")
                return {
                    "success": True,
                    "user_id": str(result.inserted_id)
                }
            else:
                return {"success": False, "error": "Failed to save user to database"}
                
        except Exception as e:
            return {"success": False, "error": f"Database save failed: {str(e)}"}

# Global instance for easy import
registration_service = RegistrationService()