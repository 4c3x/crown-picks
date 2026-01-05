import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class ViewDoctors extends StatefulWidget {
  const ViewDoctors({super.key});

  @override
  State<ViewDoctors> createState() => _ViewDoctorsState();
}

class _ViewDoctorsState extends State<ViewDoctors> {
  final supabase = Supabase.instance.client;
  bool _isLoading = true;
  List<dynamic> _doctors = [];
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _fetchDoctors();
  }

  Future<void> _fetchDoctors() async {
    try {
      final response = await supabase.from('doctors').select();

      if (!mounted) return;
      setState(() {
        _doctors = response;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint("Error fetching doctors: $e");
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  List<dynamic> get _filteredDoctors {
    if (_searchQuery.isEmpty) {
      return _doctors;
    }
    return _doctors.where((doctor) {
      final name = (doctor['doctor_name'] ?? '').toString().toLowerCase();
      final specialty = (doctor['specialty'] ?? '').toString().toLowerCase();
      final query = _searchQuery.toLowerCase();
      return name.contains(query) || specialty.contains(query);
    }).toList();
  }

  void _deleteDoctors(int doctorId) async {
    try {
      await supabase.from('doctors').delete().eq('id', doctorId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Doctor deleted successfully'),
          backgroundColor: Colors.green,
        ),
      );
      _fetchDoctors();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error deleting doctor: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _editDoctor(dynamic doctor) {
    final nameController = TextEditingController(text: doctor['doctor_name']);
    final licenseController = TextEditingController(
      text: doctor['license_number'],
    );
    final emailController = TextEditingController(
      text: doctor['email_address'],
    );
    final phoneController = TextEditingController(text: doctor['phone_number']);
    final addressController = TextEditingController(text: doctor['address']);
    final specialtyController = TextEditingController(
      text: doctor['specialty'],
    );
    final hospitalController = TextEditingController(
      text: doctor['affiliate_hospital'],
    );
    final medSchoolController = TextEditingController(
      text: doctor['med_school'],
    );
    final graduationYearController = TextEditingController(
      text: doctor['graduation_year']?.toString() ?? '',
    );
    final residencyController = TextEditingController(
      text: doctor['residency_training'],
    );
    bool isActive = doctor['is_active'] ?? false;

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit Doctor'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(labelText: 'Name'),
              ),
              TextField(
                controller: licenseController,
                decoration: const InputDecoration(labelText: 'License Number'),
              ),
              TextField(
                controller: emailController,
                decoration: const InputDecoration(labelText: 'Email'),
              ),
              TextField(
                controller: phoneController,
                decoration: const InputDecoration(labelText: 'Phone'),
              ),
              TextField(
                controller: addressController,
                decoration: const InputDecoration(labelText: 'Address'),
              ),
              TextField(
                controller: specialtyController,
                decoration: const InputDecoration(labelText: 'Specialty'),
              ),
              TextField(
                controller: hospitalController,
                decoration: const InputDecoration(labelText: 'Hospital'),
              ),
              TextField(
                controller: medSchoolController,
                decoration: const InputDecoration(labelText: 'Med School'),
              ),
              TextField(
                controller: graduationYearController,
                decoration: const InputDecoration(labelText: 'Graduation Year'),
              ),
              TextField(
                controller: residencyController,
                decoration: const InputDecoration(labelText: 'Residency'),
              ),
              CheckboxListTile(
                title: const Text('Active'),
                value: isActive,
                onChanged: (value) {
                  setState(() {
                    isActive = value ?? false;
                  });
                },
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () async {
              try {
                await supabase
                    .from('doctors')
                    .update({
                      'doctor_name': nameController.text,
                      'license_number': licenseController.text,
                      'email_address': emailController.text,
                      'phone_number': phoneController.text,
                      'address': addressController.text,
                      'specialty': specialtyController.text,
                      'affiliate_hospital': hospitalController.text,
                      'med_school': medSchoolController.text,
                      'graduation_year': int.tryParse(
                        graduationYearController.text,
                      ),
                      'residency_training': residencyController.text,
                      'is_active': isActive,
                    })
                    .eq('id', doctor['id']);

                if (!mounted) return;
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Doctor updated successfully'),
                    backgroundColor: Colors.green,
                  ),
                );
                _fetchDoctors();
              } catch (e) {
                if (!mounted) return;
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(SnackBar(content: Text('Error: $e')));
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  void _confirmDelete(int doctorId, String name) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Doctor'),
        content: Text('Are you sure you want to delete "$name"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _deleteDoctors(doctorId);
            },
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'View Doctors',
          style: TextStyle(
            color: Color.fromARGB(255, 0, 82, 103),
            fontWeight: FontWeight.bold,
            fontSize: 30,
          ),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _doctors.isEmpty
          ? const Center(
              child: Text('No doctors found', style: TextStyle(fontSize: 18)),
            )
          : Column(
              children: [
                // Search bar
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: TextField(
                    onChanged: (value) => setState(() => _searchQuery = value),
                    decoration: InputDecoration(
                      hintText: 'Search by name or specialty...',
                      prefixIcon: const Icon(Icons.search),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ),
                // Doctors grid
                Expanded(
                  child: _filteredDoctors.isEmpty
                      ? const Center(
                          child: Text('No doctors match your search'),
                        )
                      : GridView.builder(
                          padding: const EdgeInsets.all(16),
                          gridDelegate:
                              const SliverGridDelegateWithFixedCrossAxisCount(
                                crossAxisCount: 3,
                                mainAxisSpacing: 16,
                                crossAxisSpacing: 16,
                                childAspectRatio: 0.8,
                              ),
                          itemCount: _filteredDoctors.length,
                          itemBuilder: (context, index) {
                            final doctor = _filteredDoctors[index];
                            return Card(
                              elevation: 3,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Padding(
                                padding: const EdgeInsets.all(12.0),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    // Doctor icon
                                    Container(
                                      width: double.infinity,
                                      height: 80,
                                      decoration: BoxDecoration(
                                        color: Colors.blue.shade100,
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: Icon(
                                        Icons.medical_services,
                                        size: 40,
                                        color: Colors.blue.shade700,
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    // Name
                                    Text(
                                      doctor['doctor_name'],
                                      style: const TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.bold,
                                      ),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    // Specialty
                                    Text(
                                      doctor['specialty'] ?? '-',
                                      style: const TextStyle(fontSize: 12),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    // Email
                                    Text(
                                      doctor['email_address'] ?? '-',
                                      style: const TextStyle(fontSize: 11),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    // Status
                                    Padding(
                                      padding: const EdgeInsets.symmetric(
                                        vertical: 4.0,
                                      ),
                                      child: Chip(
                                        label: Text(
                                          doctor['is_active']
                                              ? 'Active'
                                              : 'Inactive',
                                          style: const TextStyle(fontSize: 11),
                                        ),
                                        backgroundColor: doctor['is_active']
                                            ? Colors.green.shade100
                                            : Colors.red.shade100,
                                        padding: const EdgeInsets.all(4),
                                      ),
                                    ),
                                    const Spacer(),
                                    // Action buttons
                                    Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.spaceEvenly,
                                      children: [
                                        ElevatedButton.icon(
                                          onPressed: () => _editDoctor(doctor),
                                          icon: const Icon(
                                            Icons.edit,
                                            size: 14,
                                          ),
                                          label: const Text(
                                            'Edit',
                                            style: TextStyle(fontSize: 11),
                                          ),
                                          style: ElevatedButton.styleFrom(
                                            backgroundColor: Colors.blue,
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 6,
                                              vertical: 6,
                                            ),
                                          ),
                                        ),
                                        ElevatedButton.icon(
                                          onPressed: () => _confirmDelete(
                                            doctor['id'],
                                            doctor['doctor_name'],
                                          ),
                                          icon: const Icon(
                                            Icons.delete,
                                            size: 14,
                                          ),
                                          label: const Text(
                                            'Delete',
                                            style: TextStyle(fontSize: 11),
                                          ),
                                          style: ElevatedButton.styleFrom(
                                            backgroundColor: Colors.red,
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 6,
                                              vertical: 6,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
    );
  }
}
