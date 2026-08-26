import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/transcript_turn.dart';
import '../presentation/controllers/transcript_controller.dart';

final transcriptControllerProvider =
    NotifierProvider<TranscriptController, List<TranscriptTurn>>(
      TranscriptController.new,
    );
