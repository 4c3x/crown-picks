import 'package:flutter/material.dart';

class UploadDoctors extends StatelessWidget {
  const UploadDoctors({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Upload Doctors',
        style: TextStyle(
          color: Color.fromARGB(255, 0, 82, 103),
          fontWeight: FontWeight.bold,
          fontSize: 30,
        ),),
      ),
      body: const Center(
        child: Text('Upload Doctors Page Content Here',
        style: TextStyle(
          fontSize: 24,
        ),),
      ),
    );    

  }
}