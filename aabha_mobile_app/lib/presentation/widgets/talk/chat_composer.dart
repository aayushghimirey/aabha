import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_dimens.dart';
import '../../../providers/voice_providers.dart';

class ChatComposer extends ConsumerStatefulWidget {
  const ChatComposer({super.key, required this.enabled});

  final bool enabled;

  @override
  ConsumerState<ChatComposer> createState() => _ChatComposerState();
}

class _ChatComposerState extends ConsumerState<ChatComposer> {
  final _input = TextEditingController();

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _input.text;
    if (text.trim().isEmpty || !widget.enabled) return;

    _input.clear();
    await ref.read(voiceControllerProvider.notifier).send(text);
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: TextField(
            controller: _input,
            enabled: widget.enabled,
            autocorrect: false,
            textInputAction: TextInputAction.send,
            onSubmitted: (_) => _send(),
            decoration: InputDecoration(
              hintText: widget.enabled
                  ? 'Type to aabha…'
                  : 'Connect to type to aabha',
            ),
          ),
        ),
        const SizedBox(width: AppDimens.gap),
        FilledButton(
          onPressed: widget.enabled ? _send : null,
          child: const Text('Send'),
        ),
      ],
    );
  }
}
