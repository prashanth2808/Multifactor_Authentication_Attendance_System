// Server-Side Voice Recording JavaScript (CLI Mode)
// Uses backend microphone only - same as CLI register.py

// Configuration - Server-side recording only (like CLI)
const RECORDING_MODE = "server"; // Backend microphone only

// Registration State - Following register.py workflow (server-side recording)
let userData = { name: '', email: '' };
let faceData = { images: [], embeddings: [], count: 0 };
let voiceData = { clips: [], embedding: null, count: 0 };
let videoStream = null;
let isCapturingFaces = false;

// Remove any Skip Voice button defensively if present in DOM
document.addEventListener('DOMContentLoaded', () => {
  const byId = document.getElementById('skipVoiceBtn');
  if (byId) byId.remove();
  document.querySelectorAll('.btn-voice-skip').forEach(el => el.remove());
});
// Removed client-side audio variables (mediaRecorder, audioChunks, isRecordingVoice)

// Main registration workflow (following register.py logic)
async function startBiometricEnrollment() {
    const name = document.getElementById('userName').value.trim();
    const email = document.getElementById('userEmail').value.trim();
    
    if (!name || !email) {
        showStatus('emailStatus', 'Please fill in all required fields', 'error');
        return;
    }
    
    if (!isValidEmail(email)) {
        showStatus('emailStatus', 'Please enter a valid email address', 'error');
        return;
    }
    
    // Check email availability (same as register.py)
    try {
        showStatus('emailStatus', 'Checking email availability...', 'info');
        
        const response = await fetch('/api/register/check-email', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({email: email})
        });
        
        const result = await response.json();
        
        if (result.exists) {
            showStatus('emailStatus', 'This email is already registered', 'error');
            return;
        }
        
        // Save user data
        userData.name = name;
        userData.email = email;
        
        showStatus('emailStatus', 'Email available ✓', 'success');
        
        // Hide user details and show biometric section
        document.getElementById('userDetailsSection').classList.add('hidden');
        document.getElementById('biometricSection').classList.remove('hidden');
        document.getElementById('nameForVoice').textContent = name;
        
        // Update progress
        updateProgress(25);
        
        // Start face capture automatically (like register.py burst mode)
        await startAutomatedFaceCapture();
        
    } catch (error) {
        showStatus('emailStatus', 'Error checking email availability', 'error');
        console.error('Email check error:', error);
    }
}

// Automated Face Capture - Following register.py capture_face_burst() logic
async function startAutomatedFaceCapture() {
    try {
        showStatus('faceStatus', '📷 Initializing camera...', 'info');
        
        // Initialize camera (same as register.py)
        videoStream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480 } 
        });
        document.getElementById('video').srcObject = videoStream;
        
        showStatus('faceStatus', '📷 Camera ready - Position your face and press SPACE', 'info');
        document.getElementById('faceInstructions').classList.remove('hidden');
        
        // Update video status
        updateVideoStatus('Ready - Press SPACE', true);
        
        // Listen for SPACE key (same as register.py)
        document.addEventListener('keydown', handleFaceCapture);
        
    } catch (error) {
        showStatus('faceStatus', 'Camera access denied. Please enable camera permissions.', 'error');
        console.error('Camera error:', error);
    }
}

// Handle face capture with SPACE key (following register.py logic)
async function handleFaceCapture(event) {
    if (event.code === 'Space' && !isCapturingFaces) {
        event.preventDefault();
        isCapturingFaces = true;
        document.removeEventListener('keydown', handleFaceCapture);
        
        showStatus('faceStatus', '📷 Starting automated capture in 3 seconds...', 'info');
        document.getElementById('faceInstructions').classList.add('hidden');
        
        // Update video status
        updateVideoStatus('Capturing photos...', true);
        
        // 3-second countdown (same as register.py)
        for (let i = 3; i > 0; i--) {
            showStatus('faceStatus', `📷 Capturing in ${i}...`, 'info');
            await sleep(1000);
        }
        
        // Capture 3 photos automatically (same as register.py)
        for (let i = 0; i < 3; i++) {
            showStatus('faceStatus', `📸 Capturing photo ${i + 1}/3...`, 'info');
            
            const success = await captureSingleFace(i + 1);
            if (!success) {
                showStatus('faceStatus', `❌ Failed to capture photo ${i + 1}. Retrying...`, 'error');
                i--; // Retry this photo
                await sleep(1000);
                continue;
            }
            
            await sleep(500); // Brief pause between photos
        }
        
        // All face photos captured - move to voice
        showStatus('faceStatus', '✅ All 3 face photos captured successfully!', 'success');
        
        // Hide video status
        updateVideoStatus('Face capture complete', false);
        
        updateProgress(60);
        
        // Start voice recording automatically
        await startAutomatedVoiceRecording();
    }
}

