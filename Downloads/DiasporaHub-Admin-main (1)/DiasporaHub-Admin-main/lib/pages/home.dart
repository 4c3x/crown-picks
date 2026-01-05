import 'package:diasorahub_admin/shared/widgets/cards.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  Future<void> _logout() async {
    try {
      await Supabase.instance.client.auth.signOut();
      if (!mounted) return;
      context.go('/');
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error logging out: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'DiasporaHub Admin',
          style: TextStyle(
            color: Color.fromARGB(255, 0, 82, 103),
            fontWeight: FontWeight.bold,
            fontSize: 30,
          ),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: ElevatedButton.icon(
              onPressed: _logout,
              icon: const Icon(Icons.logout),
              label: const Text('Logout'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.red,
                foregroundColor: Colors.white,
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            Row(
              children: [
                UploadCard(
                  title: 'Upload RealEstate',
                  icon: Icons.home,
                  onTap: () => context.go('/upload_estate'),
                ),
                const Spacer(),
                UploadCard(
                  title: 'View RealEstate',
                  icon: Icons.home,
                  onTap: () => context.go('/view_estate'),
                ),
              ],
            ),
            Row(
              children: [
                UploadCard(
                  title: 'Upload Doctors',
                  icon: Icons.medical_services,
                  onTap: () => context.go('/upload_doctors'),
                ),
                const Spacer(),
                UploadCard(
                  title: 'View Doctors',
                  icon: Icons.medical_services,
                  onTap: () => context.go('/view_doctors'),
                ),
              ],
            ),
            Row(
              children: [
                UploadCard(
                  title: 'Upload Pharmacies',
                  icon: Icons.local_pharmacy,
                  onTap: () => context.go('/upload_pharmacies'),
                ),
                const Spacer(),
                UploadCard(
                  title: 'View Pharmacies',
                  icon: Icons.local_pharmacy,
                  onTap: () => context.go('/view_pharmacies'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
