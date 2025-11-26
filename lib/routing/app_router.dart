import 'package:diasorahub_admin/pages/home.dart';
import 'package:diasorahub_admin/pages/not_found_screen.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/',
  errorBuilder: (context, state)=> const NotFoundScreen(),
  routes:[
    GoRoute(
      path: '/',
      name: 'home',
      builder: (context, state) => const HomePage(),
    )
  ]
);
