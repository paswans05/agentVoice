package com.agentvoice.agentvoice_mobile

import com.agentvoice.mobile.DeviceGatewayPlugin
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val plugin = DeviceGatewayPlugin(applicationContext)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            "com.agentvoice.mobile/gateway"
        ).setMethodCallHandler(plugin)
    }
}
