import 'dart:convert';
import 'dart:math';
import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

class LocalStore {
  static final LocalStore instance = LocalStore._();
  LocalStore._();
  Database? _db;

  Future<Database> get db async {
    if (_db != null) return _db!;
    final root = await getDatabasesPath();
    _db = await openDatabase(p.join(root, 'nwm_mobile.db'), version: 1,
      onCreate: (d, _) async {
        await d.execute('CREATE TABLE cache (cache_key TEXT PRIMARY KEY, payload TEXT NOT NULL, updated_at TEXT NOT NULL)');
        await d.execute('CREATE TABLE outbox (id INTEGER PRIMARY KEY AUTOINCREMENT, change_id TEXT UNIQUE NOT NULL, entity_type TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT \'pending\', last_error TEXT)');
        await d.execute('CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)');
      });
    return _db!;
  }

  Future<void> saveCache(String key, dynamic value) async {
    final d = await db;
    await d.insert('cache', {'cache_key': key, 'payload': jsonEncode(value), 'updated_at': DateTime.now().toIso8601String()}, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  Future<List<dynamic>> readCache(String key) async {
    final d = await db;
    final rows = await d.query('cache', where: 'cache_key = ?', whereArgs: [key], limit: 1);
    if (rows.isEmpty) return [];
    final value = jsonDecode(rows.first['payload'] as String);
    return value is List ? value : [];
  }

  Future<void> enqueue(String type, Map<String, dynamic> payload) async {
    final d = await db;
    final id = '${DateTime.now().microsecondsSinceEpoch}-$type-${Random.secure().nextInt(1 << 32)}';
    await d.insert('outbox', {'change_id': id, 'entity_type': type, 'payload': jsonEncode(payload), 'created_at': DateTime.now().toIso8601String(), 'status': 'pending'});
  }

  Future<List<Map<String, Object?>>> pending() async => (await db).query('outbox', where: "status = 'pending'", orderBy: 'id');
  Future<void> markSent(int id) async => (await db).update('outbox', {'status': 'submitted'}, where: 'id = ?', whereArgs: [id]);
  Future<void> markError(int id, String error) async => (await db).update('outbox', {'last_error': error, 'status': 'pending'}, where: 'id = ?', whereArgs: [id]);
  Future<void> markReview(int id, String error) async => (await db).update('outbox', {'last_error': error, 'status': 'review_required'}, where: 'id = ?', whereArgs: [id]);
  Future<String> deviceId() async { var value = await getSetting('device_id'); if (value == null || value.isEmpty) { value = 'android-${DateTime.now().microsecondsSinceEpoch}-${Random.secure().nextInt(1 << 32)}'; await setSetting('device_id', value); } return value; }
  Future<int> pendingCount() async => Sqflite.firstIntValue(await (await db).rawQuery("SELECT COUNT(*) FROM outbox WHERE status = 'pending'")) ?? 0;
  Future<int> reviewCount() async => Sqflite.firstIntValue(await (await db).rawQuery("SELECT COUNT(*) FROM outbox WHERE status = 'review_required'")) ?? 0;
  Future<int> getSyncCursor() async => int.tryParse(await getSetting('sync_cursor') ?? '0') ?? 0;
  Future<void> setSyncCursor(int value) async => setSetting('sync_cursor', value.toString());

  Future<void> setSetting(String key, String value) async => (await db).insert('settings', {'key': key, 'value': value}, conflictAlgorithm: ConflictAlgorithm.replace);
  Future<String?> getSetting(String key) async {
    final rows = await (await db).query('settings', where: 'key = ?', whereArgs: [key], limit: 1);
    return rows.isEmpty ? null : rows.first['value'] as String;
  }
}
