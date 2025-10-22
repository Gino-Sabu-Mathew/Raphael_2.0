# raphael_sounddevice.py
# ==========================
# pip install sounddevice scipy SpeechRecognition pyttsx3

import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import speech_recognition as sr
import pyttsx3
import tempfile
import os

from raphael_brain import RaphaelBrain
import random

# Initialize Raphael's brain
brain = RaphaelBrain()

# Initialize speech engine
tts_engine = pyttsx3.init('sapi5')
voices = tts_engine.getProperty('voices')
tts_engine.setProperty('voice', voices[0].id)  # pick a voice

recognizer = sr.Recognizer()

# === TTS function ===
def speak(text):
    print(f"Raphael: {text}")
    tts_engine.say(text)
    tts_engine.runAndWait()
    # tts_engine.stop()

# === Mood inference ===
def infer_mood(text):
    text = text.lower()
    mood = {"valence": 0.0, "topics": []}

    sad_words = ["sad", "tired", "alone", "depress", "fail", "worthless"]
    happy_words = ["happy", "good", "excited", "love", "joy", "great"]

    for w in sad_words:
        if w in text:
            mood["valence"] -= 0.3
    for w in happy_words:
        if w in text:
            mood["valence"] += 0.3

    if "work" in text or "job" in text:
        mood["topics"].append("work")
    else:
        mood["topics"].append("general")

    mood["valence"] = max(-1.0, min(1.0, mood["valence"]))
    return mood

# === Safety check ===
def safety_check(text):
    danger_words = ["suicide", "kill myself", "end my life", "hurt myself"]
    for w in danger_words:
        if w in text.lower():
            return True
    return False

# === Generate response using brain + mood ===
def generate_response(text):
    if safety_check(text):
        return "It sounds like you are in serious distress. Please contact local emergency services or a crisis hotline immediately."

    mood = infer_mood(text)
    valence = mood["valence"]

    # Emotional touch
    if valence < -0.3:
        mood_reply = "I hear you — that sounds tough. I'm here with you. "
    elif valence > 0.3:
        mood_reply = "That’s wonderful! I’m really happy for you. "
    else:
        mood_reply = ""

    # Get brain's intelligent reply
    smart_reply = brain.ask(text)
    return mood_reply + smart_reply

# === Voice input ===
def listen(duration=5, fs=16000):
    speak("I'm listening...")
    print("🎤 Speak now...")

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

# === Main loop ===
def main():
    speak("Hi, I am Raphael. How was your day?")

    while True:
        user_input = listen()
        print(f"You said: {user_input}")
        reply = generate_response(user_input)
        speak(reply)

if __name__ == "__main__":
    main()


