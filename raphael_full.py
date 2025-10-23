# raphael_full.py - FINAL CODE WITH NON-BLOCKING, THREAD-SAFE TTS FIX
# =======================================================================
import threading
import tempfile
import os
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import speech_recognition as sr
import pyttsx3
import time
import tkinter as tk
import concurrent.futures

from raphael_brain import RaphaelBrain # NOTE: Assumes this is functional
from graph import NeuralActivityVisualizer

# Set the timeout limit for core AI processing
AI_PROCESSING_TIMEOUT = 5 

# Define a constant for the timeout signal
TIMEOUT_SIGNAL = "[TIMEOUT_OCCURRED]"

state = "idle"

# -----------------------
# EmotionFace Class (with Thread-Safety & Fix for Missing Emotion)
# -----------------------
class EmotionFace:
    # (EmotionFace Class remains unchanged)
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Raphael")
        self.root.geometry("250x300")
        self.face_label = tk.Label(self.root, text="", font=("Arial", 80))
        self.face_label.pack(pady=10)
        self.status_label = tk.Label(self.root, text="Waiting...", font=("Arial", 14))
        self.status_label.pack(pady=10)
        self.faces = {
            "happy": "😊",
            "sad": "😢",
            "neutral": "😐",
            "thinking": "🤔",
            "angry": "😡",
            "surprised": "😮",
            "fearful": "😨",
        }
        self.current_emotion = "neutral"
        self.thinking = False

    def update_face(self, emotion, text_feedback="", speak=False):
        """Schedule the GUI update to run safely on the main thread (Tkinter thread-safety)."""
        self.root.after(0, self._safe_update, emotion, text_feedback, speak)

    def _safe_update(self, emotion, text_feedback, speak):
        """The actual update logic that runs on the main thread."""
        self.current_emotion = emotion
        self.status_label.config(text=text_feedback)
        
        if emotion == "thinking":
            if not self.thinking:
                self.thinking = True
                threading.Thread(target=self._animate_thinking, daemon=True).start()
        else:
            # FIX 2: Ensures the final emotion is displayed immediately upon leaving 'thinking'
            self.thinking = False 
            self.face_label.config(text=self.faces.get(emotion, "😐"))
            
    def _animate_thinking(self):
        """Cycle between 🤔 and 😐 to simulate blinking/thinking."""
        symbols = ["🤔", "😐", "🤔", "😐"]
        while self.thinking:
            for s in symbols:
                if not self.thinking:
                    break
                    
                # Use lambda for thread-safe Tkinter updates
                self.root.after(0, lambda symbol=s: self.face_label.config(text=symbol))
                time.sleep(0.6)
                
        # IMPORTANT: No need for a final face update here, as _safe_update handles it when self.thinking is set to False

    def run(self):
        self.root.mainloop()

# -----------------------
# Initialize components
# -----------------------
# NOTE: The initialization for brain, recognizer, and GUI must stay outside of functions
# to be shared globally across threads.
try:
    brain = RaphaelBrain()
except NameError:
    print("WARNING: RaphaelBrain class not found. AI functionality will fail.")
    # Create a mock brain for testing if needed
    class MockBrain:
        def ask(self, prompt):
            if "Analyze the emotion" in prompt: return "neutral"
            return "I need a functional RaphaelBrain to answer that question."
    brain = MockBrain()

face = EmotionFace() # GUI

recognizer = sr.Recognizer()

# -----------------------
# TTS Function (REVISED FIX: Dedicated Threaded Speak for Reliability)
# -----------------------

# Global flag and Lock to manage TTS state and prevent overlap
tts_lock = threading.Lock()
tts_thread_active = False

def _tts_worker(text):
    """The actual function that runs in a new thread to speak the text."""
    global tts_thread_active
    print(f"Raphael: {text}")

    local_engine = None
    try:
        # Initialize the engine
        local_engine = pyttsx3.init('sapi5')
        voices = local_engine.getProperty('voices')
        if voices:
            local_engine.setProperty('voice', voices[0].id)
        
        # Start speaking
        local_engine.say(text)
        local_engine.runAndWait()

    except Exception as e:
        print(f"[TTS Error: {e}]")
    finally:
        # Clean up the engine and release the lock/flag
        if local_engine:
            try:
                local_engine.stop()
            except:
                pass
        
        with tts_lock:
            tts_thread_active = False

