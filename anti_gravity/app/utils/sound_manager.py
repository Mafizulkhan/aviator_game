"""
Anti-Gravity — Sound Manager
Handles sound-effect and music playback.
Falls back silently when audio files are missing or in non-Kivy test environments.
"""
import os

try:
    from kivy.core.audio import SoundLoader
except ImportError:
    class SoundLoader:
        @staticmethod
        def load(path):
            return None

from app.config import SOUND_ENABLED_DEFAULT, MUSIC_ENABLED_DEFAULT, VOLUME_DEFAULT

_SOUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sounds")


class SoundManager:
    """Singleton-style sound manager. Call SoundManager.get() for the shared instance."""

    _instance = None

    def __init__(self):
        self.sfx_enabled: bool = SOUND_ENABLED_DEFAULT
        self.music_enabled: bool = MUSIC_ENABLED_DEFAULT
        self.volume: float = VOLUME_DEFAULT
        self._cache: dict = {}

    @classmethod
    def get(cls) -> "SoundManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self, name: str):
        if name in self._cache:
            return self._cache[name]
        path = os.path.join(_SOUNDS_DIR, name)
        snd = SoundLoader.load(path) if os.path.exists(path) else None
        self._cache[name] = snd
        return snd

    def play(self, name: str):
        if not self.sfx_enabled:
            return
        snd = self._load(name)
        if snd:
            try:
                snd.volume = self.volume
                snd.play()
            except Exception:
                pass

    # Convenience shortcuts
    def click(self):       self.play("button_click.wav")
    def round_start(self): self.play("round_start.wav")
    def tick(self):        self.play("multiplier_tick.wav")
    def cashout(self):     self.play("cashout.wav")
    def warning(self):     self.play("warning.wav")
    def crash(self):       self.play("crash.wav")
    def win(self):         self.play("win.wav")
