import 'dart:io';
import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/security/secure_token_store.dart';
import '../../platform/device_platform_bridge.dart';

class PairingScreen extends StatefulWidget {
  const PairingScreen({super.key});

  @override
  State<PairingScreen> createState() => _PairingScreenState();
}

class _PairingScreenState extends State<PairingScreen> {
  final _serverCtrl = TextEditingController(text: 'http://10.0.2.2:8000');
  final _codeCtrl = TextEditingController();
  final _nameCtrl = TextEditingController(text: 'My agentVoice Device');
  String _status = 'Enter the single-use pairing code from Telephony > Mobile Devices.';
  bool _busy = false;

  Future<void> _pair() async {
    setState(() {
      _busy = true;
      _status = 'Pairing device...';
    });
    try {
      final platform = Platform.isIOS ? 'ios' : 'android';
      final bridge = DevicePlatformBridge();
      final caps = await bridge.discoverCapabilities(platform);
      final api = DeviceApiClient(_serverCtrl.text.trim());
      final res = await api.pairDevice(
        pairingCode: _codeCtrl.text.trim(),
        deviceName: _nameCtrl.text.trim(),
        platform: platform,
        platformVersion: Platform.operatingSystemVersion,
        appVersion: '0.1.0',
        capabilityProfile: caps.toJson(),
      );
      final dev = Map<String, dynamic>.from(res['device'] as Map);
      await SecureTokenStore().saveCredentials(
        serverUrl: _serverCtrl.text.trim(),
        deviceId: dev['id'] as String,
        deviceToken: res['device_token'] as String,
      );
      if (!mounted) return;
      Navigator.of(context).pushReplacementNamed('/dashboard');
    } catch (e) {
      setState(() => _status = 'Pairing failed: $e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Pair agentVoice Device')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _serverCtrl,
              decoration: const InputDecoration(labelText: 'agentVoice Server URL (HTTPS in prod)'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _nameCtrl,
              decoration: const InputDecoration(labelText: 'Device Name'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _codeCtrl,
              decoration: const InputDecoration(labelText: 'Single-Use Pairing Code'),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _busy ? null : _pair,
              child: Text(_busy ? 'Pairing...' : 'Confirm Pairing'),
            ),
            const SizedBox(height: 12),
            Text(_status),
          ],
        ),
      ),
    );
  }
}
