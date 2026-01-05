import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';


class FilePickerRow extends StatelessWidget {
  final String label;
  final List<String> allowedExtensions;
  final String? fileName;
  final IconData icon;
  final void Function(Uint8List? bytes, String? name) onPicked;

  const FilePickerRow({
    super.key,
    required this.label,
    this.allowedExtensions = const ['pdf'],
    this.fileName,
    this.icon = Icons.attach_file,
    required this.onPicked,
  });

  Future<void> _pick(BuildContext context) async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: allowedExtensions,
        withData: true,
      );
      if (result != null && result.files.isNotEmpty) {
        final file = result.files.first;
        onPicked(file.bytes, file.name);
      } else {
        onPicked(null, null);
      }
    } catch (e) {
      // For robustness, call the callback with nulls and log the error.
      debugPrint('Failed to pick file: $e');
      onPicked(null, null);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton.icon(
            onPressed: () => _pick(context),
            icon: Icon(icon, color: Colors.blue),
            label: Text(label),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Text(
            fileName ?? 'No file selected',
            style: TextStyle(color: fileName != null ? Colors.black87 : Colors.grey[600]),
          ),
        ),
      ],
    );
  }
}
