import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../presentation/controllers/health_controller.dart';

final apiHealthProvider = NotifierProvider<HealthController, ApiHealth>(
  HealthController.new,
);
