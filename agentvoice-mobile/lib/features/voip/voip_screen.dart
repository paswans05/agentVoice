import 'package:flutter/material.dart';

class VoipScreen extends StatelessWidget {
  const VoipScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AgentVoice VoIP')),
      body: const Padding(
        padding: EdgeInsets.all(16),
        child: Text(
          'Call Source: AGENTVOICE_VOIP\n\n'
          'VoIP calls connect through the authorized Asterisk/SIP provider and CallKit/Telecom '
          'within platform rules. Normal cellular SIM calls are never mislabeled as VoIP.',
        ),
      ),
    );
  }
}
