# Anti-Gravity — Splash Screen
# Shown on app startup while assets and profile are loading.

from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.properties import NumericProperty


class SplashScreen(Screen):
    """
    Animated splash screen.
    Displays the title with a pulsing animation, then navigates to the Home screen.
    """

    alpha = NumericProperty(0.0)

    def on_enter(self):
        self.alpha = 0.0
        anim = Animation(alpha=1.0, duration=1.2)
        anim.bind(on_complete=self._start_delay)
        anim.start(self)

    def _start_delay(self, *args):
        Clock.schedule_once(self._go_home, 1.5)

    def _go_home(self, *args):
        self.manager.current = "home"
