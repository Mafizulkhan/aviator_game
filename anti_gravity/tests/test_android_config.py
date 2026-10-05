"""
Anti-Gravity — Sprint 8: Android Configuration & Compatibility Tests
=====================================================================

Tests cover:
  - android_config URL resolution logic (env vars, desktop vs Android)
  - buildozer.spec content validation (secrets exclusion, permissions, requirements)
  - Asset path resolvability
  - WebSocket client: no localhost assumptions on Android
  - APK security: no server secrets in client-facing config
  - Config module exports correct fields

These tests run entirely in the existing pytest environment (no Kivy needed).
"""

import os
import sys
import importlib
import types
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reload_android_config(env_overrides: dict) -> types.ModuleType:
    """
    Reload app.android_config with specific environment variable overrides.
    Ensures isolation between tests.
    """
    # Back up and apply overrides
    saved = {}
    for k, v in env_overrides.items():
        saved[k] = os.environ.get(k)
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    # Remove cached modules so they re-execute with fresh env
    for mod in list(sys.modules.keys()):
        if "anti_gravity" not in mod and mod.startswith("app."):
            del sys.modules[mod]
    sys.modules.pop("app.android_config", None)
    sys.modules.pop("app.config", None)

    import app.android_config as ac
    importlib.reload(ac)

    # Restore env
    for k, orig in saved.items():
        if orig is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = orig

    return ac


# ══════════════════════════════════════════════════════════════════════════════
# 1. android_config: environment resolution
# ══════════════════════════════════════════════════════════════════════════════

