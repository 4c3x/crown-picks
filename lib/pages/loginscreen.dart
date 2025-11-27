import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:diasorahub_admin/shared/widgets/textfield.dart';
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();

  // Controllers for fields
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  //  login details
  final String allowedEmail = "admin@diasporahub.com";
  final String allowedPassword = "DiasporaAdmin2025";

  void _login() {
    if (_formKey.currentState!.validate()) {

      // Normalize inputs: trim whitespace and normalize email casing.
      String email = _emailController.text.trim().toLowerCase();
      String password = _passwordController.text.trim();

      if (email == allowedEmail.toLowerCase() && password == allowedPassword) {
        // Success: navigate to home
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Login Successful!")),
        );
        context.go('/home');
      } else {
        // Failure
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Incorrect email or password")),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Login",
      style: TextStyle(
          color: Color.fromARGB(255, 0, 82, 103),
          fontWeight: FontWeight.bold,
          fontSize: 30,
        ),),
        ),

      body: Padding(
        padding: const EdgeInsets.all(20.0),

        child: Form(
          key: _formKey,

          child: Column(
            children: [
              // Email field
              CustomTextField(
                controller: _emailController,
                label: "Email",
                icon: Icons.email,
                keyboardType: TextInputType.emailAddress,
              ),

              const SizedBox(height: 16),

              // Password field
              CustomTextField(
                controller: _passwordController,
                label: "Password",
                icon: Icons.lock,
                obscure: true,
              ),

              const SizedBox(height: 24),

              ElevatedButton(
                onPressed: _login,
                child: const Text("Login"),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
