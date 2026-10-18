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

package com.antigravity.lark_memory

import android.content.Intent
import android.content.pm.PackageManager
import androidx.core.content.FileProvider
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : FlutterActivity() {
    private val channelName = "com.antigravity.lark_memory/media_launcher"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                if (call.method == "openMedia") {
                    val url = call.argument<String>("url")
                    val filename = call.argument<String>("filename") ?: "media_item"
                    val mimeType = call.argument<String>("mimeType") ?: "*/*"
                    val bytes = call.argument<ByteArray>("bytes")

                    Thread {
                        try {
                            val mediaDir = File(cacheDir, "shared_media")
                            if (!mediaDir.exists()) {
                                mediaDir.mkdirs()
                            }
                            val safeName = filename.replace(Regex("[^a-zA-Z0-9._-]"), "_")
                            val targetFile = File(mediaDir, safeName)

                            if (bytes != null && bytes.isNotEmpty()) {
                                FileOutputStream(targetFile).use { out ->
                                    out.write(bytes)
                                }
                            } else if (url != null && (!targetFile.exists() || targetFile.length() == 0L)) {
                                val conn = (URL(url).openConnection() as HttpURLConnection).apply {
                                    connectTimeout = 10000
                                    readTimeout = 20000
                                    requestMethod = "GET"
                                    connect()
                                }
                                if (conn.responseCode in 200..299) {
                                    conn.inputStream.use { input ->
                                        FileOutputStream(targetFile).use { output ->
                                            input.copyTo(output)
                                        }
                                    }
                                } else {
                                    throw IllegalStateException("HTTP ${conn.responseCode} fetching media")
                                }
                            }

                            if (!targetFile.exists() || targetFile.length() == 0L) {
                                throw IllegalStateException("Media file could not be prepared")
                            }

                            val authority = "${applicationContext.packageName}.fileprovider"
                            val contentUri = FileProvider.getUriForFile(this, authority, targetFile)

                            runOnUiThread {
                                try {
                                    val viewIntent = Intent(Intent.ACTION_VIEW).apply {
                                        setDataAndType(contentUri, mimeType)
                                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                    }

                                    val resolved = packageManager.queryIntentActivities(
                                        viewIntent,
                                        PackageManager.MATCH_DEFAULT_ONLY
                                    )
                                    for (info in resolved) {
                                        grantUriPermission(
                                            info.activityInfo.packageName,
                                            contentUri,
                                            Intent.FLAG_GRANT_READ_URI_PERMISSION
                                        )
                                    }

                                    if (mimeType.startsWith("text/")) {
                                        val htmlViewer = resolved.firstOrNull {
                                            it.activityInfo.packageName == "com.android.htmlviewer"
                                        }
                                        if (htmlViewer != null) {
                                            viewIntent.setClassName(
                                                htmlViewer.activityInfo.packageName,
                                                htmlViewer.activityInfo.name
                                            )
                                        }
                                    }

                                    startActivity(viewIntent)
                                    result.success(true)
                                } catch (e: Exception) {
                                    result.error("LAUNCH_ERROR", e.message, null)
                                }
                            }
                        } catch (e: Exception) {
                            runOnUiThread {
                                result.error("PREPARE_ERROR", e.message, null)
                            }
                        }
                    }.start()
                } else {
                    result.notImplemented()
                }
            }
    }
}
