import tkinter as tk
from tkinter import scrolledtext
import ollama
import threading
from gtts import gTTS
import os
import pygame
import uuid
import speech_recognition as sr


class ChatbotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ollama Chatbot")

        self.chat_window = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled', height=20, width=50)
        self.chat_window.grid(row=0, column=0, padx=10, pady=10)

        self.mic_button = tk.Button(root, text="Spracheingabe", command=self.listen_to_mic)
        self.mic_button.grid(row=1, column=0, padx=10, pady=10)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        pygame.mixer.init()

        # List to keep track of created TTS files
        self.tts_files = []

    def display_message(self, message, color, end='\n'):
        self.chat_window.config(state='normal')
        self.chat_window.insert(tk.END, message + end, color)
        self.chat_window.tag_config(color, foreground=color)
        self.chat_window.yview(tk.END)
        self.chat_window.config(state='disabled')

    def stream_bot_response(self, user_message):
        # Add the instruction to respond in German
        user_message = "Bitte antworte auf Deutsch. " + user_message

        stream = ollama.chat(
            model='llama3',
            messages=[{'role': 'user', 'content': user_message}],
            stream=True,
        )
        self.display_message("Ollama: ", "red", end='')  # Display the prefix without a newline
        bot_message = ""
        for chunk in stream:
            bot_message += chunk['message']['content']
            self.update_display(chunk['message']['content'], "red")

        self.speak(bot_message)

    def update_display(self, message, color):
        self.chat_window.config(state='normal')
        self.chat_window.insert(tk.END, message, color)
        self.chat_window.yview(tk.END)
        self.chat_window.config(state='disabled')

    def speak(self, message):
        # Generate a unique filename for the TTS output
        filename = f"response_{uuid.uuid4()}.mp3"

        # Convert text to speech using gTTS
        tts = gTTS(text=message, lang='de')
        tts.save(filename)

        # Add filename to the list of TTS files
        self.tts_files.append(filename)

        try:
            # Play the MP3 file
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pass
        finally:
            # Ensure the file is closed and removed
            pygame.mixer.music.unload()
            self.cleanup_tts_files(exclude_current=True)

    def cleanup_tts_files(self, exclude_current=False):
        files_to_remove = self.tts_files[:-1] if exclude_current else self.tts_files
        for old_filename in files_to_remove:
            if os.path.exists(old_filename):
                try:
                    os.remove(old_filename)
                except Exception as e:
                    print(f"Error removing file {old_filename}: {e}")

    def listen_to_mic(self):
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.pause_threshold = 2.0

        with sr.Microphone() as source:
            self.display_message("Listening...", "blue")
            try:
                # Listen for speech
                audio_data = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                user_message = recognizer.recognize_google(audio_data, language='de-DE')
                self.display_message(f"Recognized: {user_message}", "green")
                threading.Thread(target=self.stream_bot_response, args=(user_message,)).start()
            except sr.UnknownValueError:
                self.display_message("Google Speech Recognition could not understand audio", "red")
            except sr.RequestError as e:
                self.display_message(f"Could not request results from Google Speech Recognition service; {e}", "red")
            except sr.WaitTimeoutError:
                self.display_message("Listening timed out while waiting for phrase to start", "red")

    def on_closing(self):
        # Remove all TTS files
        self.cleanup_tts_files()

        pygame.quit()
        self.root.quit()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatbotApp(root)
    root.mainloop()
