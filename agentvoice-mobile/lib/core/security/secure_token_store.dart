import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureTokenStore {
  static const _storage = FlutterSecureStorage();
  static const _keyDeviceId = 'agentvoice_device_id';
  static const _keyDeviceToken = 'agentvoice_device_token';
  static const _keyServerUrl = 'agentvoice_server_url';

  Future<void> saveCredentials({
    required String serverUrl,
    required String deviceId,
    required String deviceToken,
  }) async {
    await _storage.write(key: _keyServerUrl, value: serverUrl);
    await _storage.write(key: _keyDeviceId, value: deviceId);
    await _storage.write(key: _keyDeviceToken, value: deviceToken);
  }

  Future<String?> getDeviceId() => _storage.read(key: _keyDeviceId);
  Future<String?> getDeviceToken() => _storage.read(key: _keyDeviceToken);
  Future<String?> getServerUrl() => _storage.read(key: _keyServerUrl);

  Future<void> clear() async {
    await _storage.deleteAll();
  }
}
