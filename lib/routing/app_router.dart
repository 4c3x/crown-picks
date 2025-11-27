import 'package:diasorahub_admin/pages/home.dart';
import 'package:diasorahub_admin/pages/loginscreen.dart';
import 'package:diasorahub_admin/pages/not_found_screen.dart';
import 'package:diasorahub_admin/pages/upload_doctors.dart';
import 'package:diasorahub_admin/pages/upload_real_estate.dart';
import 'package:diasorahub_admin/pages/view_doctors.dart';
import 'package:diasorahub_admin/pages/view_real_estate.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/',
  errorBuilder: (context, state)=> const NotFoundScreen(),
  routes:[
    GoRoute(path: '/',
    name: 'login',
    builder: (context, state) => const LoginScreen(),
    ), 
    GoRoute(
      path: '/home',
      name: 'home',
      builder: (context, state) => const HomePage(),
    ),
    GoRoute(
      path:'/upload_estate',
      name:'upload_estate',
      builder: (context, state) => const UploadEstate(),
    ),
    GoRoute(
      path: '/view_estate',
      name: 'view_estate',
      builder: (context, state)=> const ViewEstate(),
    ), 
    GoRoute(
      path: '/upload_doctors',
      name: 'upload_doctors',
      builder: (context, state) => const UploadDoctors(),
    ),
    GoRoute(
      path: '/view_doctors',
      name: 'view_doctors',
      builder: (context, state) => const ViewDoctors(),
    ),
  ]
);
