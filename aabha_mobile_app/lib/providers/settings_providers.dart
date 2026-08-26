import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../presentation/controllers/settings_controller.dart';

final apiBaseUrlProvider = NotifierProvider<SettingsController, String>(
  SettingsController.new,
);