// Capture single face photo and process (following register.py logic)
async function captureSingleFace(photoNumber) {
    try {
        const video = document.getElementById('video');
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0);
        
        const imageData = canvas.toDataURL('image/jpeg', 0.8);
        
        // Send to backend for embedding generation (same as register.py)
        const response = await fetch('/api/register/process-face', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({image: imageData})
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Store face data
            faceData.images.push(imageData);
            faceData.embeddings.push(result.embedding);
            faceData.count++;
            
            // Update UI
            document.getElementById(`face${photoNumber}`).classList.add('success');
            document.getElementById(`face${photoNumber}`).innerHTML = 
                `<div class="icon">✅</div><div class="title">Photo ${photoNumber}</div>`;
            
            return true;
        } else {
            console.error('Face processing failed:', result.error);
            return false;
        }
        
    } catch (error) {
        console.error('Face capture error:', error);
        return false;
    }
}

// DUAL-MODE Voice Recording System
async function startAutomatedVoiceRecording() {
    // Stop camera first
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
    
    showStatus('voiceStatus', '🎤 Starting voice enrollment...', 'info');
    document.getElementById('voiceStatus').classList.remove('hidden');
    
    // Always use server-side recording (CLI mode)
    showStatus('voiceStatus', '🎤 Using backend microphone (CLI mode)', 'info');
    await startServerVoiceRecording();
}

// CLIENT MODE: Removed - Only using server-side recording (CLI mode)

// SERVER MODE: Server-side recording (like CLI register.py)
async function startServerVoiceRecording() {
    try {
        showStatus('voiceStatus', '🎤 Backend microphone: Starting voice enrollment...', 'info');
        // Use single-shot server endpoint that records 3 clips and saves backups like CLI
        const resp = await fetch('/api/register/voice/three-times', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: userData.name, email: userData.email, duration: 7.0 })
        });
        const result = await resp.json();
        if (!result.success) {
            throw new Error(result.error || 'Voice recording failed');
        }
        // Store embedding and backup paths
        voiceData.embedding = result.embedding;
        voiceData.count = result.clips_recorded || 3;
        voiceData.voiceBackupPaths = result.voice_backup_paths || [];
        voiceData.voiceAudioPath = result.voice_audio_path || null;
        voiceData.backupUserId = result.backup_user_id || null;

        // Mark UI steps as successful
        for (let i = 1; i <= 3; i++) {
            const el = document.getElementById(`voice${i}`);
            if (el) {
                el.classList.add('success');
                el.innerHTML = `<div class="icon">✅</div><div class="title">Recording ${i}</div>`;
            }
        }

        showStatus('voiceStatus', '✅ Voice enrollment complete', 'success');
        // Complete registration with server-recorded voice data
        await completeRegistration();
    } catch (e) {
        console.error('Server voice three-times error:', e);
        showStatus('voiceStatus', `❌ Voice recording error: ${e.message}`, 'error');
    }
}

// Client-side recording removed - Using only backend microphone (CLI mode)

