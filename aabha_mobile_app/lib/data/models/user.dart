import '../../core/utils/date_formatting.dart';

/// Mirrors `UserResponse` — the public view, which never carries the password.
class User {
  const User({
    required this.id,
    required this.username,
    required this.email,
    required this.dob,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String username;
  final String email;
  final DateTime dob;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as String,
      username: json['username'] as String,
      email: json['email'] as String,
      dob: parseApiDate(json['dob']),
      createdAt: parseApiDate(json['created_at']),
      updatedAt: parseApiDate(json['updated_at']),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'username': username,
    'email': email,
    'dob': dob.toIso8601String(),
    'created_at': createdAt.toIso8601String(),
    'updated_at': updatedAt.toIso8601String(),
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is User &&
          other.id == id &&
          other.username == username &&
          other.email == email &&
          other.dob == dob &&
          other.updatedAt == updatedAt;

  @override
  int get hashCode => Object.hash(id, username, email, dob, updatedAt);
}
