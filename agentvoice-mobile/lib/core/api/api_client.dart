import 'package:dio/dio.dart';

class DeviceApiClient {
  DeviceApiClient(this.baseUrl)
      : _dio = Dio(BaseOptions(baseUrl: baseUrl, connectTimeout: const Duration(seconds: 10)));

  final String baseUrl;
  final Dio _dio;

  Future<Map<String, dynamic>> pairDevice({
    required String pairingCode,
    required String deviceName,
    required String platform,
    required String platformVersion,
    required String appVersion,
    required Map<String, dynamic> capabilityProfile,
  }) async {
    final resp = await _dio.post('/api/v1/devices/pair', data: {
      'pairing_code': pairingCode,
      'device_name': deviceName,
      'platform': platform,
      'platform_version': platformVersion,
      'app_version': appVersion,
      'capability_profile': capabilityProfile,
    });
    return Map<String, dynamic>.from(resp.data['data'] as Map);
  }

  Future<Map<String, dynamic>> sendHeartbeat({
    required String deviceId,
    required String deviceToken,
    required Map<String, dynamic> health,
    required Map<String, dynamic> capabilityProfile,
  }) async {
    final resp = await _dio.post(
      '/api/v1/devices/$deviceId/heartbeat',
      data: {'health': health, 'capability_profile': capabilityProfile},
      options: Options(headers: {'X-Device-Token': deviceToken}),
    );
    return Map<String, dynamic>.from(resp.data['data'] as Map);
  }
}
