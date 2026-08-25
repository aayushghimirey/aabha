import 'livekit_token.dart';
import 'user.dart';

/// Everything signing in produced: who you are, and the grant to talk.
class Session {
  const Session({required this.user, required this.token});

  final User user;
  final LivekitToken token;

  Session copyWith({User? user, LivekitToken? token}) =>
      Session(user: user ?? this.user, token: token ?? this.token);

  factory Session.fromJson(Map<String, dynamic> json) {
    return Session(
      user: User.fromJson(json['user'] as Map<String, dynamic>),
      token: LivekitToken.fromJson(json['token'] as Map<String, dynamic>),
    );
  }

  Map<String, dynamic> toJson() => {
    'user': user.toJson(),
    'token': token.toJson(),
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Session && other.user == user && other.token == token;

  @override
  int get hashCode => Object.hash(user, token);
}
