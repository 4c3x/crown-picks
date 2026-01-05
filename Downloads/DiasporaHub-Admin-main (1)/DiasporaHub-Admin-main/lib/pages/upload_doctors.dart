import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class UploadDoctors extends StatefulWidget {
  const UploadDoctors({super.key});

  @override
  State<UploadDoctors> createState() => _UploadDoctorsState();
}

class _UploadDoctorsState extends State<UploadDoctors> {
  final _formKey = GlobalKey<FormState>();
  bool _isLoading = false;

  // Form controllers
  final _nameController = TextEditingController();
  final _licenseController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _addressController = TextEditingController();
  final _hospitalController = TextEditingController();
  final _specialtyController = TextEditingController();
  final _medSchoolController = TextEditingController();
  final _graduationYearController = TextEditingController();
  final _residencyController = TextEditingController();

  bool _isActive = true;

  Future<void> _submitForm() async {
    if (!_formKey.currentState!.validate()) return;
    _formKey.currentState!.save();

    setState(() => _isLoading = true);

    final supabase = Supabase.instance.client;

    try {
      final insertData = {
        'doctor_name': _nameController.text.trim(),
        'license_number': _licenseController.text.trim(),
        'phone_number': _phoneController.text.trim(),
        'email_address': _emailController.text.trim().toLowerCase(),
        'address': _addressController.text.trim(),
        'affiliate_hospital': _hospitalController.text.trim(),
        'specialty': _specialtyController.text.trim(),
        'med_school': _medSchoolController.text.isNotEmpty
            ? _medSchoolController.text.trim()
            : null,
        'graduation_year': _graduationYearController.text.isNotEmpty
            ? int.tryParse(_graduationYearController.text.trim())
            : null,
        'residency_training': _residencyController.text.isNotEmpty
            ? _residencyController.text.trim()
            : null,
        'is_active': _isActive,
      };

      await supabase.from('doctors').insert(insertData);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Doctor added successfully'),
            backgroundColor: Colors.green,
          ),
        );

        // Clear form
        _formKey.currentState!.reset();
        _nameController.clear();
        _licenseController.clear();
        _phoneController.clear();
        _emailController.clear();
        _addressController.clear();
        _hospitalController.clear();
        _specialtyController.clear();
        _medSchoolController.clear();
        _graduationYearController.clear();
        _residencyController.clear();
        setState(() => _isActive = true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error adding doctor: ${e.toString()}'),
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
          'Upload Doctors',
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
                        // Doctor Name
                        TextFormField(
                          controller: _nameController,
                          decoration: const InputDecoration(
                            labelText: 'Doctor Name',
                            border: OutlineInputBorder(),
                          ),
                          validator: (v) => v == null || v.isEmpty
                              ? 'Please enter doctor name'
                              : null,
                        ),
                        const SizedBox(height: 12),

                        // License Number
                        TextFormField(
                          controller: _licenseController,
                          decoration: const InputDecoration(
                            labelText: 'License Number',
                            border: OutlineInputBorder(),
                          ),
                          validator: (v) => v == null || v.isEmpty
                              ? 'Please enter license number'
                              : null,
                        ),
                        const SizedBox(height: 12),

                        // Email
                        TextFormField(
                          controller: _emailController,
                          decoration: const InputDecoration(
                            labelText: 'Email Address',
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.emailAddress,
                          validator: (v) {
                            if (v == null || v.isEmpty) {
                              return 'Please enter email';
                            }
                            if (!RegExp(
                              r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                            ).hasMatch(v)) {
                              return 'Please enter a valid email';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: 12),

                        // Phone Number
                        TextFormField(
                          controller: _phoneController,
                          decoration: const InputDecoration(
                            labelText: 'Phone Number',
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.phone,
                          validator: (v) => v == null || v.isEmpty
                              ? 'Please enter phone number'
                              : null,
                        ),
                        const SizedBox(height: 12),

                        // Specialty
                        TextFormField(
                          controller: _specialtyController,
                          decoration: const InputDecoration(
                            labelText: 'Specialty',
                            border: OutlineInputBorder(),
                          ),
                          validator: (v) => v == null || v.isEmpty
                              ? 'Please enter specialty'
                              : null,
                        ),
                        const SizedBox(height: 12),

                        // Address
                        TextFormField(
                          controller: _addressController,
                          decoration: const InputDecoration(
                            labelText: 'Address',
                            border: OutlineInputBorder(),
                          ),
                          maxLines: 2,
                          validator: (v) => v == null || v.isEmpty
                              ? 'Please enter address'
                              : null,
                        ),
                        const SizedBox(height: 12),

                        // Affiliate Hospital
                        TextFormField(
                          controller: _hospitalController,
                          decoration: const InputDecoration(
                            labelText: 'Affiliate Hospital',
                            border: OutlineInputBorder(),
                          ),
                          validator: (v) => v == null || v.isEmpty
                              ? 'Please enter affiliate hospital'
                              : null,
                        ),
                        const SizedBox(height: 12),

                        // Medical School
                        TextFormField(
                          controller: _medSchoolController,
                          decoration: const InputDecoration(
                            labelText: 'Medical School (Optional)',
                            border: OutlineInputBorder(),
                          ),
                        ),
                        const SizedBox(height: 12),

                        // Graduation Year
                        TextFormField(
                          controller: _graduationYearController,
                          decoration: const InputDecoration(
                            labelText: 'Graduation Year (Optional)',
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.number,
                        ),
                        const SizedBox(height: 12),

                        // Residency Training
                        TextFormField(
                          controller: _residencyController,
                          decoration: const InputDecoration(
                            labelText: 'Residency Training (Optional)',
                            border: OutlineInputBorder(),
                          ),
                          maxLines: 2,
                        ),
                        const SizedBox(height: 12),

                        // Is Active Checkbox
                        CheckboxListTile(
                          title: const Text('Is Active'),
                          value: _isActive,
                          onChanged: (value) =>
                              setState(() => _isActive = value ?? true),
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
                                    'Add Doctor',
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
    _licenseController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _addressController.dispose();
    _hospitalController.dispose();
    _specialtyController.dispose();
    _medSchoolController.dispose();
    _graduationYearController.dispose();
    _residencyController.dispose();
    super.dispose();
  }
}
