import 'dart:io';
import 'package:flutter/material.dart';

import '../../core/api/api_client.dart';
import '../../core/security/secure_token_store.dart';
import '../../platform/device_platform_bridge.dart';

class GatewayDashboardScreen extends StatefulWidget {
  const GatewayDashboardScreen({super.key});

  @override
  State<GatewayDashboardScreen> createState() => _GatewayDashboardScreenState();
}

class _GatewayDashboardScreenState extends State<GatewayDashboardScreen> {
  String _status = 'Ready to sync heartbeat.';
  String _audioStatus = 'CELLULAR_AUDIO_BRIDGE_UNAVAILABLE';

  Future<void> _sendHeartbeat() async {
    final store = SecureTokenStore();
    final url = await store.getServerUrl();
    final id = await store.getDeviceId();
    final token = await store.getDeviceToken();
    if (url == null || id == null || token == null) {
      setState(() => _status = 'Not paired.');
      return;
    }
    final platform = Platform.isIOS ? 'ios' : 'android';
    final bridge = DevicePlatformBridge();
    final caps = await bridge.discoverCapabilities(platform);
    final health = await bridge.collectHealth();
    await DeviceApiClient(url).sendHeartbeat(
      deviceId: id,
      deviceToken: token,
      health: health,
      capabilityProfile: caps.toJson(),
    );
    setState(() {
      _audioStatus = caps.cellularAudioBridgeStatus;
      _status = 'Heartbeat synced at ${DateTime.now().toIso8601String()}';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Device Gateway Dashboard')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: ListTile(
                title: const Text('Cellular AI Audio Bridge'),
                subtitle: Text(_audioStatus),
                leading: const Icon(Icons.info_outline),
              ),
            ),
            const SizedBox(height: 12),
            Text(_status),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _sendHeartbeat,
              child: const Text('Sync Heartbeat & Capabilities'),
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: () => Navigator.of(context).pushNamed('/voip'),
              child: const Text('Open AgentVoice VoIP Endpoint'),
            ),
          ],
        ),
      ),
    );
  }
}
