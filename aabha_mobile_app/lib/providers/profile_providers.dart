import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../presentation/controllers/profile_controller.dart';

final profileControllerProvider =
    NotifierProvider<ProfileController, ProfileState>(
      ProfileController.new,
      isAutoDispose: true,
    );
