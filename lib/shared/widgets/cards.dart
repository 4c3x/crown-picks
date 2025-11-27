import 'package:flutter/material.dart';

class UploadCard extends StatelessWidget {
  final String title;
  final IconData? icon;
  final VoidCallback? onTap;
  const UploadCard({super.key, required this.title, this.icon, this.onTap});

  @override
  Widget build(BuildContext context) {
    return Row(
              children: [
                Padding(
                  padding: const EdgeInsets.all(40.0),
                  child: GestureDetector(
                    onTap: onTap,
                    child: Card(
                      elevation: 10,
                      color: const Color.fromARGB(221, 20, 72, 98),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: SizedBox(
                        width: MediaQuery.of(context).size.width * 0.4,
                        height: 250,
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              icon,
                              size: 100,
                              color: const Color.fromARGB(188, 255, 255, 255),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              title,
                              style: const TextStyle(
                                color: Color.fromARGB(255, 255, 191, 1),
                                fontSize: 20,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ],
          );
  }
}