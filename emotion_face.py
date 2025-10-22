# emotion_face.py

import tkinter as tk
import pyttsx3

class EmotionFace:
    def __init__(self):
        # Define emoji faces
        self.faces = {
            "happy": "😊",
            "sad": "😢",
            "angry": "😠",
            "surprised": "😮",
            "neutral": "😐"
        }

        # Initialize TTS engine
        self.engine = pyttsx3.init()

        # Setup GUI
        self.root = tk.Tk()
        self.root.title("Raphael Emotion Face")

        self.label_face = tk.Label(self.root, text="😐", font=("Arial", 100))
        self.label_face.pack(pady=20)

        self.label_status = tk.Label(self.root, text="Waiting...", font=("Arial", 14))
        self.label_status.pack(pady=10)

        # Optional: Run GUI in non-blocking mode
        self.root.after(100, self.update_gui)
    
    def update_gui(self):
        self.root.update()
        self.root.after(100, self.update_gui)

    def update_face(self, emotion, text_feedback=None, speak=True):
        """
        Updates the face based on emotion.
        :param emotion: 'happy', 'sad', 'angry', 'surprised', or 'neutral'
        :param text_feedback: Optional status text to show
        :param speak: If True, say the feedback with TTS
        """
        if emotion not in self.faces:
            emotion = "neutral"

        self.label_face.config(text=self.faces[emotion])
        if text_feedback:
            self.label_status.config(text=text_feedback)
        else:
            self.label_status.config(text=f"Emotion detected: {emotion}")

        if speak:
            self.engine.say(f"I see you are {emotion}")
            self.engine.runAndWait()

    def run(self):
        """Keeps the GUI running (blocking call) if needed standalone."""
        self.root.mainloop()
