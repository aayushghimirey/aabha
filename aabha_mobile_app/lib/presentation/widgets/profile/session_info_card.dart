import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/widgets/app_card.dart';
import '../../../providers/session_providers.dart';
import 'info_row.dart';

/// What `POST /auth/token` handed back.
class SessionInfoCard extends ConsumerWidget {
  const SessionInfoCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(currentSessionProvider);

    return AppCard(
      title: 'Session',
      subtitle: 'The LiveKit grant this sign-in bought.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InfoRow(label: 'User id', value: session?.user.id),
          InfoRow(label: 'Room', value: session?.token.room),
          InfoRow(label: 'Server', value: session?.token.serverUrl),
        ],
      ),
    );
  }
}
