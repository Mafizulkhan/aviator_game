# Anti-Gravity — Home Screen

from kivy.uix.screenmanager import Screen
from app.utils.sound_manager import SoundManager


class HomeScreen(Screen):
    """
    Main menu screen.
    Buttons: PLAY, HISTORY, PROFILE, SETTINGS, HOW TO PLAY
    """

    def on_play(self):
        SoundManager.get().click()
        self.manager.current = "game"

    def on_history(self):
        SoundManager.get().click()
        self.manager.current = "history"

    def on_profile(self):
        SoundManager.get().click()
        self.manager.current = "profile"

    def on_settings(self):
        SoundManager.get().click()
        self.manager.current = "settings"

    def on_tutorial(self):
        SoundManager.get().click()
        self.manager.current = "tutorial"
