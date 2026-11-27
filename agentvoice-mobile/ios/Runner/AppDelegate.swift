import UIKit
import Flutter

@UIApplicationMain
@objc class AppDelegate: FlutterAppDelegate {
    private var voipBridge: CallKitVoipBridge?

    override func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        let controller = window?.rootViewController as! FlutterViewController
        let channel = FlutterMethodChannel(
            name: "com.agentvoice.mobile/gateway",
            binaryMessenger: controller.binaryMessenger
        )
        let bridge = CallKitVoipBridge()
        self.voipBridge = bridge

        channel.setMethodCallHandler { call, result in
            switch call.method {
            case "getCapabilities":
                result([
                    "platform": "ios",
                    "cellular_call_initiation": false,
                    "cellular_call_state": false,
                    "cellular_audio_capture": false,
                    "cellular_audio_injection": false,
                    "cellular_audio_bridge_status": "CELLULAR_AUDIO_BRIDGE_UNAVAILABLE",
                    "voip_supported": true,
                    "callkit_supported": true,
                    "device_health": true
                ])
            case "getHealth":
                UIDevice.current.isBatteryMonitoringEnabled = true
                let level = UIDevice.current.batteryLevel >= 0 ? Int(UIDevice.current.batteryLevel * 100) : nil
                result([
                    "battery_percent": level as Any,
                    "battery_charging": UIDevice.current.batteryState == .charging,
                    "network_type": "ios_managed",
                    "connected": true,
                    "permissions": [:]
                ])
            default:
                result(FlutterMethodNotImplemented)
            }
        }
        GeneratedPluginRegistrant.register(with: self)
        return super.application(application, didFinishLaunchingWithOptions: launchOptions)
    }
}