class TestAndroidConfigEnvironmentResolution:
    """Verify URL resolution under different environment configurations."""

    def _get_urls(self, env_vars: dict) -> tuple:
        """Helper: get (api_url, ws_url) under given env vars."""
        saved = {}
        for k, v in env_vars.items():
            saved[k] = os.environ.get(k)
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        try:
            sys.modules.pop("app.android_config", None)
            sys.modules.pop("app.config", None)
            import app.android_config as ac
            importlib.reload(ac)
            return ac.get_api_base_url(), ac.get_ws_base_url()
        finally:
            for k, orig in saved.items():
                if orig is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = orig
            sys.modules.pop("app.android_config", None)
            sys.modules.pop("app.config", None)

    def test_explicit_api_url_override_wins(self):
        """ANTI_GRAVITY_API_URL env var must take top priority."""
        api_url, _ = self._get_urls({
            "ANTI_GRAVITY_API_URL": "http://custom.server:9000/api",
            "ANTI_GRAVITY_ENV": "production",
        })
        assert api_url == "http://custom.server:9000/api"

    def test_explicit_ws_url_override_wins(self):
        """ANTI_GRAVITY_WS_URL env var must take top priority."""
        _, ws_url = self._get_urls({
            "ANTI_GRAVITY_WS_URL": "wss://custom.server:9000/ws/game",
            "ANTI_GRAVITY_ENV": "production",
        })
        assert ws_url == "wss://custom.server:9000/ws/game"

    def test_staging_env_uses_staging_urls(self):
        """ENV=staging must return staging server addresses."""
        sys.modules.pop("app.android_config", None)
        import app.android_config as ac
        importlib.reload(ac)

        saved_env = os.environ.get("ANTI_GRAVITY_ENV")
        saved_api = os.environ.get("ANTI_GRAVITY_API_URL")
        saved_ws = os.environ.get("ANTI_GRAVITY_WS_URL")
        try:
            os.environ["ANTI_GRAVITY_ENV"] = "staging"
            os.environ.pop("ANTI_GRAVITY_API_URL", None)
            os.environ.pop("ANTI_GRAVITY_WS_URL", None)
            sys.modules.pop("app.android_config", None)
            import app.android_config as ac2
            importlib.reload(ac2)
            api = ac2.get_api_base_url()
            ws = ac2.get_ws_base_url()
            assert "staging" in api or "example" in api, f"Staging URL unexpected: {api}"
            assert "staging" in ws or "example" in ws, f"Staging WS URL unexpected: {ws}"
        finally:
            if saved_env is None:
                os.environ.pop("ANTI_GRAVITY_ENV", None)
            else:
                os.environ["ANTI_GRAVITY_ENV"] = saved_env
            if saved_api is None:
                os.environ.pop("ANTI_GRAVITY_API_URL", None)
            else:
                os.environ["ANTI_GRAVITY_API_URL"] = saved_api
            if saved_ws is None:
                os.environ.pop("ANTI_GRAVITY_WS_URL", None)
            else:
                os.environ["ANTI_GRAVITY_WS_URL"] = saved_ws
            sys.modules.pop("app.android_config", None)
            sys.modules.pop("app.config", None)

    def test_production_env_uses_production_urls(self):
        """ENV=production must return production server addresses."""
        saved = {}
        for k in ("ANTI_GRAVITY_ENV", "ANTI_GRAVITY_API_URL", "ANTI_GRAVITY_WS_URL"):
            saved[k] = os.environ.get(k)
        try:
            os.environ["ANTI_GRAVITY_ENV"] = "production"
            os.environ.pop("ANTI_GRAVITY_API_URL", None)
            os.environ.pop("ANTI_GRAVITY_WS_URL", None)
            sys.modules.pop("app.android_config", None)
            import app.android_config as ac3
            importlib.reload(ac3)
            api = ac3.get_api_base_url()
            ws = ac3.get_ws_base_url()
            # Production must NOT be localhost or 127.0.0.1
            assert "localhost" not in api
            assert "127.0.0.1" not in api
            assert "localhost" not in ws
            assert "127.0.0.1" not in ws
        finally:
            for k, orig in saved.items():
                if orig is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = orig
            sys.modules.pop("app.android_config", None)
            sys.modules.pop("app.config", None)

    def test_api_url_has_no_trailing_slash(self):
        """API base URL must not end with / (would cause double-slash in paths)."""
        sys.modules.pop("app.android_config", None)
        import app.android_config as ac
        importlib.reload(ac)
        url = ac.get_api_base_url()
        assert not url.endswith("/"), f"API URL must not end with /: {url!r}"

    def test_ws_url_starts_with_ws_scheme(self):
        """WebSocket URL must start with ws:// or wss://."""
        sys.modules.pop("app.android_config", None)
        import app.android_config as ac
        importlib.reload(ac)
        ws = ac.get_ws_base_url()
        assert ws.startswith("ws://") or ws.startswith("wss://"), \
            f"WS URL must start with ws:// or wss://, got: {ws!r}"

    def test_api_url_starts_with_http_scheme(self):
        """API URL must start with http:// or https://."""
        sys.modules.pop("app.android_config", None)
        import app.android_config as ac
        importlib.reload(ac)
        api = ac.get_api_base_url()
        assert api.startswith("http://") or api.startswith("https://"), \
            f"API URL must start with http:// or https://, got: {api!r}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. Android vs desktop detection
# ══════════════════════════════════════════════════════════════════════════════

