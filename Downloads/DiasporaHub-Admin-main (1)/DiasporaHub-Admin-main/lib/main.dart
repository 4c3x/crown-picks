import 'package:diasorahub_admin/routing/app_router.dart';
import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Hardcoded credentials (for web/development)
  // In production, use environment variables or a secure configuration service
  const String supabaseUrl = 'https://btfflbtigilpwwreuheg.supabase.co';
  const String supabaseAnonKey =
      'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ0ZmZsYnRpZ2lscHd3cmV1aGVnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzY5ODUzNDksImV4cCI6MjA1MjU2MTM0OX0.Go4ok3x56RGSZ31_9GMhYy6yyZvbjbF1Fd8tTvptXG8';

  if (supabaseUrl.isEmpty || supabaseAnonKey.isEmpty) {
    throw Exception(
      'Missing Supabase credentials. Please configure SUPABASE_URL and SUPABASE_ANON_KEY.',
    );
  }

  await Supabase.initialize(url: supabaseUrl, anonKey: supabaseAnonKey);

  runApp(const MainApp());
}

class MainApp extends StatelessWidget {
  const MainApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      routerConfig: appRouter,
      debugShowCheckedModeBanner: false,
    );
  }
}
