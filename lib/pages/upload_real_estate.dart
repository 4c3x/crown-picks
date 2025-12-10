import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:diasorahub_admin/shared/widgets/file_picker_row.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

// storage bucket used for uploaded files. Change here if you use a different bucket.
const String _storageBucket = 'properties';

class UploadEstate extends StatefulWidget {
  const UploadEstate({super.key});

  @override
  State<UploadEstate> createState() => _UploadEstateState();
}

class _UploadEstateState extends State<UploadEstate> {
  final _formKey = GlobalKey<FormState>();

  Uint8List? _pickedImageBytes;
  Uint8List? _pickedPdfBytes;
  String? _pickedPdfName;
  String? _location;
  String? _dollarAmount;
  String? _nairaAmount;
  String? _title;
  String? _description;
  String? _propertyType = 'Villa';
  String? _listingType = 'For Sale';
  int _bedrooms = 1;
  int _bathrooms = 1;
  String? _sqft;
  bool _isLoading = false;

  Future<void> _pickImage() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      withData: true,
    );
    if (result != null && result.files.isNotEmpty) {
      final file = result.files.first;
      setState(() {
        _pickedImageBytes = file.bytes;
      });
    }
  }
  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    _formKey.currentState!.save();

    final payload = {
      'title': _title,
      'description': _description,
      'location': _location,
      'dollar': _dollarAmount,
      'naira': _nairaAmount,
      'propertyType': _propertyType,
      'listingType': _listingType,
      'bedrooms': _bedrooms,
      'bathrooms': _bathrooms,
      'sqft': _sqft,
      'hasImage': _pickedImageBytes != null,
      'hasPdf': _pickedPdfBytes != null,
    };

  
    // Image is required (PDF is optional)
    if (_pickedImageBytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please upload an image for the property')),
      );
      return;
    }

    setState(() {
      _isLoading = true;
    });

    final supabase = Supabase.instance.client;
    debugPrint('AUTH USER: ${supabase.auth.currentUser}');
    try {
      final imagePath = 'property_images/${DateTime.now().millisecondsSinceEpoch}.jpg';

      // provide a content type so Supabase serves the correct MIME type
      await supabase.storage.from(_storageBucket).uploadBinary(
        imagePath,
        _pickedImageBytes!,
        fileOptions: const FileOptions(contentType: 'image/jpeg'),
      );

      final imageUrl = supabase.storage.from(_storageBucket).getPublicUrl(imagePath);
      debugPrint('imageUrl: $imageUrl');

      String? pdfUrl;
      if (_pickedPdfBytes != null && _pickedPdfName != null) {
        // sanitize filename by using only the extension and a timestamp-based name
        final extension = _pickedPdfName!.split('.').isNotEmpty
            ? _pickedPdfName!.split('.').last
            : 'pdf';
        final pdfPath = 'property_pdfs/${DateTime.now().millisecondsSinceEpoch}.$extension';

        await supabase.storage.from(_storageBucket).uploadBinary(
          pdfPath,
          _pickedPdfBytes!,
          fileOptions: const FileOptions(contentType: 'application/pdf'),
        );

        pdfUrl = supabase.storage.from(_storageBucket).getPublicUrl(pdfPath);
        debugPrint('pdfUrl: $pdfUrl');
      }
      String listingTypeDB =
      _listingType == 'For Sale' ? 'sale' : 'rent';

      // Insert record into Supabase 'properties' table
      final insertData = {
        'title': _title,
        'description': _description,
        'location': _location,
        'price_usd': double.tryParse(_dollarAmount ?? '0') ?? 0,
        'price_ngn': double.tryParse(_nairaAmount ?? '0') ?? 0,
        'bedrooms': _bedrooms,
        'bathrooms': _bathrooms,
        'square_feet': double.tryParse(_sqft ?? '0') ?? 0,
        'property_type': _propertyType?.toLowerCase(),
        'listing_type': listingTypeDB,
        'main_image': imageUrl,
        'floor_plan_pdf': pdfUrl,
        'status': 'available',
        'application_fee_usd': 100,
        'application_fee_ngn': 45000,
      };

  final inserted = await supabase.from('properties').insert(insertData).select();
      debugPrint('Inserted property: $inserted');

      // On success show a success message and clear the form (only if still mounted)
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Upload successful'), backgroundColor: Colors.green),
        );

        // Reset state
        _formKey.currentState!.reset();
        setState(() {
          _pickedImageBytes = null;
          _pickedPdfBytes = null;
          _pickedPdfName = null;
          _title = null;
          _description = null;
          _propertyType = 'Villa';
          _listingType = 'For Sale';
          _location = null;
          _dollarAmount = null;
          _nairaAmount = null;
          _bedrooms = 1;
          _bathrooms = 1;
          _sqft = null;
        });
      } else {
        debugPrint('Upload succeeded but widget is no longer mounted; skipping UI update.');
      }
    } catch (e, st) {
      debugPrint('Upload failed: $e\n$st');

      final errTxt = e.toString();
      final userMessage = errTxt.contains('Bucket not found')
          ? 'Upload failed: storage bucket "$_storageBucket" not found for the configured Supabase project. Create the bucket or update the bucket name in code.'
          : 'Upload failed: ${errTxt.split('\n').first}';

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(userMessage)),
        );
      } else {
        debugPrint('Could not show error to user because widget is unmounted: $userMessage');
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Upload Real Estate',
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
                        // Title
                        TextFormField(
                          decoration: const InputDecoration(
                            labelText: 'Title',
                            border: OutlineInputBorder(),
                          ),
                          onSaved: (v) => _title = v,
                          validator: (v) => v == null || v.isEmpty ? 'Please enter a title' : null,
                        ),
                        const SizedBox(height: 12),

                        // Description
                        TextFormField(
                          decoration: const InputDecoration(
                            labelText: 'Description',
                            border: OutlineInputBorder(),
                          ),
                          maxLines: 4,
                          onSaved: (v) => _description = v,
                          validator: (v) => v == null || v.isEmpty ? 'Please enter a description' : null,
                        ),
                        const SizedBox(height: 12),

                        // Property & listing type
                        Row(
                          children: [
                            Expanded(
                              child: DropdownButtonFormField<String>(
                                initialValue: _propertyType,
                                decoration: const InputDecoration(
                                  labelText: 'Property Type',
                                  border: OutlineInputBorder(),
                                ),
                                items: ['Villa', 'Townhouse', 'Apartment']
                                    .map((t) => DropdownMenuItem(value: t, child: Text(t)))
                                    .toList(),
                                onChanged: (v) => setState(() => _propertyType = v),
                                validator: (v) => v == null || v.isEmpty ? 'Please select a property type' : null,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: DropdownButtonFormField<String>(
                                initialValue: _listingType,
                                decoration: const InputDecoration(
                                  labelText: 'Listing Type',
                                  border: OutlineInputBorder(),
                                ),
                                items: const [
                                  DropdownMenuItem(value: 'For Sale', child: Text('For Sale')),
                                  DropdownMenuItem(value: 'For Rent', child: Text('For Rent')),
                                ],
                                onChanged: (v) => setState(() => _listingType = v),
                                validator: (v) => v == null || v.isEmpty ? 'Please select a listing type' : null,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),

                        // Image upload area
                        GestureDetector(
                          onTap: _pickImage,
                          child: Container(
                            height: 300,
                            decoration: BoxDecoration(
                              color: Colors.grey[200],
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: Colors.blue.shade100),
                            ),
                            child: _pickedImageBytes == null
                                ? Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Icon(Icons.cloud_upload, size: 48, color: Colors.blue[600]),
                                      const SizedBox(height: 8),
                                      Text('Tap to upload image', style: TextStyle(color: Colors.blue[700])),
                                    ],
                                  )
                                : ClipRRect(
                                    borderRadius: BorderRadius.circular(8),
                                    child: Image.memory(
                                      _pickedImageBytes!,
                                      fit: BoxFit.cover,
                                      width: double.infinity,
                                      height: double.infinity,
                                    ),
                                  ),
                          ),
                        ),
                        const SizedBox(height: 16),

                        // PDF upload (reusable row)
                        FilePickerRow(
                          label: 'Upload PDF',
                          allowedExtensions: const ['pdf'],
                          fileName: _pickedPdfName,
                          icon: Icons.picture_as_pdf,
                          onPicked: (bytes, name) => setState(() {
                            _pickedPdfBytes = bytes;
                            _pickedPdfName = name;
                          }),
                        ),
                        const SizedBox(height: 16),

                        // Location
                        TextFormField(
                          decoration: const InputDecoration(
                            labelText: 'Location',
                            prefixIcon: Icon(Icons.location_on),
                            border: OutlineInputBorder(),
                          ),
                          onSaved: (v) => _location = v,
                          validator: (v) => v == null || v.isEmpty ? 'Please enter location' : null,
                        ),
                        const SizedBox(height: 12),

                        // Dollar amount
                        TextFormField(
                          decoration: const InputDecoration(
                            labelText: 'Amount (USD)',
                            prefixIcon: Icon(Icons.attach_money),
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.number,
                          onSaved: (v) => _dollarAmount = v,
                          validator: (v) => v == null || v.isEmpty ? 'Please enter USD amount' : null,
                        ),
                        const SizedBox(height: 12),

                        // Naira amount
                        TextFormField(
                          decoration: const InputDecoration(
                            labelText: 'Amount (NGN)',
                            prefixText: 'NGN ',
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.number,
                          onSaved: (v) => _nairaAmount = v,
                          validator: (v) => v == null || v.isEmpty ? 'Please enter NGN amount' : null,
                        ),
                        const SizedBox(height: 12),

                        
                        Row(
                          children: [
                            Expanded(
                              child: DropdownButtonFormField<int>(
                                initialValue: _bedrooms,
                                decoration: const InputDecoration(
                                  labelText: 'Bedrooms',
                                  prefixIcon: Icon(Icons.bed),
                                  border: OutlineInputBorder(),
                                ),
                                items: List.generate(10, (i) => i + 1)
                                    .map((n) => DropdownMenuItem(value: n, child: Text('$n')))
                                    .toList(),
                                onChanged: (v) => setState(() => _bedrooms = v ?? 1),
                                validator: (v) => v == null ? 'Please select bedrooms' : null,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: DropdownButtonFormField<int>(
                                  initialValue: _bathrooms,
                                  decoration: const InputDecoration(
                                    labelText: 'Bathrooms',
                                    prefixIcon: Icon(Icons.bathtub),
                                    border: OutlineInputBorder(),
                                  ),
                                  items: List.generate(10, (i) => i + 1)
                                      .map((n) => DropdownMenuItem(value: n, child: Text('$n')))
                                      .toList(),
                                  onChanged: (v) => setState(() => _bathrooms = v ?? 1),
                                  validator: (v) => v == null ? 'Please select bathrooms' : null,
                                ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),

                        // Sqft
                        TextFormField(
                          decoration: const InputDecoration(
                            labelText: 'Square feet',
                            prefixIcon: Icon(Icons.square_foot),
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.number,
                          onSaved: (v) => _sqft = v,
                          validator: (v) => v == null || v.isEmpty ? 'Please enter square feet' : null,
                        ),
                        const SizedBox(height: 16),

                        ElevatedButton(
                          onPressed: _isLoading ? null : _submit,
                          style: ElevatedButton.styleFrom(backgroundColor: const Color.fromARGB(255, 0, 82, 103)),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 14.0),
                            child: _isLoading
                                ? const SizedBox(
                                    height: 16,
                                    width: 16,
                                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                  )
                                : const Text('Submit',
                                    style: TextStyle(
                                      fontSize: 16,
                                      color: Colors.white,
                                    )),
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
}