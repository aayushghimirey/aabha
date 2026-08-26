import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_exception.dart';
import '../../data/models/voice_event.dart';
import '../../providers/session_providers.dart';
import '../../providers/transcript_providers.dart';
import '../../providers/voice_providers.dart';

enum VoiceStatus { idle, connecting, connected }

class VoiceState {
  const VoiceState({
    this.status = VoiceStatus.idle,
    this.agentPresent = false,
    this.isMuted = false,
    this.error,
    this.notice,
    this.connectedAt,
  });

  final VoiceStatus status;
  final bool agentPresent;
  final bool isMuted;
  final String? error;

  /// Something to say in the status line for a moment without losing what it
  /// was showing before.
  final String? notice;

  final DateTime? connectedAt;

  bool get isLive => status == VoiceStatus.connected;
  bool get isBusy => status == VoiceStatus.connecting;

  String get stateLabel {
    if (notice != null) return notice!;

    return switch (status) {
      VoiceStatus.idle => 'Not connected',
      VoiceStatus.connecting => 'Connecting…',
      VoiceStatus.connected => agentPresent
          ? 'aabha is listening'
          : 'Connected — waiting for the agent to join',
    };
  }

  VoiceState copyWith({
    VoiceStatus? status,
    bool? agentPresent,
    bool? isMuted,
    String? error,
    String? notice,
    DateTime? connectedAt,
    bool clearError = false,
    bool clearNotice = false,
    bool clearConnectedAt = false,
  }) {
    return VoiceState(
      status: status ?? this.status,
      agentPresent: agentPresent ?? this.agentPresent,
      isMuted: isMuted ?? this.isMuted,
      error: clearError ? null : (error ?? this.error),
      notice: clearNotice ? null : (notice ?? this.notice),
      connectedAt: clearConnectedAt ? null : (connectedAt ?? this.connectedAt),
    );
  }
}

class VoiceController extends Notifier<VoiceState> {
  Timer? _noticeTimer;

  @override
  VoiceState build() {
    final subscription = ref
        .watch(voiceRepositoryProvider)
        .events
        .listen(_onEvent);

    ref.onDispose(() {
      _noticeTimer?.cancel();
      subscription.cancel();
    });

    return const VoiceState();
  }

  Future<void> connect() async {
    final session = ref.read(currentSessionProvider);
    if (session == null || state.isBusy || state.isLive) return;

    state = state.copyWith(
      status: VoiceStatus.connecting,
      clearError: true,
      clearNotice: true,
    );

    try {
      await ref.read(voiceRepositoryProvider).connect(session);
    } on ApiException catch (error) {
      state = state.copyWith(status: VoiceStatus.idle, error: error.message);
    } catch (error, stack) {
      // Anything reaching here escaped the repository's own reporting, so it
      // is shown rather than replaced with a sentence that explains nothing.
      debugPrint('aabha: connect failed before the room opened: $error');
      debugPrintStack(stackTrace: stack, maxFrames: 8);

      state = state.copyWith(
        status: VoiceStatus.idle,
        error: 'Could not join the room.\n$error',
      );
    }
  }

  Future<void> disconnect() async {
    await ref.read(voiceRepositoryProvider).disconnect();
  }

  Future<void> toggleMicrophone() async {
    if (!state.isLive) return;

    final enabled = await ref.read(voiceRepositoryProvider).toggleMicrophone();
    state = state.copyWith(isMuted: !enabled);
  }

  Future<void> send(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || !state.isLive) return;

    ref.read(transcriptControllerProvider.notifier).addTyped(trimmed);

    try {
      await ref.read(voiceRepositoryProvider).sendChat(trimmed);
    } catch (_) {
      state = state.copyWith(error: 'That message did not send.');
    }
  }

  void _onEvent(VoiceEvent event) {
    switch (event) {
      case VoiceConnected():
        state = state.copyWith(
          status: VoiceStatus.connected,
          isMuted: false,
          connectedAt: DateTime.now(),
          clearError: true,
        );

      case VoiceDisconnected(:final reason):
        _noticeTimer?.cancel();
        state = VoiceState(
          error: reason == null ? null : 'Disconnected ($reason)',
        );
        ref.read(transcriptControllerProvider.notifier).clear();

      case AgentPresenceChanged(:final present):
        state = state.copyWith(agentPresent: present);

      case VoiceNotice(:final message):
        _flash(message);

      case VoiceProblem(:final message):
        state = state.copyWith(error: message);
    }
  }

  /// Say something in the status line, then give it back.
  void _flash(String message) {
    state = state.copyWith(notice: message);

    _noticeTimer?.cancel();
    _noticeTimer = Timer(const Duration(seconds: 4), () {
      if (!ref.mounted) return;
      state = state.copyWith(clearNotice: true);
    });
  }
}
