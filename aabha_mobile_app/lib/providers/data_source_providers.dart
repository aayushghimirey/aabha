import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/data_sources/local/session_local_data_source.dart';
import '../data/data_sources/local/settings_local_data_source.dart';
import '../data/data_sources/remote/auth_remote_data_source.dart';
import '../data/data_sources/remote/health_remote_data_source.dart';
import '../data/data_sources/remote/user_remote_data_source.dart';
import 'network_providers.dart';
import 'storage_providers.dart';

final authRemoteDataSourceProvider = Provider<AuthRemoteDataSource>((ref) {
  return AuthRemoteDataSource(ref.watch(dioProvider));
});

final userRemoteDataSourceProvider = Provider<UserRemoteDataSource>((ref) {
  return UserRemoteDataSource(ref.watch(dioProvider));
});

final healthRemoteDataSourceProvider = Provider<HealthRemoteDataSource>((ref) {
  return HealthRemoteDataSource(ref.watch(dioProvider));
});

final sessionLocalDataSourceProvider = Provider<SessionLocalDataSource>((ref) {
  return SessionLocalDataSource(ref.watch(secureStorageProvider));
});

final settingsLocalDataSourceProvider = Provider<SettingsLocalDataSource>((ref) {
  return SettingsLocalDataSource(ref.watch(secureStorageProvider));
});
