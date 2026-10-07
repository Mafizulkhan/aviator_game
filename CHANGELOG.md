# Changelog

All notable changes to Zero Gravity will be documented in this file.

## [1.0.0] - 2026-10-07

### Added
- Complete Flutter Android mobile application with Clean Architecture (models, repositories, networking, features, widgets, theme).
- Provably fair cyber spider animations and dynamic multiplier displays in Flutter.
- Real-time WebSocket connection manager with exponential backoff auto-reconnect.
- Admin Web application for operational controls, RBAC management, audit log inspection, and fairness verification.
- GitHub Actions CI workflows for Flutter Android build and FastAPI backend automated test verification.

### Changed
- Replaced obsolete Kivy/Buildozer mobile prototype with production Flutter + Dart stack.
- Modernized naming across web and mobile frontend to Zero Gravity.
- Configured pytest testpaths in pytest.ini with 202 passing automated tests covering backend API, game engine, security, fairness, performance, and race conditions.

### Security
- Defense-in-depth security model: Argon2id password hashing, JWT access tokens, rate limiting, and atomic transaction locks for cashout race protection.
