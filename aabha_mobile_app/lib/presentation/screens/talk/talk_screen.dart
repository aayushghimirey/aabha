import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_dimens.dart';
import '../../../core/widgets/app_card.dart';
import '../../../core/widgets/status_message.dart';
import '../../../providers/transcript_providers.dart';
import '../../../providers/voice_providers.dart';
import '../../controllers/voice_controller.dart';
import '../../widgets/talk/chat_composer.dart';
import '../../widgets/talk/transcript_view.dart';
import '../../widgets/talk/voice_orb.dart';

class TalkScreen extends ConsumerWidget {
  const TalkScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final voice = ref.watch(voiceControllerProvider);
    final controller = ref.read(voiceControllerProvider.notifier);
    final turns = ref.watch(transcriptControllerProvider);
    final theme = Theme.of(context);

    return ListView(
      padding: const EdgeInsets.all(AppDimens.pagePadding),
      children: [
        AppCard(
          title: 'Talk to aabha',
          subtitle: 'Opens a LiveKit room and streams your mic to the agent.',
          child: Column(
            children: [
              if (voice.error != null) ...[
                StatusMessage(text: voice.error!),
                const SizedBox(height: AppDimens.gapLg),
              ],
              VoiceOrb(isLive: voice.isLive),
              const SizedBox(height: AppDimens.gapLg),
              Text(
                voice.stateLabel,
                textAlign: TextAlign.center,
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: AppDimens.gapLg),
              _Controls(voice: voice, controller: controller),
            ],
          ),
        ),
        const SizedBox(height: AppDimens.gapLg),
        AppCard(
          title: 'Conversation',
          subtitle:
              'Speech comes back over lk.transcription; typing goes out on '
              'lk.chat. aabha answers out loud either way.',
          child: Column(
            children: [
              TranscriptView(turns: turns),
              const SizedBox(height: AppDimens.gap),
              ChatComposer(enabled: voice.isLive),
            ],
          ),
        ),
      ],
    );
  }
}

class _Controls extends StatelessWidget {
  const _Controls({required this.voice, required this.controller});

  final VoiceState voice;
  final VoiceController controller;

  @override
  Widget build(BuildContext context) {
    if (!voice.isLive) {
      return FilledButton(
        onPressed: voice.isBusy ? null : controller.connect,
        child: Text(voice.isBusy ? 'Connecting…' : 'Connect'),
      );
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        OutlinedButton.icon(
          onPressed: controller.toggleMicrophone,
          icon: Icon(voice.isMuted ? Icons.mic_off : Icons.mic, size: 18),
          label: Text(voice.isMuted ? 'Unmute' : 'Mute'),
        ),
        const SizedBox(width: AppDimens.gap),
        OutlinedButton(
          onPressed: controller.disconnect,
          style: OutlinedButton.styleFrom(foregroundColor: AppColors.danger),
          child: const Text('Leave'),
        ),
      ],
    );
  }
}
