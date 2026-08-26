import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/data_sources/local/location_data_source.dart';
import '../data/data_sources/local/microphone_data_source.dart';
import '../data/data_sources/remote/livekit_room_data_source.dart';
import '../data/repositories/voice_repository.dart';
import '../data/services/location_rpc_service.dart';
import '../presentation/controllers/voice_controller.dart';
import 'repository_providers.dart';

final locationDataSourceProvider = Provider<LocationDataSource>((ref) {
  return const LocationDataSource();
});

final livekitRoomDataSourceProvider = Provider<LivekitRoomDataSource>((ref) {
  return LivekitRoomDataSource();
});

final microphoneDataSourceProvider = Provider<MicrophoneDataSource>((ref) {
  return const MicrophoneDataSource();
});

final locationRpcServiceProvider = Provider<LocationRpcService>((ref) {
  return LocationRpcService(
    location: ref.watch(locationDataSourceProvider),
    room: ref.watch(livekitRoomDataSourceProvider),
  );
});

/// Kept for the life of the app rather than the screen: a live room must
/// survive a look at the profile tab.
final voiceRepositoryProvider = Provider<VoiceRepository>((ref) {
  final repository = VoiceRepository(
    room: ref.watch(livekitRoomDataSourceProvider),
    auth: ref.watch(authRepositoryProvider),
    location: ref.watch(locationRpcServiceProvider),
    microphone: ref.watch(microphoneDataSourceProvider),
  );

  ref.onDispose(repository.dispose);
  return repository;
});

final voiceControllerProvider = NotifierProvider<VoiceController, VoiceState>(
  VoiceController.new,
);
