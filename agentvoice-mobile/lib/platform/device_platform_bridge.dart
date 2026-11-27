import 'package:flutter/services.dart';

class DeviceCapabilitySnapshot {
  const DeviceCapabilitySnapshot({
    required this.platform,
    required this.cellularCallInitiation,
    required this.cellularCallState,
    required this.cellularAudioCapture,
    required this.cellularAudioInjection,
    required this.cellularAudioBridgeStatus,
    required this.voipSupported,
    required this.callkitSupported,
  });

  final String platform;
  final bool cellularCallInitiation;
  final bool cellularCallState;
  final bool cellularAudioCapture;
  final bool cellularAudioInjection;
  final String cellularAudioBridgeStatus;
  final bool voipSupported;
  final bool callkitSupported;

  Map<String, dynamic> toJson() => {
        'platform': platform,
        'cellular_call_initiation': cellularCallInitiation,
        'cellular_call_state': cellularCallState,
        'cellular_audio_capture': false,
        'cellular_audio_injection': false,
        'cellular_audio_bridge_status': 'CELLULAR_AUDIO_BRIDGE_UNAVAILABLE',
        'voip_supported': voipSupported,
        'callkit_supported': callkitSupported,
        'device_health': true,
        'ai_call_ready': false,
      };
}

class DevicePlatformBridge {
  static const MethodChannel _channel = MethodChannel('com.agentvoice.mobile/gateway');

  Future<DeviceCapabilitySnapshot> discoverCapabilities(String platform) async {
    try {
      final res = await _channel.invokeMapMethod<String, dynamic>('getCapabilities');
      if (res != null) {
        return DeviceCapabilitySnapshot(
          platform: platform,
          cellularCallInitiation: res['cellular_call_initiation'] == true,
          cellularCallState: res['cellular_call_state'] == true,
          cellularAudioCapture: false,
          cellularAudioInjection: false,
          cellularAudioBridgeStatus:
              (res['cellular_audio_bridge_status'] as String?) ??
                  'CELLULAR_AUDIO_BRIDGE_UNAVAILABLE',
          voipSupported: res['voip_supported'] != false,
          callkitSupported: res['callkit_supported'] == true,
        );
      }
    } on PlatformException {
      // Fallback to safe platform defaults if native channel unavailable
    }
    return DeviceCapabilitySnapshot(
      platform: platform,
      cellularCallInitiation: platform == 'android',
      cellularCallState: platform == 'android',
      cellularAudioCapture: false,
      cellularAudioInjection: false,
      cellularAudioBridgeStatus: 'CELLULAR_AUDIO_BRIDGE_UNAVAILABLE',
      voipSupported: true,
      callkitSupported: platform == 'ios',
    );
  }

  Future<Map<String, dynamic>> collectHealth() async {
    try {
      final res = await _channel.invokeMapMethod<String, dynamic>('getHealth');
      if (res != null) return res;
    } on PlatformException {
      // Fallback
    }
    return {
      'connected': true,
      'network_type': 'unknown',
      'permissions': <String, bool>{},
    };
  }
}