def speak(text):
    global state

    state = "speaking"

    """Starts the speaking process in a new, non-blocking thread."""
    global tts_thread_active
    
    # Wait until the previous speech finishes before starting a new one
    # This prevents pyttsx3 calls from piling up and causing locks
    while True:
        with tts_lock:
            if not tts_thread_active:
                tts_thread_active = True
                break
        time.sleep(0.1) # Wait a little before checking the lock again
        
    threading.Thread(target=_tts_worker, args=(text,), daemon=True).start()
    
    # We must block the main_loop thread here until speaking is complete,
    # otherwise the main loop will immediately proceed to listen() while the AI is speaking.
    # The simplest way is to wait for the tts_thread_active flag to become False again.
    while True:
        with tts_lock:
            if not tts_thread_active:
                break
        time.sleep(0.1)


# -----------------------
# Safety Check
# -----------------------
def safety_check(text):
    danger_words = ["suicide", "kill myself", "end my life", "hurt myself"]
    return any(w in text.lower() for w in danger_words)

# -----------------------
# Brain-Based Emotion Detection (Helper)
# -----------------------
def analyze_and_respond(text):
    global state
    state = "thinking"
    try:
        # ----- Unified Prompt -----
        prompt = f"""
        You are Raphael, a helpful and emotionally intelligent AI assistant.

        Analyze the user's message below and do TWO things in your response:
        1. Provide a natural, empathetic, and factual reply to the user.
        2. Identify the primary emotion expressed by the user as one of:
           happy, sad, angry, surprised, fearful, or neutral.

        Respond strictly in this JSON format:
        {{
            "response": "<your reply here>",
            "emotion": "<one of: happy, sad, angry, surprised, fearful, neutral>"
        }}

        User says: "{text}"
        """

        raw_output = brain.ask(prompt)

        # ----- Parse Output -----
        import json, re
        try:
            # Try parsing as JSON first
            data = json.loads(raw_output)
        except Exception:
            # Fallback: extract manually if model didn't return perfect JSON
            response_match = re.search(r'"response"\s*:\s*"(.*?)"', raw_output, re.DOTALL)
            emotion_match = re.search(r'"emotion"\s*:\s*"(.*?)"', raw_output, re.DOTALL)
            data = {
                "response": response_match.group(1).strip() if response_match else raw_output.strip(),
                "emotion": emotion_match.group(1).strip().lower() if emotion_match else "neutral"
            }

        emotion = data.get("emotion", "neutral").lower()
        if emotion not in ["happy", "sad", "angry", "surprised", "fearful", "neutral"]:
            emotion = "neutral"

        response = data.get("response", "I'm here to help.")

        print(f"Emotion: {emotion}")
        print(f"Response: {response}")

        return {"emotion": emotion, "response": response}

    except Exception as e:
        print(f"[Unified Analysis Error: {e}]")
        return {"emotion": "neutral", "response": "Sorry, I had trouble understanding that."}


# -----------------------
# Voice Input Function
# -----------------------
def listen(duration=5, fs=16000):
    global state
    state = "listening"

    print("🎤 Speak now (5 seconds max)...")
    # Reduced duration might be better but 5s is kept as per original code
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        wav.write(temp_file.name, fs, recording)
        filename = temp_file.name
    with sr.AudioFile(filename) as source:
        audio = recognizer.record(source)
    os.remove(filename)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "[could not understand]"
    except sr.RequestError:
        return "[speech service unavailable]"