class TestPlatformDetection:
    """Verify _is_desktop() and _is_android() helpers."""

    def test_is_desktop_on_windows_linux_mac(self):
        """Non-Android platforms must report as desktop."""
        sys.modules.pop("app.android_config", None)
        import app.android_config as ac
        importlib.reload(ac)
        # On the test host (Windows), _is_desktop() must be True
        assert ac._is_desktop() is True

    def test_is_android_false_on_test_host(self):
        """_is_android() must be False on the dev/test machine."""
        sys.modules.pop("app.android_config", None)
        import app.android_config as ac
        importlib.reload(ac)
        assert ac._is_android() is False

    def test_desktop_dev_uses_localhost(self):
        """On desktop with ENV=development, URL must use 127.0.0.1 (desktop localhost)."""
        saved = {}
        for k in ("ANTI_GRAVITY_ENV", "ANTI_GRAVITY_API_URL", "ANTI_GRAVITY_WS_URL"):
            saved[k] = os.environ.get(k)
        try:
            os.environ["ANTI_GRAVITY_ENV"] = "development"
            os.environ.pop("ANTI_GRAVITY_API_URL", None)
            os.environ.pop("ANTI_GRAVITY_WS_URL", None)
            sys.modules.pop("app.android_config", None)
            import app.android_config as ac
            importlib.reload(ac)
            api = ac.get_api_base_url()
            ws = ac.get_ws_base_url()
            # On desktop, dev mode should use 127.0.0.1 (localhost shortcut)
            assert "127.0.0.1" in api or "localhost" in api, \
                f"Desktop dev mode should use localhost, got: {api}"
            assert "127.0.0.1" in ws or "localhost" in ws, \
                f"Desktop dev WS should use localhost, got: {ws}"
        finally:
            for k, orig in saved.items():
                if orig is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = orig
            sys.modules.pop("app.android_config", None)
            sys.modules.pop("app.config", None)


# ══════════════════════════════════════════════════════════════════════════════
# 3. buildozer.spec security and content validation
# ══════════════════════════════════════════════════════════════════════════════

SPEC_PATH = os.path.join(os.path.dirname(__file__), "..", "buildozer.spec")


class TestBuildozerSpec:
    """Validate buildozer.spec is correctly configured and free of secrets."""

    def _read_spec(self) -> str:
        with open(SPEC_PATH, "r", encoding="utf-8") as f:
            return f.read()

    def test_spec_file_exists(self):
        """buildozer.spec must exist at project root."""
        assert os.path.isfile(SPEC_PATH), "buildozer.spec not found"

    def test_internet_permission_present(self):
        """INTERNET permission must be declared — required for backend comms."""
        content = self._read_spec()
        assert "INTERNET" in content, "INTERNET permission missing from buildozer.spec"

    def test_no_excessive_permissions(self):
        """APK must NOT request camera, microphone, location, contacts, or phone permissions."""
        content = self._read_spec()
        # Only check the actual permissions line, not comments
        perm_lines = [l for l in content.splitlines()
                      if l.strip().startswith("android.permissions")]
        assert perm_lines, "android.permissions line not found in buildozer.spec"
        perm_value = perm_lines[0].upper()
        forbidden = ["CAMERA", "RECORD_AUDIO", "ACCESS_FINE_LOCATION",
                     "READ_CONTACTS", "CALL_PHONE", "READ_PHONE_STATE"]
        for perm in forbidden:
            assert perm not in perm_value, \
                f"Excessive permission {perm} found in buildozer.spec permissions — not needed"

    def test_backend_packages_not_in_requirements(self):
        """Server-only packages must NOT be in APK requirements."""
        content = self._read_spec()
        server_only = ["fastapi", "uvicorn", "sqlalchemy", "aiosqlite",
                       "passlib", "python-jose", "pytest", "pytest-asyncio",
                       "alembic"]
        # Find the requirements= line
        req_lines = [l for l in content.splitlines() if l.strip().startswith("requirements")]
        assert req_lines, "No requirements line found in buildozer.spec"
        req_line = req_lines[0].lower()
        for pkg in server_only:
            assert pkg not in req_line, \
                f"Server-only package '{pkg}' must NOT be in buildozer.spec requirements (APK client only)"

    def test_kivy_in_requirements(self):
        """kivy must be in requirements."""
        content = self._read_spec()
        req_lines = [l for l in content.splitlines() if l.strip().startswith("requirements")]
        assert req_lines
        assert "kivy" in req_lines[0].lower()

    def test_websocket_client_in_requirements(self):
        """websocket-client must be in requirements (WS connection to backend)."""
        content = self._read_spec()
        req_lines = [l for l in content.splitlines() if l.strip().startswith("requirements")]
        assert req_lines
        assert "websocket-client" in req_lines[0].lower()

    def test_backend_excluded_from_source(self):
        """backend/ directory must be in source.exclude_dirs."""
        content = self._read_spec()
        exclude_lines = [l for l in content.splitlines()
                         if l.strip().startswith("source.exclude_dirs")]
        assert exclude_lines, "source.exclude_dirs not found in buildozer.spec"
        assert "backend" in exclude_lines[0], \
            "backend/ must be excluded from APK source"

    def test_tests_excluded_from_source(self):
        """tests/ directory must be in source.exclude_dirs."""
        content = self._read_spec()
        exclude_lines = [l for l in content.splitlines()
                         if l.strip().startswith("source.exclude_dirs")]
        assert exclude_lines
        assert "tests" in exclude_lines[0], \
            "tests/ must be excluded from APK source"

    def test_no_secrets_in_spec(self):
        """buildozer.spec must not contain secret values."""
        content = self._read_spec().lower()
        forbidden_patterns = [
            "secret_key", "jwt_secret", "db_password", "server_seed",
            "private_key", "password=", "passwd=",
        ]
        for pattern in forbidden_patterns:
            assert pattern not in content, \
                f"Potential secret pattern '{pattern}' found in buildozer.spec"

    def test_orientation_portrait(self):
        """App must be locked to portrait orientation."""
        content = self._read_spec()
        assert "orientation = portrait" in content

    def test_min_api_is_21_or_higher(self):
        """minapi must be 21+ (Android 5.0 minimum for Kivy)."""
        content = self._read_spec()
        for line in content.splitlines():
            if line.strip().startswith("android.minapi"):
                val = int(line.split("=")[1].strip())
                assert val >= 21, f"android.minapi must be >= 21, got {val}"
                return
        pytest.fail("android.minapi not found in buildozer.spec")

    def test_target_api_is_31_or_higher(self):
        """android.api must be >= 31 to comply with Play Store requirements."""
        content = self._read_spec()
        for line in content.splitlines():
            if line.strip().startswith("android.api"):
                val = int(line.split("=")[1].strip())
                assert val >= 31, f"android.api must be >= 31, got {val}"
                return
        pytest.fail("android.api not found in buildozer.spec")

    def test_debug_artifact_is_apk(self):
        """debug builds must produce .apk (not .aab)."""
        content = self._read_spec()
        for line in content.splitlines():
            if line.strip().startswith("android.debug_artifact"):
                assert "apk" in line.lower()
                return
        pytest.fail("android.debug_artifact not found in buildozer.spec")


