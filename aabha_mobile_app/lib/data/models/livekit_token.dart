/// Mirrors `TokenResponse` — the LiveKit grant.
///
/// The API issues no session of its own, so this is the only credential the
/// client holds, and it is what `POST /auth/dispatch` authenticates with.
class LivekitToken {
  const LivekitToken({
    required this.token,
    required this.serverUrl,
    required this.room,
    required this.identity,
  });

  final String token;
  final String serverUrl;
  final String room;
  final String identity;

  factory LivekitToken.fromJson(Map<String, dynamic> json) {
    return LivekitToken(
      token: json['token'] as String,
      serverUrl: json['server_url'] as String,
      room: json['room'] as String,
      identity: json['identity'] as String,
    );
  }

  Map<String, dynamic> toJson() => {
    'token': token,
    'server_url': serverUrl,
    'room': room,
    'identity': identity,
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is LivekitToken &&
          other.token == token &&
          other.serverUrl == serverUrl &&
          other.room == room &&
          other.identity == identity;

  @override
  int get hashCode => Object.hash(token, serverUrl, room, identity);
}
