from gtts import gTTS
import tempfile
import threading
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"  # Hide pygame's welcome message, remind me to remove this later, they deserve recognize, thank you for the fast tts
import pygame
import tkinter as tk

volume = 0.25
subtitles = True
_AUDIO_READY = False
_AUDIO_INIT_ERROR = None


def _ensure_audio_ready():
    global _AUDIO_READY, _AUDIO_INIT_ERROR
    if _AUDIO_READY:
        return True
    if _AUDIO_INIT_ERROR:
        return False
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        _AUDIO_READY = True
        return True
    except Exception as e:
        _AUDIO_INIT_ERROR = e
        print(f"Audio init failed. Continuing without audio playback: {e}")
        return False

class TransparentSubtitlesWindow:
    def __init__(self, text):
        self.root = tk.Tk()
        self.text = text
        self.label = tk.Label(self.root, text=self.text, font=('Helvetica', 16), fg='white', bg='black')
        self.label.pack()

        # Set the window to be always on top, transparent, and without decorations
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', 'black')

        # Set window position
        self.root.geometry('+%d+%d' % (self.root.winfo_screenwidth() // 2 - self.label.winfo_reqwidth() // 2,
                                       self.root.winfo_screenheight() - 100))
        self.update()

    def update(self):
        self.label.configure(text=self.text)
        self.root.update_idletasks()
        self.root.update()

    def change_text(self, new_text, duration):
        self.text = new_text
        self.update()

        # Schedule removing the text after the duration
        self.root.after(duration, lambda: self.label.configure(text=""))

    def close(self):
        self.root.quit()  # changed from destroy() to quit()


def calculate_duration_of_speech(text, lang='en', wpm=150):
    """Estimate the duration the subtitles should be displayed based on words per minute (WPM)"""
    words = text.split()
    word_count = len(words)
    duration_in_seconds = (word_count / wpm) * 60
    return int(duration_in_seconds * 1000)  # Convert to milliseconds for tkinter's after method


def play_audio(file_path, text, lang='en'):
    # Estimate the duration the subtitles should be shown
    duration = calculate_duration_of_speech(text, lang)

    if not _ensure_audio_ready():
        if os.path.exists(file_path):
            os.remove(file_path)
        return

    try:
        # Load and play audio file
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play()

        # When the audio finishes, stop the mixer and remove the temporary file
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


def set_volume(volume_level):
    global volume
    volume = volume_level
    if _ensure_audio_ready():
        pygame.mixer.music.set_volume(volume)

def set_subtitles(subtitles_bool):
    global subtitles
    subtitles = subtitles_bool


def speaker(text, lang='en'):
    def run_tts_pipeline():
        pygame.init()

        temp_file_path = None
        try:
            # Temporary mp3 file creation
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_file_path = fp.name

            tts = gTTS(text=text, lang=lang)
            tts.save(temp_file_path)

            # Start the subtitles thread
            if subtitles is True:
                def setup_subtitles():
                    window = TransparentSubtitlesWindow(text)
                    window.change_text(text, calculate_duration_of_speech(text, lang))
                    window.root.mainloop()

                subtitles_thread = threading.Thread(target=setup_subtitles, daemon=True)
                subtitles_thread.start()

            play_audio(temp_file_path, text, lang)
        except Exception as e:
            print(f"Speaker pipeline error: {e}")
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    # Run the entire TTS pipeline asynchronously to avoid blocking the UI thread.
    worker_thread = threading.Thread(target=run_tts_pipeline, daemon=True)
    worker_thread.start()
    return worker_thread, None


if __name__ == '__main__':
    text_to_speak = "Hello, this is a test."
    speaker(text_to_speak)
    # Main script can do other tasks here, threads will not prevent script from exiting