// Record single voice clip using server-side recording (LEGACY REMOVED: using only /api/register/voice/three-times)
async function recordServerVoiceClip(clipNumber) {
    try {
        // Start server recording
        const startResponse = await fetch('/api/register/voice/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({duration: 5})
        });
        
        const startResult = await startResponse.json();
        
        if (!startResult.success) {
            throw new Error(startResult.message || 'Failed to start server recording');
        }
        
        showStatus('voiceStatus', `🔴 Server recording ${clipNumber}/3 in progress...`, 'info');
        
        // Poll for recording completion
        let attempts = 0;
        const maxAttempts = 30; // 15 seconds max wait
        
        while (attempts < maxAttempts) {
            await sleep(500);
            attempts++;
            
            const statusResponse = await fetch('/api/register/voice/status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'}
            });
            
            const statusResult = await statusResponse.json();
            
            if (statusResult.recording === 'done' || statusResult.recording === 'error') {
                break;
            }
            
            // Update progress if available
            if (statusResult.progress) {
                showStatus('voiceStatus', `🔴 Server recording ${clipNumber}/3: ${statusResult.progress}%`, 'info');
            }
        }
        
        // Get the recording result
        const resultResponse = await fetch('/api/register/voice/result', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await resultResponse.json();
        
        if (result.success) {
            // Store the embedding directly (server already processed it)
            if (clipNumber === 1) {
                voiceData.embedding = result.embedding;
            }
            
            // Update UI
            document.getElementById(`voice${clipNumber}`).classList.add('success');
            document.getElementById(`voice${clipNumber}`).innerHTML = 
                `<div class="icon">✅</div><div class="title">Recording ${clipNumber}</div>`;
            
            return true;
        } else {
            throw new Error(result.message || 'Server recording failed');
        }
        
    } catch (error) {
        console.error('Server recording error:', error);
        showStatus('voiceStatus', `❌ Server recording error: ${error.message}`, 'error');
        return false;
    }
}

// Client-side voice processing removed - Server processes each clip individually

// Complete Registration (following register.py save_user logic)
async function completeRegistration() {
    try {
        showStatus('voiceStatus', '🔄 Creating your account...', 'info');
        updateProgress(95);
        
        // Prepare registration data (same structure as register.py)
        const registrationData = {
            name: userData.name,
            email: userData.email,
            faceEmbeddings: faceData.embeddings,
            voiceEmbedding: voiceData.embedding,
            faceImages: faceData.images,
            // pass backup info so server can persist paths in DB
            voiceBackupPaths: voiceData.voiceBackupPaths,
            voiceAudioPath: voiceData.voiceAudioPath,
            backupUserId: voiceData.backupUserId
        };
        
        console.log('Submitting registration (register.py style):', {
            name: registrationData.name,
            email: registrationData.email,
            faceEmbeddings: registrationData.faceEmbeddings.length,
            voiceEmbedding: registrationData.voiceEmbedding ? 'Present' : 'Missing',
            faceImages: registrationData.faceImages.length
        });
        
        // Submit to backend (same as register.py save_user)
        const response = await fetch('/api/register/submit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(registrationData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Show completion
            showStatus('voiceStatus', '', 'success');
            document.getElementById('voiceStatus').classList.add('hidden');
            
            document.getElementById('completionMessage').innerHTML = 
                `🎉 <strong>Registration Successful!</strong><br>
                 User ID: ${result.userId}<br>
                 ${result.message}<br>
                 <small>Recording mode: ${RECORDING_MODE}</small>`;
            document.getElementById('completionMessage').classList.remove('hidden');
            
            document.getElementById('completeBtn').classList.remove('hidden');
            document.getElementById('homeBtn').classList.remove('hidden');
            
            updateProgress(100);
        } else {
            throw new Error(result.error || 'Registration failed');
        }
        
    } catch (error) {
        console.error('Registration error:', error);
        showStatus('voiceStatus', `Registration failed: ${error.message}`, 'error');
    }
}

// Utility Functions
function updateProgress(percentage) {
    document.getElementById('progressFill').style.width = percentage + '%';
    
    // Update step indicators based on progress
    const steps = document.querySelectorAll('.progress-step');
    steps.forEach((step, index) => {
        const stepPercentage = (index + 1) * 25; // 25%, 50%, 75%, 100%
        
        if (percentage >= stepPercentage) {
            step.classList.add('completed');
            step.classList.remove('active');
        } else if (percentage >= stepPercentage - 25) {
            step.classList.add('active');
            step.classList.remove('completed');
        } else {
            step.classList.remove('active', 'completed');
        }
    });
    
    // Update step content
    updateStepContent(percentage);
}

