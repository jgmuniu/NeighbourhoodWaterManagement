import 'package:flutter/material.dart';
import '../services/api_client.dart';
import 'home_screen.dart';

const aqua = Color(0xFF12B8C4);

class LoginScreen extends StatefulWidget { const LoginScreen({super.key}); @override State<LoginScreen> createState() => _LoginScreenState(); }
class _LoginScreenState extends State<LoginScreen> {
  final user = TextEditingController(); final pass = TextEditingController(); bool busy = false; String? error;
  Future<void> submit() async { setState(() {busy = true; error = null;}); try { await ApiClient.instance.login(user.text.trim(), pass.text); if (!mounted) return; Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const HomeScreen())); } catch (e) { setState(() => error = e.toString().replaceFirst('Exception: ', '')); } finally { if (mounted) setState(() => busy = false); } }
  @override Widget build(BuildContext context) => Scaffold(body: Center(child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 420), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [Container(padding: const EdgeInsets.all(24), decoration: BoxDecoration(color: aqua.withValues(alpha: .12), borderRadius: BorderRadius.circular(24)), child: const Column(children: [Icon(Icons.water_drop, size: 58, color: aqua), SizedBox(height: 12), Text('Neighbourhood Water Management', textAlign: TextAlign.center, style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold)), Text('Mobile companion', style: TextStyle(color: Colors.black54))])), const SizedBox(height: 28), TextField(controller: user, decoration: const InputDecoration(labelText: 'Username', prefixIcon: Icon(Icons.person))), const SizedBox(height: 14), TextField(controller: pass, obscureText: true, decoration: const InputDecoration(labelText: 'Password', prefixIcon: Icon(Icons.lock))), if (error != null) Padding(padding: const EdgeInsets.only(top: 12), child: Text(error!, style: const TextStyle(color: Colors.red))), const SizedBox(height: 20), FilledButton(onPressed: busy ? null : submit, child: Padding(padding: const EdgeInsets.all(12), child: busy ? const CircularProgressIndicator() : const Text('Sign in'))), const SizedBox(height: 12), const Text('Connect to the same API used by the desktop application.', textAlign: TextAlign.center, style: TextStyle(color: Colors.black54))])))));
}
