import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class UploadPharmacies extends StatefulWidget {
  const UploadPharmacies({super.key});

  @override
  State<UploadPharmacies> createState() => _UploadPharmaciesState();
}

class _UploadPharmaciesState extends State<UploadPharmacies> {
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;

  // Form controllers
  final _nameController = TextEditingController();
  final _stateController = TextEditingController();
  final _addressController = TextEditingController();
  final _phoneController = TextEditingController();
  final _websiteController = TextEditingController();
  final _emailController = TextEditingController();
  final _medicationsController = TextEditingController();
  final _servicesController = TextEditingController();

  Future<void> _submitForm() async {
    if (!_formKey.currentState!.validate()) return;
    _formKey.currentState!.save();

    setState(() => _isLoading = true);

    final supabase = Supabase.instance.client;

    try {
      final insertData = {
        'name': _nameController.text.trim(),
        'state': _stateController.text.trim(),
        'physical_address': _addressController.text.trim(),
        'phone_number': _phoneController.text.isNotEmpty
            ? _phoneController.text.trim()
            : null,
        'website': _websiteController.text.isNotEmpty
            ? _websiteController.text.trim()
            : null,
        'email': _emailController.text.isNotEmpty
            ? _emailController.text.trim()
            : null,
        'categories_of_medications': _medicationsController.text.isNotEmpty
            ? _medicationsController.text.trim()
            : null,
        'special_services_offered': _servicesController.text.isNotEmpty
            ? _servicesController.text.trim()
            : null,
      };

      await supabase.from('pharmacies').insert(insertData);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Pharmacy added successfully'),
            backgroundColor: Colors.green,
          ),
        );

        // Clear form
        _formKey.currentState!.reset();
        _nameController.clear();
        _stateController.clear();
        _addressController.clear();
        _phoneController.clear();
        _websiteController.clear();
        _emailController.clear();
        _medicationsController.clear();
        _servicesController.clear();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error adding pharmacy: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Upload Pharmacies',
          style: TextStyle(
            color: Color.fromARGB(255, 0, 82, 103),
            fontWeight: FontWeight.bold,
            fontSize: 30,
          ),
        ),
      ),
      body: SingleChildScrollView(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 800),
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Card(
                elevation: 6,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Pharmacy Name
                        TextFormField(
                          controller: _nameController,
                          decoration: const InputDecoration(
                            labelText: 'Pharmacy Name',
                            border: OutlineInputBorder(),
                          ),
                          validator: (v) => v == null || v.isEmpty
                              ? 'Please enter pharmacy name'
                              : null,
                        ),
                        const SizedBox(height: 12),

                        // State
                        TextFormField(
                          controller: _stateController,
                          decoration: const InputDecoration(
                            labelText: 'State',
                            border: OutlineInputBorder(),
                          ),
                          validator: (v) => v == null || v.isEmpty
                              ? 'Please enter state'
                              : null,
                        ),
                        const SizedBox(height: 12),

                        // Physical Address
                        TextFormField(
                          controller: _addressController,
                          decoration: const InputDecoration(
                            labelText: 'Physical Address',
                            border: OutlineInputBorder(),
                          ),
                          maxLines: 2,
                          validator: (v) => v == null || v.isEmpty
                              ? 'Please enter address'
                              : null,
                        ),
                        const SizedBox(height: 12),

                        // Phone Number
                        TextFormField(
                          controller: _phoneController,
                          decoration: const InputDecoration(
                            labelText: 'Phone Number (Optional)',
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.phone,
                        ),
                        const SizedBox(height: 12),

                        // Website
                        TextFormField(
                          controller: _websiteController,
                          decoration: const InputDecoration(
                            labelText: 'Website (Optional)',
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.url,
                        ),
                        const SizedBox(height: 12),

                        // Email
                        TextFormField(
                          controller: _emailController,
                          decoration: const InputDecoration(
                            labelText: 'Email Address (Optional)',
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.emailAddress,
                        ),
                        const SizedBox(height: 12),

                        // Categories of Medications
                        TextFormField(
                          controller: _medicationsController,
                          decoration: const InputDecoration(
                            labelText: 'Categories of Medications (Optional)',
                            border: OutlineInputBorder(),
                            hintText:
                                'e.g., Antibiotics, Pain Relief, Vitamins',
                          ),
                          maxLines: 2,
                        ),
                        const SizedBox(height: 12),

                        // Special Services
                        TextFormField(
                          controller: _servicesController,
                          decoration: const InputDecoration(
                            labelText: 'Special Services Offered (Optional)',
                            border: OutlineInputBorder(),
                            hintText:
                                'e.g., Home Delivery, Consultation, Vaccination',
                          ),
                          maxLines: 2,
                        ),
                        const SizedBox(height: 16),

                        // Submit Button
                        ElevatedButton(
                          onPressed: _isLoading ? null : _submitForm,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color.fromARGB(
                              255,
                              0,
                              82,
                              103,
                            ),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 14.0),
                            child: _isLoading
                                ? const SizedBox(
                                    height: 16,
                                    width: 16,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                : const Text(
                                    'Add Pharmacy',
                                    style: TextStyle(
                                      fontSize: 16,
                                      color: Colors.white,
                                    ),
                                  ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _nameController.dispose();
    _stateController.dispose();
    _addressController.dispose();
    _phoneController.dispose();
    _websiteController.dispose();
    _emailController.dispose();
    _medicationsController.dispose();
    _servicesController.dispose();
    super.dispose();
  }
}
