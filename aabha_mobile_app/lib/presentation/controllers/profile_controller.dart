import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_exception.dart';
import '../../data/models/user_update.dart';
import '../../providers/repository_providers.dart';
import '../../providers/session_providers.dart';

class ProfileState {
  const ProfileState({
    this.isSaving = false,
    this.isReloading = false,
    this.error,
    this.justSaved = false,
  });

  final bool isSaving;
  final bool isReloading;
  final String? error;
  final bool justSaved;

  bool get isBusy => isSaving || isReloading;

  ProfileState copyWith({
    bool? isSaving,
    bool? isReloading,
    String? error,
    bool? justSaved,
    bool clearError = false,
  }) {
    return ProfileState(
      isSaving: isSaving ?? this.isSaving,
      isReloading: isReloading ?? this.isReloading,
      error: clearError ? null : (error ?? this.error),
      justSaved: justSaved ?? this.justSaved,
    );
  }
}

class ProfileController extends Notifier<ProfileState> {
  @override
  ProfileState build() => const ProfileState();

  Future<void> save(UserUpdate update) async {
    final user = ref.read(currentUserProvider);
    if (user == null) return;

    state = state.copyWith(isSaving: true, justSaved: false, clearError: true);

    try {
      final saved = await ref
          .read(userRepositoryProvider)
          .update(user.id, update);

      // A changed username is shown all over the app, so the stored session
      // is rewritten rather than left describing who you used to be.
      await ref.read(sessionControllerProvider.notifier).replaceUser(saved);

      state = state.copyWith(isSaving: false, justSaved: true);
    } on ApiException catch (error) {
      state = state.copyWith(isSaving: false, error: error.message);
    }
  }

  Future<void> reload() async {
    final user = ref.read(currentUserProvider);
    if (user == null) return;

    state = state.copyWith(
      isReloading: true,
      justSaved: false,
      clearError: true,
    );

    try {
      final fresh = await ref.read(userRepositoryProvider).fetch(user.id);
      await ref.read(sessionControllerProvider.notifier).replaceUser(fresh);

      state = state.copyWith(isReloading: false);
    } on ApiException catch (error) {
      state = state.copyWith(isReloading: false, error: error.message);
    }
  }

  /// Typing again makes the last verdict stale.
  void clearFeedback() {
    if (state.error == null && !state.justSaved) return;
    state = state.copyWith(justSaved: false, clearError: true);
  }
}
