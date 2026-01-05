import 'package:flutter/material.dart';

class NotFoundScreen extends StatelessWidget {
  const NotFoundScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Text('404 - Page Not Found',
        style: TextStyle(
          fontSize: 40, 
          fontWeight: FontWeight.w800,

        ),),
      ),
    );
  }
}