# ══════════════════════════════════════════════════════════════════════════════
# 4. APK security: secrets must not be in client config
# ══════════════════════════════════════════════════════════════════════════════

class TestApkSecretExclusion:
    """Verify no server secrets appear in client-facing config files."""

    def _read_client_config(self) -> str:
        config_path = os.path.join(os.path.dirname(__file__), "..", "app", "android_config.py")
        with open(config_path, "r", encoding="utf-8") as f:
            return f.read()

    def _read_app_config(self) -> str:
        config_path = os.path.join(os.path.dirname(__file__), "..", "app", "config.py")
        with open(config_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_android_config_has_no_jwt_secret(self):
        content = self._read_client_config()
        assert "SECRET_KEY" not in content
        assert "jwt_secret" not in content.lower()
        assert "HS256" not in content

    def test_android_config_has_no_db_credentials(self):
        """android_config.py must not contain actual DB connection credentials."""
        content = self._read_client_config()
        # Only check code lines, not docstring/comment mentions
        code_lines = [l for l in content.splitlines()
                      if not l.strip().startswith("#") and '"""' not in l and "'''" not in l]
        code_text = "\n".join(code_lines)
        assert "DATABASE_URL" not in code_text, "DATABASE_URL must not appear in android_config code"
        assert "sqlite" not in code_text.lower(), "sqlite must not appear in android_config code"
        # No actual password= assignments in code
        import re
        assert not re.search(r'^\s*password\s*=', code_text, re.MULTILINE), \
            "password= assignment must not appear in android_config code"

    def test_android_config_has_no_server_seed(self):
        content = self._read_client_config()
        assert "SERVER_SEED" not in content
        assert "server_seed" not in content.lower()
        assert "HMAC" not in content

    def test_app_config_imports_urls_from_android_config(self):
        """app/config.py must delegate URL resolution to android_config, not hardcode."""
        content = self._read_app_config()
        # Must import from android_config
        assert "android_config" in content
        assert "get_api_base_url" in content
        assert "get_ws_base_url" in content

    def test_app_config_has_no_hardcoded_localhost(self):
        """app/config.py must not hardcode localhost URLs directly."""
        content = self._read_app_config()
        # Direct hardcoded strings must not appear
        assert '"http://localhost' not in content
        assert "'http://localhost" not in content
        assert '"http://127.0.0.1' not in content
        assert "'http://127.0.0.1" not in content


# ══════════════════════════════════════════════════════════════════════════════
# 5. Asset path resolution (Android cwd safety)
# ══════════════════════════════════════════════════════════════════════════════

class TestAssetPathResolution:
    """Verify that asset and KV paths are resolved with abspath (Android cwd-safe)."""

    def test_main_py_uses_abspath_for_kv_dir(self):
        """main.py must use os.path.abspath to resolve the KV directory."""
        main_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
        with open(main_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "abspath" in content, \
            "main.py must use os.path.abspath for KV directory resolution (Android cwd safety)"

    def test_sound_manager_uses_abspath(self):
        """sound_manager.py must use os.path.abspath for sound directory."""
        sm_path = os.path.join(os.path.dirname(__file__), "..",
                               "app", "utils", "sound_manager.py")
        with open(sm_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "abspath" in content, \
            "sound_manager.py must use abspath for sounds directory (Android cwd safety)"

    def test_kv_directory_exists(self):
        """app/kv/ directory must exist and contain .kv files."""
        kv_dir = os.path.join(os.path.dirname(__file__), "..", "app", "kv")
        assert os.path.isdir(kv_dir), "app/kv/ directory not found"
        kv_files = [f for f in os.listdir(kv_dir) if f.endswith(".kv")]
        assert len(kv_files) >= 5, f"Expected at least 5 .kv files, found {len(kv_files)}"

    def test_assets_directory_exists(self):
        """app/assets/ directory structure must exist."""
        assets_dir = os.path.join(os.path.dirname(__file__), "..", "app", "assets")
        assert os.path.isdir(assets_dir), "app/assets/ directory not found"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Android lifecycle: main.py on_pause / on_resume
# ══════════════════════════════════════════════════════════════════════════════

class TestAndroidLifecycle:
    """Verify Android lifecycle hooks are present in main.py."""

    def _read_main(self) -> str:
        main_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
        with open(main_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_on_pause_returns_true(self):
        """on_pause must return True so Android doesn't destroy the app on backgrounding."""
        content = self._read_main()
        assert "def on_pause" in content, "on_pause not found in main.py"
        assert "return True" in content, "on_pause must return True"

    def test_on_resume_defined(self):
        """on_resume must be defined to handle app resuming from background."""
        content = self._read_main()
        assert "def on_resume" in content, "on_resume not found in main.py"

    def test_backend_not_started_in_main(self):
        """main.py must NOT import or start uvicorn or FastAPI server."""
        content = self._read_main()
        # Only check actual import/code lines, not docstring/comment mentions
        import_lines = [l for l in content.splitlines()
                        if l.strip().startswith(("import ", "from "))]
        import_text = "\n".join(import_lines).lower()
        assert "uvicorn" not in import_text, \
            "uvicorn must NOT be imported in main.py (server not in APK)"
        assert "fastapi" not in import_text, \
            "FastAPI must NOT be imported in main.py (server not in APK)"
        assert "from backend" not in import_text, \
            "backend package imports must NOT appear in main.py"


# ══════════════════════════════════════════════════════════════════════════════
# 7. WebSocket client: Android compatibility checks
# ══════════════════════════════════════════════════════════════════════════════

class TestWebSocketAndroidCompatibility:
    """Verify the WS client is compatible with Android threading model."""

    def _read_ws_client(self) -> str:
        ws_path = os.path.join(os.path.dirname(__file__), "..",
                               "app", "services", "websocket.py")
        with open(ws_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_ws_client_uses_daemon_thread(self):
        """WebSocket must run on a daemon thread so it doesn't block app exit."""
        content = self._read_ws_client()
        assert "daemon=True" in content, \
            "WS background thread must be a daemon thread"

    def test_ws_client_dispatches_to_ui_thread(self):
        """UI callbacks must be dispatched through Clock.schedule_once."""
        content = self._read_ws_client()
        assert "Clock.schedule_once" in content, \
            "WS callbacks must dispatch to Kivy main thread via Clock.schedule_once"

    def test_ws_client_has_reconnect_logic(self):
        """WS client must implement reconnection (handles Android network drops)."""
        content = self._read_ws_client()
        assert "auto_reconnect" in content or "reconnect" in content.lower(), \
            "WS client must implement reconnection for Android network interruption"

    def test_ws_client_has_disconnect_method(self):
        """WS client must be explicitly disconnectable (for app lifecycle)."""
        content = self._read_ws_client()
        assert "def disconnect" in content, "WS client must have disconnect() method"

    def test_ws_client_imports_config_not_hardcoded_url(self):
        """WS client must import URL from config, not hardcode localhost."""
        content = self._read_ws_client()
        assert "from app.config import WS_URL" in content or "app.config" in content, \
            "WS client must import URL from app.config"
        assert "localhost" not in content, \
            "WS client must not hardcode localhost (breaks on Android device)"

    def test_ws_client_no_asyncio_loop(self):
        """WS client must NOT use asyncio event loops (Kivy uses its own loop)."""
        content = self._read_ws_client()
        assert "asyncio.get_event_loop()" not in content, \
            "WS client must not call asyncio.get_event_loop() — conflicts with Kivy's loop on Android"


# ══════════════════════════════════════════════════════════════════════════════
# 8. Network security config validation
# ══════════════════════════════════════════════════════════════════════════════

class TestNetworkSecurityConfig:
    """Validate the Android network security config XML."""

    def _read_xml(self) -> str:
        xml_path = os.path.join(os.path.dirname(__file__), "..",
                                "app", "android_network_security.xml")
        with open(xml_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_network_security_xml_exists(self):
        """android_network_security.xml must exist."""
        xml_path = os.path.join(os.path.dirname(__file__), "..",
                                "app", "android_network_security.xml")
        assert os.path.isfile(xml_path), "android_network_security.xml not found"

    def test_base_config_blocks_cleartext(self):
        """Base config must block cleartext traffic (production-safe default)."""
        content = self._read_xml()
        assert 'cleartextTrafficPermitted="false"' in content or \
               "cleartextTrafficPermitted='false'" in content, \
            "Base config must block cleartext traffic"

    def test_dev_config_permits_cleartext_for_lan(self):
        """Dev domain-config must permit cleartext for LAN IPs."""
        content = self._read_xml()
        assert "domain-config" in content, \
            "domain-config for dev LAN cleartext must be present"
        assert "cleartextTrafficPermitted" in content

    def test_xml_is_valid_structure(self):
        """XML must contain network-security-config root element."""
        content = self._read_xml()
        assert "<network-security-config>" in content
        assert "</network-security-config>" in content

    def test_emulator_loopback_address_present(self):
        """10.0.2.2 (Android emulator loopback to host) must be in dev config."""
        content = self._read_xml()
        assert "10.0.2.2" in content, \
            "Emulator loopback 10.0.2.2 must be in network security config for emulator testing"
