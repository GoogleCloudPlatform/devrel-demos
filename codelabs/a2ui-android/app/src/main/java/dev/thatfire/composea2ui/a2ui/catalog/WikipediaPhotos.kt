package dev.thatfire.composea2ui.a2ui.catalog

import android.net.Uri
import java.io.IOException
import java.net.URL
import java.util.concurrent.ConcurrentHashMap
import javax.net.ssl.HttpsURLConnection
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONException
import org.json.JSONObject

/**
 * Resolves Wikipedia article URLs (such as `https://en.wikipedia.org/wiki/Senso-ji`) to their
 * lead image URL via the Wikimedia REST Summary API, passing non-Wikipedia URLs through unchanged.
 */
internal object WikipediaPhotos {

    private const val WIKI_PATH_PREFIX = "/wiki/"
    private const val USER_AGENT = "ComposeA2UIDemo/1.0 (Android; Jetpack Compose A2UI Codelab)"
    private const val TIMEOUT_MS = 10_000

    private val cache = ConcurrentHashMap<String, String>()

    suspend fun find(url: String): String {
        val parsed = Uri.parse(url)
        val scheme = parsed.scheme?.lowercase()
        val host = parsed.host?.lowercase()
        val encodedPath = parsed.encodedPath

        val isWikipediaArticle =
            scheme == "https" &&
                host != null &&
                (host == "wikipedia.org" || host.endsWith(".wikipedia.org")) &&
                encodedPath != null &&
                encodedPath.startsWith(WIKI_PATH_PREFIX) &&
                encodedPath.length > WIKI_PATH_PREFIX.length

        if (encodedPath == null || !isWikipediaArticle) {
            return url
        }

        cache[url]?.let { return it }

        val slug = encodedPath.removePrefix(WIKI_PATH_PREFIX)
        val summaryEndpoint = "https://$host/api/rest_v1/page/summary/$slug"

        return withContext(Dispatchers.IO) {
            val connection = (URL(summaryEndpoint).openConnection() as HttpsURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = TIMEOUT_MS
                readTimeout = TIMEOUT_MS
                setRequestProperty("Accept", "application/json")
                setRequestProperty("User-Agent", USER_AGENT)
            }
            try {
                val statusCode = connection.responseCode
                if (statusCode !in 200..299) {
                    throw IOException("Wikipedia summary request failed with HTTP $statusCode")
                }
                val body = connection.inputStream.bufferedReader().use { it.readText() }
                val json = try {
                    JSONObject(body)
                } catch (e: JSONException) {
                    throw IOException("Invalid JSON from Wikipedia summary endpoint", e)
                }
                val imageUrl =
                    json.optJSONObject("thumbnail")?.optString("source")?.takeIf { it.isNotBlank() }
                        ?: json.optJSONObject("originalimage")?.optString("source")?.takeIf { it.isNotBlank() }
                        ?: throw IOException("No lead photo available for Wikipedia article: $url")

                cache[url] = imageUrl
                imageUrl
            } finally {
                connection.disconnect()
            }
        }
    }
}
