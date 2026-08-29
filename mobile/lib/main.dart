import 'dart:async';
import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

void main() => runApp(const SciTranslatorApp());

class SciTranslatorApp extends StatelessWidget {
  const SciTranslatorApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        debugShowCheckedModeBanner: false,
        title: 'Scientific Translator',
        theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
        home: const HomePage(),
      );
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  // Android emulator: 10.0.2.2. Use HTTPS for real Android/iOS devices in production.
  final apiController = TextEditingController(text: 'http://10.0.2.2:8000');
  final glossaryController = TextEditingController();
  PlatformFile? selected;
  String source = 'auto';
  String target = 'vi';
  String status = 'Chưa có tác vụ';
  double progress = 0;
  Map<String, dynamic> outputs = {};
  String? currentJobId;
  Timer? timer;
  bool submitting = false;

  static const sourceLanguages = <String, String>{
    'auto': 'Tự động',
    'en': 'English',
    'vi': 'Tiếng Việt',
    'zh': '中文',
    'ja': '日本語',
    'ko': '한국어',
    'de': 'Deutsch',
    'fr': 'Français',
    'es': 'Español',
    'ru': 'Русский',
  };

  static const targetLanguages = <String, String>{
    'vi': 'Tiếng Việt',
    'en': 'English',
    'zh': '中文',
    'ja': '日本語',
    'ko': '한국어',
    'de': 'Deutsch',
    'fr': 'Français',
    'es': 'Español',
    'ru': 'Русский',
  };

  String get baseUrl => apiController.text.trim().replaceAll(RegExp(r'/+$'), '');

  Future<void> pick() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      withData: true,
      allowedExtensions: ['pdf', 'docx', 'txt', 'md', 'png', 'jpg', 'jpeg', 'pptx', 'xlsx'],
    );
    if (result != null && mounted) {
      setState(() => selected = result.files.single);
    }
  }

  Future<http.MultipartFile> _multipartFor(PlatformFile file) async {
    if (file.path != null) {
      return http.MultipartFile.fromPath('file', file.path!, filename: file.name);
    }
    if (file.bytes != null) {
      return http.MultipartFile.fromBytes('file', file.bytes!, filename: file.name);
    }
    throw StateError('Không đọc được dữ liệu tệp đã chọn.');
  }

  Future<void> submit() async {
    if (selected == null || submitting) return;
    if (baseUrl.isEmpty) {
      setState(() => status = 'Hãy nhập địa chỉ API server.');
      return;
    }

    setState(() {
      submitting = true;
      status = 'Đang tải lên...';
      progress = .02;
      outputs = {};
    });

    try {
      final req = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/v1/jobs'))
        ..fields['source_language'] = source
        ..fields['target_language'] = target
        ..fields['output_format'] = 'html'
        ..fields['glossary_json'] = glossaryController.text.trim()
        ..files.add(await _multipartFor(selected!));

      final res = await req.send();
      final body = await res.stream.bytesToString();
      if (res.statusCode >= 300) {
        if (mounted) setState(() => status = body);
        return;
      }

      final job = jsonDecode(body) as Map<String, dynamic>;
      currentJobId = job['id'] as String;
      poll(currentJobId!);
    } catch (e) {
      if (mounted) setState(() => status = 'Lỗi: $e');
    } finally {
      if (mounted) setState(() => submitting = false);
    }
  }

  void poll(String id) {
    timer?.cancel();
    timer = Timer.periodic(const Duration(seconds: 2), (t) async {
      try {
        final res = await http.get(Uri.parse('$baseUrl/api/v1/jobs/$id'));
        if (res.statusCode != 200) return;
        final job = jsonDecode(res.body) as Map<String, dynamic>;
        if (!mounted) return;
        setState(() {
          status = '${job['message'] ?? job['status']}${job['error'] != null ? ' — ${job['error']}' : ''}';
          progress = ((job['progress'] ?? 0) as num).toDouble() / 100;
          outputs = Map<String, dynamic>.from(job['outputs'] ?? {});
        });
        if (job['status'] == 'completed' || job['status'] == 'failed') t.cancel();
      } catch (_) {
        // Keep polling; transient mobile network failures are common.
      }
    });
  }

  Future<void> openOutput(String fmt) async {
    final output = outputs[fmt];
    if (output == null) return;
    final raw = output.toString();
    final uri = raw.startsWith('http://') || raw.startsWith('https://')
        ? Uri.parse(raw)
        : Uri.parse('$baseUrl$raw');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  void dispose() {
    timer?.cancel();
    apiController.dispose();
    glossaryController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Scientific Translator')),
        body: ListView(
          padding: const EdgeInsets.all(18),
          children: [
            TextField(
              controller: apiController,
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(labelText: 'API server', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: submitting ? null : pick,
              icon: const Icon(Icons.upload_file),
              label: Text(selected?.name ?? 'Chọn tài liệu'),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: source,
                    decoration: const InputDecoration(labelText: 'Nguồn'),
                    items: sourceLanguages.entries
                        .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                        .toList(),
                    onChanged: (v) => setState(() => source = v!),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: target,
                    decoration: const InputDecoration(labelText: 'Đích'),
                    items: targetLanguages.entries
                        .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                        .toList(),
                    onChanged: (v) => setState(() => target = v!),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            TextField(
              controller: glossaryController,
              minLines: 2,
              maxLines: 5,
              decoration: const InputDecoration(
                labelText: 'Glossary JSON (tùy chọn)',
                hintText: '{"wave function":"hàm sóng"}',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: selected == null || submitting ? null : submit,
              child: Text(submitting ? 'ĐANG TẢI...' : 'DỊCH TÀI LIỆU'),
            ),
            const SizedBox(height: 18),
            LinearProgressIndicator(value: progress),
            const SizedBox(height: 8),
            Text(status),
            if (outputs.isNotEmpty) ...[
              const Padding(
                padding: EdgeInsets.only(top: 16, bottom: 8),
                child: Text('Kết quả', style: TextStyle(fontWeight: FontWeight.w700)),
              ),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: outputs.keys
                    .map((fmt) => OutlinedButton(
                          onPressed: () => openOutput(fmt),
                          child: Text(fmt.replaceAll('_', ' ').toUpperCase()),
                        ))
                    .toList(),
              ),
            ],
          ],
        ),
      );
}
