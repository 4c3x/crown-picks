import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class ViewEstate extends StatefulWidget {
  const ViewEstate({super.key});

  @override
  State<ViewEstate> createState() => _ViewEstateState();
}

class _ViewEstateState extends State<ViewEstate> {
  final supabase = Supabase.instance.client;
  bool _isLoading = true;
  List<dynamic> _properties = [];

  @override
  void initState() {
    super.initState();
    _fetchProperties();
  }

  Future<void> _fetchProperties() async {
    try {
      final response = await supabase.from('properties').select();

      setState(() {
        _properties = response;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint("Error fetching properties: $e");
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "View Real Estates",
          style: TextStyle(
            color: Color.fromARGB(255, 0, 82, 103),
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _properties.isEmpty
              ? const Center(
                  child: Text(
                    "No properties uploaded yet.",
                    style: TextStyle(fontSize: 18),
                  ),
                )
              : GridView.builder(
                  padding: const EdgeInsets.all(16),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 3,
                    mainAxisSpacing: 20,
                    crossAxisSpacing: 20,
                    childAspectRatio: 0.7,
                  ),
                  itemCount: _properties.length,
                  itemBuilder: (context, index) {
                    final property = _properties[index];

                    return Card(
                      elevation: 3,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // Image
                          ClipRRect(
                            borderRadius: const BorderRadius.vertical(
                              top: Radius.circular(12),
                            ),
                            child: Image.network(
                              property['main_image'],
                              height: 150,
                              fit: BoxFit.cover,
                              errorBuilder: (c, e, s) =>
                                  const Icon(Icons.broken_image, size: 80),
                            ),
                          ),

                          // Title
                          Padding(
                            padding: const EdgeInsets.all(8.0),
                            child: Text(
                              property['title'],
                              style: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),

                          // Location
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 8),
                            child: Text(
                              property['location'],
                              style: const TextStyle(fontSize: 14),
                            ),
                          ),

                          // Price
                          Padding(
                            padding: const EdgeInsets.all(8.0),
                            child: Text(
                              "\$${property['price_usd']} | ₦${property['price_ngn']}",
                              style: const TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),

                          const Spacer(),

                          // View Details button
                          Padding(
                            padding: const EdgeInsets.all(8.0),
                            child: ElevatedButton(
                              onPressed: () {
                                // Implement view details functionality

                              },
                              style: ElevatedButton.styleFrom(
                                backgroundColor:
                                    const Color.fromARGB(255, 0, 82, 103),
                              ),
                              child: const Text("View Details",
                              style:TextStyle(
                                color: Colors.white,
                              ),),
                            ),
                          )
                        ],
                      ),
                    );
                  },
                ),
    );
  }
}
