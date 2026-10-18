// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import 'package:flutter/material.dart';
import '../services/vertex_ai_client.dart';
import '../theme/app_theme.dart';

class SettingsDrawer extends StatefulWidget {
  final String currentToken;
  final String? currentEndpoint;
  final int currentDimension;
  final ValueChanged<String> onTokenSaved;
  final ValueChanged<int>? onDimensionChanged;
  final Future<bool> Function()? onTestConnection;
  final VoidCallback? onManageFolders;

  const SettingsDrawer({
    super.key,
    required this.currentToken,
    this.currentEndpoint,
    this.currentDimension = 768,
    required this.onTokenSaved,
    this.onDimensionChanged,
    this.onTestConnection,
    this.onManageFolders,
  });

  @override
  State<SettingsDrawer> createState() => _SettingsDrawerState();
}

class _SettingsDrawerState extends State<SettingsDrawer> {
  late final TextEditingController _tokenController;
  bool _isTesting = false;
  String? _testResult;
  bool? _testSuccess;

  @override
  void initState() {
    super.initState();
    _tokenController = TextEditingController(text: widget.currentToken);
  }

  @override
  void dispose() {
    _tokenController.dispose();
    super.dispose();
  }

  Future<void> _handleTestConnection() async {
    setState(() {
      _isTesting = true;
      _testResult = null;
      _testSuccess = null;
    });

    try {
      final success = widget.onTestConnection != null
          ? await widget.onTestConnection!()
          : await VertexAiClient(defaultToken: _tokenController.text.trim())
              .testConnection();

      setState(() {
        _isTesting = false;
        _testSuccess = success;
        _testResult = success
            ? '🟢 Connected: Endpoint is ready & responding'
            : '🔴 Connection failed. Check token or endpoint.';
      });
    } catch (e) {
      setState(() {
        _isTesting = false;
        _testSuccess = false;
        _testResult = '🔴 Error: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Drawer(
      backgroundColor: AppTheme.creamCanvas,
      child: SafeArea(
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppTheme.amberPrimary.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.hub_rounded, color: AppTheme.amberPrimary, size: 24),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Text(
                    'Settings & Cloud Sync',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.textMain,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Mode indicator (clean status card)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: AppTheme.surfaceWhite,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppTheme.borderSubtle),
              ),
              child: const Row(
                children: [
                  Icon(Icons.bolt_rounded, size: 18, color: AppTheme.amberPrimary),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Cloud + Local Hybrid Mode',
                      style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: AppTheme.textMain),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Token input
            const Text(
              'Google Cloud Access Token',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textMain),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _tokenController,
              decoration: const InputDecoration(
                hintText: 'Paste token (ya29...)',
                isDense: true,
              ),
              style: const TextStyle(fontSize: 13),
              maxLines: 2,
            ),
            const SizedBox(height: 10),
            ElevatedButton(
              onPressed: () {
                widget.onTokenSaved(_tokenController.text.trim());
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Access token saved!'),
                    backgroundColor: AppTheme.amberPrimary,
                    duration: Duration(seconds: 2),
                  ),
                );
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.amberPrimary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: const Text('Save Token'),
            ),
            const SizedBox(height: 16),

            // Test Connection
            OutlinedButton.icon(
              onPressed: _isTesting ? null : _handleTestConnection,
              icon: _isTesting
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.sync_rounded, size: 16),
              label: const Text('Test Endpoint Connection'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.ceruleanBlue,
                side: const BorderSide(color: AppTheme.ceruleanBlue),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            if (_testResult != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: (_testSuccess == true ? AppTheme.sageGreen : Colors.red).withOpacity(0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  _testResult!,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: _testSuccess == true ? AppTheme.sageGreen : Colors.red,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
