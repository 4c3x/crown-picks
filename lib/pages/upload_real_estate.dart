import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

class UploadEstate extends StatefulWidget {
  const UploadEstate({super.key});

  @override
  State<UploadEstate> createState() => _UploadEstateState();
}

class _UploadEstateState extends State<UploadEstate> {
  final _formKey = GlobalKey<FormState>();

  Uint8List? _pickedImageBytes;
  String? _location;
  String? _dollarAmount;
  String? _nairaAmount;
  int _bedrooms = 1;
  int _toilets = 1;
  String? _sqft;

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

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    _formKey.currentState!.save();
    
    final payload = {
      'location': _location,
      'dollar': _dollarAmount,
      'naira': _nairaAmount,
      'bedrooms': _bedrooms,
      'toilets': _toilets,
      'sqft': _sqft,
      'hasImage': _pickedImageBytes != null,
    };

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Preview'),
        content: SingleChildScrollView(
          child: Text(payload.toString()),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
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
                        // Image upload area
                        GestureDetector(
                          onTap: _pickImage,
                          child: Container(
                            height: 300,
                            decoration: BoxDecoration(
                              color: Colors.grey[200],
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: Colors.grey.shade400),
                            ),
                            child: _pickedImageBytes == null
                                ? Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: const [
                                      Icon(Icons.cloud_upload, size: 48),
                                      SizedBox(height: 8),
                                      Text('Tap to upload image'),
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
                        ),
                        const SizedBox(height: 12),

                        // Naira amount
                        TextFormField(
                          decoration: const InputDecoration(
                            labelText: 'Amount (NGN)',
                            prefixIcon: Icon(Icons.currency_exchange),
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.number,
                          onSaved: (v) => _nairaAmount = v,
                        ),
                        const SizedBox(height: 12),

                        
                        Row(
                          children: [
                            Expanded(
                              child: DropdownButtonFormField<int>(
                                value: _bedrooms,
                                decoration: const InputDecoration(
                                  labelText: 'Bedrooms',
                                  prefixIcon: Icon(Icons.bed),
                                  border: OutlineInputBorder(),
                                ),
                                items: List.generate(10, (i) => i + 1)
                                    .map((n) => DropdownMenuItem(value: n, child: Text('$n')))
                                    .toList(),
                                onChanged: (v) => setState(() => _bedrooms = v ?? 1),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: DropdownButtonFormField<int>(
                                value: _toilets,
                                decoration: const InputDecoration(
                                  labelText: 'Toilets',
                                  prefixIcon: Icon(Icons.bathtub),
                                  border: OutlineInputBorder(),
                                ),
                                items: List.generate(10, (i) => i + 1)
                                    .map((n) => DropdownMenuItem(value: n, child: Text('$n')))
                                    .toList(),
                                onChanged: (v) => setState(() => _toilets = v ?? 1),
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
                        ),
                        const SizedBox(height: 16),

                        ElevatedButton(
                          onPressed: _submit,
                          child: const Padding(
                            padding: EdgeInsets.symmetric(vertical: 14.0),
                            child: Text('Submit', style: TextStyle(fontSize: 16)),
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