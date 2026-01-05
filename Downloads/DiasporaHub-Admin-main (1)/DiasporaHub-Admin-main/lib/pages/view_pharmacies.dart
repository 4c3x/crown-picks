import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class ViewPharmacies extends StatefulWidget {
  const ViewPharmacies({super.key});

  @override
  State<ViewPharmacies> createState() => _ViewPharmaciesState();
}

class _ViewPharmaciesState extends State<ViewPharmacies> {
  final supabase = Supabase.instance.client;
  bool _isLoading = true;
  List<dynamic> _pharmacies = [];
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _fetchPharmacies();
  }

  Future<void> _fetchPharmacies() async {
    try {
      final response = await supabase.from('pharmacies').select();

      if (!mounted) return;
      setState(() {
        _pharmacies = response;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint("Error fetching pharmacies: $e");
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  List<dynamic> get _filteredPharmacies {
    if (_searchQuery.isEmpty) {
      return _pharmacies;
    }
    return _pharmacies.where((pharmacy) {
      final name = (pharmacy['name'] ?? '').toString().toLowerCase();
      final state = (pharmacy['state'] ?? '').toString().toLowerCase();
      final query = _searchQuery.toLowerCase();
      return name.contains(query) || state.contains(query);
    }).toList();
  }

  void _deletePharmacy(int pharmacyId) async {
    try {
      await supabase.from('pharmacies').delete().eq('id', pharmacyId);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Pharmacy deleted successfully'),
          backgroundColor: Colors.green,
        ),
      );
      _fetchPharmacies();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error deleting pharmacy: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _editPharmacy(dynamic pharmacy) {
    final nameController = TextEditingController(text: pharmacy['name']);
    final stateController = TextEditingController(text: pharmacy['state']);
    final addressController = TextEditingController(
      text: pharmacy['physical_address'],
    );
    final phoneController = TextEditingController(
      text: pharmacy['phone_number'],
    );
    final websiteController = TextEditingController(text: pharmacy['website']);
    final emailController = TextEditingController(text: pharmacy['email']);
    final categoriesController = TextEditingController(
      text: pharmacy['categories_of_medications'],
    );
    final servicesController = TextEditingController(
      text: pharmacy['special_services_offered'],
    );

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Edit Pharmacy'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(labelText: 'Name'),
              ),
              TextField(
                controller: stateController,
                decoration: const InputDecoration(labelText: 'State'),
              ),
              TextField(
                controller: addressController,
                decoration: const InputDecoration(labelText: 'Address'),
              ),
              TextField(
                controller: phoneController,
                decoration: const InputDecoration(labelText: 'Phone'),
              ),
              TextField(
                controller: websiteController,
                decoration: const InputDecoration(labelText: 'Website'),
              ),
              TextField(
                controller: emailController,
                decoration: const InputDecoration(labelText: 'Email'),
              ),
              TextField(
                controller: categoriesController,
                decoration: const InputDecoration(
                  labelText: 'Categories of Medications',
                ),
                maxLines: 2,
              ),
              TextField(
                controller: servicesController,
                decoration: const InputDecoration(
                  labelText: 'Special Services',
                ),
                maxLines: 2,
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
                    .from('pharmacies')
                    .update({
                      'name': nameController.text,
                      'state': stateController.text,
                      'physical_address': addressController.text,
                      'phone_number': phoneController.text,
                      'website': websiteController.text,
                      'email': emailController.text,
                      'categories_of_medications': categoriesController.text,
                      'special_services_offered': servicesController.text,
                    })
                    .eq('id', pharmacy['id']);

                if (!mounted) return;
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Pharmacy updated successfully'),
                    backgroundColor: Colors.green,
                  ),
                );
                _fetchPharmacies();
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

  void _confirmDelete(int pharmacyId, String name) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Pharmacy'),
        content: Text('Are you sure you want to delete "$name"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(context);
              _deletePharmacy(pharmacyId);
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
          'View Pharmacies',
          style: TextStyle(
            color: Color.fromARGB(255, 0, 82, 103),
            fontWeight: FontWeight.bold,
            fontSize: 30,
          ),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _pharmacies.isEmpty
          ? const Center(
              child: Text(
                'No pharmacies found',
                style: TextStyle(fontSize: 18),
              ),
            )
          : Column(
              children: [
                // Search bar
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: TextField(
                    onChanged: (value) => setState(() => _searchQuery = value),
                    decoration: InputDecoration(
                      hintText: 'Search by name or state...',
                      prefixIcon: const Icon(Icons.search),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ),
                // Pharmacies grid
                Expanded(
                  child: _filteredPharmacies.isEmpty
                      ? const Center(
                          child: Text('No pharmacies match your search'),
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
                          itemCount: _filteredPharmacies.length,
                          itemBuilder: (context, index) {
                            final pharmacy = _filteredPharmacies[index];
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
                                    // Pharmacy icon
                                    Container(
                                      width: double.infinity,
                                      height: 80,
                                      decoration: BoxDecoration(
                                        color: Colors.green.shade100,
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: Icon(
                                        Icons.local_pharmacy,
                                        size: 40,
                                        color: Colors.green.shade700,
                                      ),
                                    ),
                                    const SizedBox(height: 8),
                                    // Name
                                    Text(
                                      pharmacy['name'],
                                      style: const TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.bold,
                                      ),
                                      maxLines: 2,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    // State
                                    Text(
                                      pharmacy['state'] ?? '-',
                                      style: const TextStyle(fontSize: 12),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    // Address
                                    Text(
                                      pharmacy['physical_address'] ?? '-',
                                      style: const TextStyle(fontSize: 11),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    // Phone
                                    Text(
                                      pharmacy['phone_number'] ?? '-',
                                      style: const TextStyle(fontSize: 11),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    const Spacer(),
                                    // Action buttons
                                    Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.spaceEvenly,
                                      children: [
                                        ElevatedButton.icon(
                                          onPressed: () =>
                                              _editPharmacy(pharmacy),
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
                                            pharmacy['id'],
                                            pharmacy['name'],
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
