import 'package:flutter/material.dart';

import '../features/device_registration/pairing_screen.dart';
import '../features/gateway_dashboard/gateway_dashboard_screen.dart';
import '../features/voip/voip_screen.dart';

class AgentVoiceMobileApp extends StatelessWidget {
  const AgentVoiceMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'agentVoice Gateway',
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF2563EB),
        useMaterial3: true,
      ),
      initialRoute: '/pair',
      routes: {
        '/pair': (_) => const PairingScreen(),
        '/dashboard': (_) => const GatewayDashboardScreen(),
        '/voip': (_) => const VoipScreen(),
      },
    );
  }
}
