import 'package:flutter/material.dart';

class CustomTextField extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final IconData icon;
  final TextInputType keyboardType;
  final bool obscure;

  /// Optional styling
  final double height; // total height of the field
  final double borderRadius;
  final Color? fillColor;
  final EdgeInsetsGeometry? contentPadding;

  const CustomTextField({
    super.key,
    required this.controller,
    required this.label,
    required this.icon,
    this.keyboardType = TextInputType.text,
    this.obscure = false,
    this.height = 56.0,
    this.borderRadius = 12.0,
    this.fillColor,
    this.contentPadding,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final Color effectiveFill = fillColor ?? Colors.grey.shade100;

    return SizedBox(
      height: height,
      child: TextFormField(
        controller: controller,
        keyboardType: keyboardType,
        obscureText: obscure,
        decoration: InputDecoration(
          labelText: label,
          // smaller icon and some spacing
          prefixIcon: Padding(
            padding: const EdgeInsets.only(left: 12.0, right: 8.0),
            child: Icon(icon, size: 20),
          ),
          prefixIconConstraints: const BoxConstraints(minWidth: 44, minHeight: 44),
          isDense: true,
          contentPadding: contentPadding ?? const EdgeInsets.symmetric(vertical: 14.0, horizontal: 12.0),
          filled: true,
          fillColor: effectiveFill,
          labelStyle: theme.textTheme.bodyMedium?.copyWith(fontSize: 14),
          hintStyle: theme.textTheme.bodyMedium?.copyWith(color: Colors.grey[600]),
          // Rounded borders with subtle outline on focus
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(borderRadius),
            borderSide: BorderSide.none,
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(borderRadius),
            borderSide: BorderSide(color: Colors.transparent),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(borderRadius),
            borderSide: BorderSide(color: theme.colorScheme.primary, width: 2.0),
          ),
          errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(borderRadius),
            borderSide: BorderSide(color: theme.colorScheme.error),
          ),
        ),
  style: theme.textTheme.bodyMedium,
        validator: (value) => value == null || value.isEmpty ? 'Please enter $label' : null,
      ),
    );
  }
}