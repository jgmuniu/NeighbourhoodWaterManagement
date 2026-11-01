import 'dart:convert';
import 'package:http/http.dart' as http;
import '../data/local_store.dart';

class ApiClient {
  static final ApiClient instance = ApiClient._();
  ApiClient._();
  String baseUrl = 'http://10.0.2.2:8000';
  String? token;

  Future<void> loadSettings() async {
    baseUrl = await LocalStore.instance.getSetting('api_url') ?? baseUrl;
    token = await LocalStore.instance.getSetting('token');
  }

  Map<String, String> get headers => {'Content-Type': 'application/json', if (token != null) 'Authorization': 'Bearer $token'};

  Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await http.post(Uri.parse('$baseUrl/auth/login'), headers: headers, body: jsonEncode({'username': username, 'password': password})).timeout(const Duration(seconds: 15));
    final data = jsonDecode(response.body);
    if (response.statusCode != 200) throw Exception(data['detail'] ?? 'Login failed');
    token = data['access_token'];
    await LocalStore.instance.setSetting('token', token!);
    await LocalStore.instance.setSetting('username', username);
    return Map<String, dynamic>.from(data['user']);
  }

  Future<dynamic> get(String path) async {
    final response = await http.get(Uri.parse('$baseUrl$path'), headers: headers).timeout(const Duration(seconds: 15));
    if (response.statusCode < 200 || response.statusCode >= 300) throw Exception('Request failed (${response.statusCode})');
    return jsonDecode(response.body);
  }

  Future<dynamic> post(String path, Map<String, dynamic> body, {Map<String, String> extraHeaders = const {}}) async {
    final response = await http.post(Uri.parse('$baseUrl$path'), headers: {...headers, ...extraHeaders}, body: jsonEncode(body)).timeout(const Duration(seconds: 15));
    final data = jsonDecode(response.body);
    if (response.statusCode < 200 || response.statusCode >= 300) throw ApiRequestException(response.statusCode, data['detail'] ?? 'Request failed (${response.statusCode})');
    return data;
  }

  Future<void> refreshCache() async {
    for (final key in ['households', 'meters', 'bills', 'billing-periods']) {
      final value = await get('/$key');
      await LocalStore.instance.saveCache(key, value);
    }
  }

  Future<Map<String, dynamic>> submitQueued(String type, Map<String, dynamic> value, String changeId) async {
    final device = await LocalStore.instance.deviceId();
    final path = type == 'reading' ? '/sync/readings' : type == 'payment' ? '/sync/payments' : '';
    if (path.isEmpty) throw Exception('Unsupported queued operation: $type');
    return Map<String, dynamic>.from(await post(path, value, extraHeaders: {
      'X-Idempotency-Key': changeId,
      'X-Device-Id': device,
    }));
  }

  Future<int> flushOutbox() async {
    final entries = await LocalStore.instance.pending();
    var sent = 0;
    for (final entry in entries) {
      final id = entry['id'] as int;
      try {
        final payload = Map<String, dynamic>.from(jsonDecode(entry['payload'] as String));
        await submitQueued(entry['entity_type'] as String, payload, entry['change_id'] as String);
        await LocalStore.instance.markSent(id);
        sent++;
      } on ApiRequestException catch (e) {
        if (e.statusCode >= 400 && e.statusCode < 500 && e.statusCode != 409) {
          await LocalStore.instance.markReview(id, e.message);
        } else {
          await LocalStore.instance.markError(id, e.message);
          break;
        }
      } catch (e) {
        await LocalStore.instance.markError(id, e.toString());
        break;
      }
    }
    return sent;
  }

  Future<int> pullChanges() async {
    var cursor = await LocalStore.instance.getSyncCursor();
    var received = 0;
    while (true) {
      final page = Map<String, dynamic>.from(await get('/sync/pull?after_id=$cursor&limit=500'));
      final changes = List<dynamic>.from(page['changes'] ?? []);
      received += changes.length;
      final next = int.tryParse('${page['next_cursor'] ?? cursor}') ?? cursor;
      if (next > cursor) {
        cursor = next;
        await LocalStore.instance.setSyncCursor(cursor);
      }
      if (page['has_more'] != true || changes.isEmpty || next <= cursor && changes.isEmpty) break;
    }
    return received;
  }

  Future<Map<String, dynamic>> submitReading(Map<String, dynamic> value) async => Map<String, dynamic>.from(await post('/readings', value));
  Future<Map<String, dynamic>> submitPayment(Map<String, dynamic> value) async => Map<String, dynamic>.from(await post('/payments', value));
}

class ApiRequestException implements Exception {
  final int statusCode;
  final String message;
  ApiRequestException(this.statusCode, this.message);
  @override String toString() => message;
}
