# Anti-Gravity — Settings Screen

from kivy.uix.screenmanager import Screen
from kivy.properties import BooleanProperty, NumericProperty
from app.utils.sound_manager import SoundManager
from app.config import SOUND_ENABLED_DEFAULT, MUSIC_ENABLED_DEFAULT, VOLUME_DEFAULT


class SettingsScreen(Screen):
    sfx_enabled   = BooleanProperty(SOUND_ENABLED_DEFAULT)
    music_enabled = BooleanProperty(MUSIC_ENABLED_DEFAULT)
    volume        = NumericProperty(VOLUME_DEFAULT)

    def on_enter(self):
        sm = SoundManager.get()
        self.sfx_enabled   = sm.sfx_enabled
        self.music_enabled = sm.music_enabled
        self.volume        = sm.volume

    def on_sfx_toggle(self, value: bool):
        SoundManager.get().sfx_enabled = value

    def on_music_toggle(self, value: bool):
        SoundManager.get().music_enabled = value

    def on_volume_change(self, value: float):
        SoundManager.get().volume = value

    def on_back(self):
        SoundManager.get().click()
        self.manager.current = "home"
