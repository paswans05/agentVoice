package com.agentvoice.mobile

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager
import android.telephony.TelephonyManager
import androidx.core.content.ContextCompat
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * Android Device Gateway native bridge.
 * Reports only platform-permitted device health, network, SIM presence, and Telecom capabilities.
 * Explicitly reports CELLULAR_AUDIO_BRIDGE_UNAVAILABLE (never uses privileged/accessibility audio hacks).
 */
class DeviceGatewayPlugin(private val context: Context) : MethodChannel.MethodCallHandler {
    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "getCapabilities" -> result.success(discoverCapabilities())
            "getHealth" -> result.success(collectHealth())
            else -> result.notImplemented()
        }
    }

    private fun hasPermission(perm: String): Boolean {
        return ContextCompat.checkSelfPermission(context, perm) == PackageManager.PERMISSION_GRANTED
    }

    private fun discoverCapabilities(): Map<String, Any> {
        val canReadPhoneState = hasPermission(Manifest.permission.READ_PHONE_STATE)
        val canCallPhone = hasPermission(Manifest.permission.CALL_PHONE)
        return mapOf(
            "platform" to "android",
            "cellular_call_initiation" to canCallPhone,
            "cellular_call_state" to canReadPhoneState,
            "cellular_audio_capture" to false,
            "cellular_audio_injection" to false,
            "cellular_audio_bridge_status" to "CELLULAR_AUDIO_BRIDGE_UNAVAILABLE",
            "voip_supported" to true,
            "callkit_supported" to false,
            "device_health" to true
        )
    }

    private fun collectHealth(): Map<String, Any?> {
        val bm = context.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val batteryPct = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        val charging = bm.isCharging

        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val activeNet = cm.activeNetwork
        val caps = cm.getNetworkCapabilities(activeNet)
        val netType = when {
            caps == null -> "offline"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "wifi"
            caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "cellular"
            else -> "other"
        }

        val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
        val simPresent = tm.simState == TelephonyManager.SIM_STATE_READY
        val carrierName = if (hasPermission(Manifest.permission.READ_PHONE_STATE)) {
            tm.networkOperatorName
        } else {
            null
        }

        return mapOf(
            "battery_percent" to batteryPct,
            "battery_charging" to charging,
            "network_type" to netType,
            "connected" to (caps != null),
            "sim_present" to simPresent,
            "carrier_name" to carrierName,
            "permissions" to mapOf(
                "READ_PHONE_STATE" to hasPermission(Manifest.permission.READ_PHONE_STATE),
                "CALL_PHONE" to hasPermission(Manifest.permission.CALL_PHONE),
                "RECORD_AUDIO" to hasPermission(Manifest.permission.RECORD_AUDIO)
            )
        )
    }
}
