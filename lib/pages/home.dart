import 'package:diasorahub_admin/shared/widgets/cards.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter/material.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar
      (
        title: const Text('DiasporaHub Admin',
        style: TextStyle(
          color: Color.fromARGB(255, 0, 82, 103),
          fontWeight: FontWeight.bold,
          fontSize: 30,
        ),),
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
                    
                    Spacer(),
                    UploadCard(
                      title: 'View RealEstate',
                      icon: Icons.home,
                      onTap: () => context.go('/view_estate')
                    ),
                  ],
                ),
            Row(children: [
              UploadCard(
                title: 'Upload Doctors',
                icon: Icons.medical_services,
                onTap: () => context.go('/upload_doctors'),
                ),
                Spacer(),
              UploadCard(
                title: 'View Doctors',
                icon:Icons.medical_services,
                onTap: () => context.go('/view_doctors'),
              ),
            ],)
          ],
        ),
        ),
      );
  }
}