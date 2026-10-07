import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../repositories/auth_repository.dart';
import '../../core/constants/app_constants.dart';
import '../auth/login_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _soundEnabled = true;
  bool _musicEnabled = true;
  bool _vibrationEnabled = true;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('SETTINGS'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Column(
              children: [
                SwitchListTile(
                  value: _soundEnabled,
                  onChanged: (val) => setState(() => _soundEnabled = val),
                  title: const Text('Sound Effects (SFX)', style: TextStyle(color: AppColors.textPrimary)),
                  activeColor: AppColors.primaryCyan,
                ),
                const Divider(color: AppColors.border, height: 1),
                SwitchListTile(
                  value: _musicEnabled,
                  onChanged: (val) => setState(() => _musicEnabled = val),
                  title: const Text('Cyber Synth Background Music', style: TextStyle(color: AppColors.textPrimary)),
                  activeColor: AppColors.primaryCyan,
                ),
                const Divider(color: AppColors.border, height: 1),
                SwitchListTile(
                  value: _vibrationEnabled,
                  onChanged: (val) => setState(() => _vibrationEnabled = val),
                  title: const Text('Haptic Vibration Feedback', style: TextStyle(color: AppColors.textPrimary)),
                  activeColor: AppColors.primaryCyan,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.info_outline, color: AppColors.primaryCyan),
                  title: const Text('Version', style: TextStyle(color: AppColors.textPrimary)),
                  trailing: const Text('v1.0.0 (Production-Ready)', style: TextStyle(color: AppColors.textSecondary)),
                ),
                const Divider(color: AppColors.border, height: 1),
                ListTile(
                  leading: const Icon(Icons.security, color: AppColors.accentGold),
                  title: const Text('Provably Fair Engine', style: TextStyle(color: AppColors.textPrimary)),
                  trailing: const Text('SHA256 / HMAC', style: TextStyle(color: AppColors.accentGold)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          SizedBox(
            height: 52,
            child: ElevatedButton(
              onPressed: () async {
                final authRepo = context.read<AuthRepository>();
                await authRepo.logout();
                if (!mounted) return;
                Navigator.pushAndRemoveUntil(
                  context,
                  MaterialPageRoute(builder: (_) => const LoginScreen()),
                  (route) => false,
                );
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppColors.dangerRed,
                foregroundColor: Colors.white,
              ),
              child: const Text('LOGOUT'),
            ),
          ),
        ],
      ),
    );
  }
}
