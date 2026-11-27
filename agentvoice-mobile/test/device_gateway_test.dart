import 'package:flutter_test/flutter_test.dart';
import 'package:agentvoice_mobile/platform/device_platform_bridge.dart';

void main() {
  test('DeviceCapabilitySnapshot never claims cellular audio bridge', () {
    const snap = DeviceCapabilitySnapshot(
      platform: 'android',
      cellularCallInitiation: true,
      cellularCallState: true,
      cellularAudioCapture: true,
      cellularAudioInjection: true,
      cellularAudioBridgeStatus: 'CELLULAR_AUDIO_BRIDGE_UNAVAILABLE',
      voipSupported: true,
      callkitSupported: false,
    );
    final json = snap.toJson();
    expect(json['cellular_audio_capture'], false);
    expect(json['cellular_audio_injection'], false);
    expect(json['cellular_audio_bridge_status'], 'CELLULAR_AUDIO_BRIDGE_UNAVAILABLE');
    expect(json['ai_call_ready'], false);
  });
}