function updateStepContent(percentage) {
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');
    const step4 = document.getElementById('step4');
    
    if (percentage >= 100) {
        step4.querySelector('.step-circle').innerHTML = '';
        step4.classList.add('completed');
    }
    if (percentage >= 75) {
        step3.querySelector('.step-circle').innerHTML = '';
        step3.classList.add('completed');
    }
    if (percentage >= 50) {
        step2.querySelector('.step-circle').innerHTML = '';
        step2.classList.add('completed');
    }
    if (percentage >= 25) {
        step1.querySelector('.step-circle').innerHTML = '';
        step1.classList.add('completed');
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function showStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.className = `status-message status-${type}`;
        element.classList.remove('hidden');
    }
}

function updateVideoStatus(message, show = true) {
    const videoStatus = document.getElementById('videoStatus');
    if (videoStatus) {
        videoStatus.textContent = message;
        if (show) {
            videoStatus.classList.add('active');
        } else {
            videoStatus.classList.remove('active');
        }
    }
}

// Handle page unload to cleanup resources
window.addEventListener('beforeunload', () => {
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
    }
    // No client-side mediaRecorder cleanup needed (server-side recording only)
});

// Export functions for global access
// ==================== CLI-REPLICA VOICE REGISTRATION ====================

/**
 * Call the exact CLI register.py voice registration logic
 * This implements record_and_embed_three_times() directly on the backend
 * Just like running: python main.py register
 */
async function startCliVoiceRegistration(userName = 'User', duration = 5.0) {
    try {
        console.log('🎤 Starting CLI-style voice registration...');
        
        // Show user instructions
        alert(`Voice Registration\n\n` +
              `The system will now record 3 voice clips using the exact same process as the CLI.\n\n` +
              `You will hear audio prompts. Please speak clearly:\n` +
              `• Clip 1: "My name is ${userName}"\n` +
              `• Clip 2: "Today is a beautiful day"\n` +
              `• Clip 3: "I am registering for biometric access"\n\n` +
              `Click OK to start recording...`);
        
        const response = await fetch('/api/register/voice/three-times', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: userName,
                duration: duration
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('✅ CLI voice registration successful!');
            console.log('🎯 Voice embedding:', result.voiceEmbedding);
            console.log('📊 Clips recorded:', result.clips_recorded);
            console.log('📏 Embedding shape:', result.embedding_shape);
            
            alert(`Voice Registration Successful!\n\n` +
                  `✅ ${result.clips_recorded} voice clips recorded\n` +
                  `🎯 Voice embedding generated (${result.embedding_shape.join('x')})\n` +
                  `🔢 Embedding quality: ${result.embedding_norm.toFixed(4)}\n\n` +
                  `Your voice profile has been created successfully!`);
            
            return result.voiceEmbedding;
        } else {
            console.error('❌ CLI voice registration failed:', result.error);
            alert(`Voice Registration Failed\n\n${result.error}\n\nPlease try again.`);
            return null;
        }
        
    } catch (error) {
        console.error('❌ Voice registration request failed:', error);
        alert(`Voice Registration Error\n\n${error.message}\n\nPlease check the console and try again.`);
        return null;
    }
}

/**
 * Example usage for complete user registration
 */
async function registerUserWithCliVoice(name, email, faceEmbeddings, faceImages) {
    try {
        console.log('👤 Starting user registration with CLI voice...');
        
        // Step 1: Record voice using CLI method
        const voiceEmbedding = await startCliVoiceRegistration(name);
        
        if (!voiceEmbedding) {
            throw new Error('Voice registration failed');
        }
        
        // Step 2: Submit complete registration
        const response = await fetch('/api/register/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                email: email,
                faceEmbeddings: faceEmbeddings,
                voiceEmbedding: voiceEmbedding,
                faceImages: faceImages
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('🎉 Complete registration successful!');
            alert(`Registration Complete!\n\n` +
                  `✅ User: ${name}\n` +
                  `📧 Email: ${email}\n` +
                  `👤 Face: 3 photos processed\n` +
                  `🎤 Voice: 3 clips processed\n\n` +
                  `User ID: ${result.userId}`);
            return result;
        } else {
            throw new Error(result.error);
        }
        
    } catch (error) {
        console.error('❌ Complete registration failed:', error);
        alert(`Registration Failed\n\n${error.message}`);
        return null;
    }
}

// Export functions for use
window.startCliVoiceRegistration = startCliVoiceRegistration;
window.registerUserWithCliVoice = registerUserWithCliVoice;

window.startBiometricEnrollment = startBiometricEnrollment;