# -----------------------
# Generate AI Response (Concurrent Processing & Latency Fix with Timeout)
# -----------------------
def generate_response(text):
    global state
    state = "thinking"

    if safety_check(text):
        face.update_face("sad", text_feedback="Safety Protocol Activated")
        return "It sounds like you are in serious distress. Please contact local emergency services or a crisis hotline immediately."

    # 1. Update face to "thinking" state
    face.update_face("thinking", text_feedback="Raphael is thinking...", speak=False)

    # Default values
    user_emotion = "neutral"
    smart_reply = "I'm sorry, I couldn't generate a response."

    # Use ThreadPoolExecutor to run unified brain call in parallel (in case you add other async tasks later)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        unified_future = executor.submit(analyze_and_respond, text)

        try:
            result = unified_future.result(timeout=AI_PROCESSING_TIMEOUT)
            smart_reply = result.get("response", smart_reply)
            user_emotion = result.get("emotion", user_emotion)

            print(f"Smart Reply: {smart_reply}")
            print(f"Detected Emotion: {user_emotion}")

        except concurrent.futures.TimeoutError:
            print(f"[Core AI Processing Error: Timeout after {AI_PROCESSING_TIMEOUT}s]")
            return TIMEOUT_SIGNAL

        except Exception as e:
            print(f"[Core AI Processing Error: {e}]")
            smart_reply = "I’m sorry, something went wrong while I was processing that."

    # 2. Sanitize reply and emotion
    if not isinstance(smart_reply, str):
        print(f"--- DEBUG: Raw Brain Reply: {smart_reply} (Type: {type(smart_reply).__name__}) ---")
        smart_reply = "I apologize, I didn't get a clear response for that request."
    else:
        print(f"--- DEBUG: Raw Brain Reply: '{smart_reply.strip()}' ---")

    # 3. Update user emotion visually
    face.update_face(user_emotion, text_feedback=f"You sound {user_emotion}", speak=False)
    print(f"[User Emotion Detected: {user_emotion}]")

    # 4. Add empathetic prefix to make Raphael feel alive
    empathy_prefix = {
        "sad": "I'm so sorry to hear that. ",
        "happy": "That’s wonderful! ",
        "angry": "I can sense your frustration. ",
        "fearful": "That sounds scary, but you’re not alone. ",
        "surprised": "Wow, that’s unexpected! "
    }.get(user_emotion, "")

    final_reply = empathy_prefix + smart_reply

    # 5. Determine Raphael's visual emotion (how he reacts)
    ai_emotion_map = {
        "sad": "sad",
        "happy": "happy",
        "angry": "neutral",
        "fearful": "sad",
        "surprised": "neutral",
        "neutral": "neutral",
    }
    ai_emotion = ai_emotion_map.get(user_emotion, "neutral")

    # 6. Update Raphael’s emotion display
    face.update_face(ai_emotion, text_feedback=f"Raphael feels {ai_emotion}", speak=False)
    print(f"[Raphael's Emotion: {ai_emotion}]")

    return final_reply


# -----------------------
# Main Interaction Loop (Synchronous/Sequential Flow)
# -----------------------
def main_loop():
    # Initial greeting uses the fixed speak function
    speak("Hi, I am Raphael. How was your day?") 
    while True:
        # 1. BLOCKING: Wait for the user to speak
        user_input = listen()
        print(f"You said: {user_input}")
        
        # Check if input was understood before processing
        if user_input.startswith("[could not understand]"):
            speak("I'm sorry, I couldn't understand what you said. Could you please repeat that?")
            # We explicitly wait for the speak to finish here to ensure the user hears the prompt
            continue
        elif user_input.startswith("[speech service unavailable]"):
             speak("My speech recognition service is currently unavailable. Please check your internet connection.")
             continue

        # 2. BLOCKING: Process the input and generate the reply (concurrent internally, with 5s timeout)
        reply = generate_response(user_input) 
        
        # Check for the timeout signal
        if reply == TIMEOUT_SIGNAL:
            # If a timeout occurred, print the message and immediately restart the loop (go back to listen)
            print("Raphael: Processing timed out. Please try speaking again immediately.")
            face.update_face("neutral", text_feedback="Processing timed out! Please speak now.")
            # Skip the speak call and continue to listen()
            continue

        # 3. BLOCKING: Speak the reply (uses the fixed speak function)
        speak(reply)
        
# -----------------------
# Run GUI and AI threads
# -----------------------
if __name__ == "__main__":

    # Global visualizer instance
    viz = None

    def state_monitor():
        """
        Continuously monitors the global 'state' variable and updates the visualizer.
        """
        global state, viz
        
        previous_state = None
        
        # Wait for viz to be initialized
        while viz is None:
            time.sleep(0.1)
        
        while True:
            current_state = state
            
            # Only update if state has changed
            if current_state != previous_state:
                if current_state == "listening":
                    viz.listening()
                elif current_state == "thinking":
                    viz.thinking()
                elif current_state == "speaking":
                    viz.speaking()
                elif current_state == "idle":
                    viz.idle()
                
                previous_state = current_state
            
            time.sleep(0.1)  # Check every 100ms

    def start_visualizer():
        """
        Initializes and displays the neural activity visualizer in a separate thread.
        """
        global viz
        
        viz = NeuralActivityVisualizer()
        viz.show()  # This blocks, but only this thread

    # Start the state monitor thread
    monitor_thread = threading.Thread(target=state_monitor, daemon=True)
    monitor_thread.start()
    
    # Start the visualizer in a separate thread
    viz_thread = threading.Thread(target=start_visualizer, daemon=True)
    viz_thread.start()
    
    # Give the visualizer a moment to initialize
    time.sleep(1)
    
    # Start the main interaction loop on a dedicated thread
    threading.Thread(target=main_loop, daemon=True).start()
    
    # Start the GUI on the main thread (this blocks, but everything else is already running)
    face.run()