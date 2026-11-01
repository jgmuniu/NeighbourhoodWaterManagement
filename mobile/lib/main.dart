import 'package:flutter/material.dart';
import 'data/local_store.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';
import 'services/api_client.dart';

const aqua = Color(0xFF12B8C4);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiClient.instance.loadSettings();
  runApp(const WaterApp());
}

class WaterApp extends StatelessWidget {
  const WaterApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Neighbourhood Water Management', debugShowCheckedModeBanner: false,
    theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: aqua, primary: aqua), scaffoldBackgroundColor: const Color(0xFFF3FAFA), useMaterial3: true, inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder(), filled: true, fillColor: Colors.white)),
    home: const Startup(),
  );
}

class Startup extends StatefulWidget { const Startup({super.key}); @override State<Startup> createState() => _StartupState(); }
class _StartupState extends State<Startup> {
  bool loading = true;
  @override void initState() { super.initState(); _check(); }
  Future<void> _check() async { final token = await LocalStore.instance.getSetting('token'); if (!mounted) return; setState(() => loading = false); if (token != null && token.isNotEmpty) ApiClient.instance.token = token; }
  @override Widget build(BuildContext context) => loading ? const Scaffold(body: Center(child: CircularProgressIndicator())) : (ApiClient.instance.token == null ? const LoginScreen() : const HomeScreen());
}
