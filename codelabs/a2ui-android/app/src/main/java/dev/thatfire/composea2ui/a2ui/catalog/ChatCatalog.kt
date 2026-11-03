package dev.thatfire.composea2ui.a2ui.catalog

import android.content.Context
import androidx.a2ui.compose.ui.A2uiCatalog
import androidx.a2ui.compose.ui.catalog.A2uiBasicCatalogV1
import androidx.compose.foundation.layout.Box
import androidx.compose.material3.a2ui.catalog.A2uiImageRenderer
import androidx.compose.material3.a2ui.catalog.MaterialA2uiBasicCatalogV1Defaults
import androidx.compose.material3.a2ui.catalog.materialA2uiBasicCatalogV1
import androidx.compose.runtime.Composable
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import coil3.compose.AsyncImage
import coil3.compose.LocalPlatformContext
import coil3.network.NetworkHeaders
import coil3.network.httpHeaders
import coil3.request.ImageRequest
import java.io.IOException

// TODO(developer): Step #6 - Define a unique URI ID for the extended catalog

@Suppress("UnusedParameter")
fun createCatalog(context: Context): A2uiCatalog {
    TODO("Complete Step #2 in README.md to create the A2uiCatalog")
}

/**
 * Loads images with Coil, the image loading library that the app already uses.
 * For a Wikipedia article, it loads the article's lead photo.
 */
private object CoilA2uiImageRenderer : A2uiImageRenderer {

    private val requestHeaders =
        NetworkHeaders.Builder()
            .set("User-Agent", WikipediaPhotos.USER_AGENT)
            .build()

    @Composable
    override fun Image(
        url: String,
        contentDescription: String?,
        contentScale: ContentScale,
        modifier: Modifier,
        onError: (throwable: Throwable?) -> Unit,
    ) {
        val photoUrl =
            produceState<String?>(initialValue = null, url) {
                value =
                    try {
                        WikipediaPhotos.find(url)
                    } catch (e: IOException) {
                        onError(e)
                        null
                    }
            }.value

        if (photoUrl == null) {
            // Keeps the image's space while the photo is looked up.
            Box(modifier)
        } else {
            val context = LocalPlatformContext.current
            val imageRequest = remember(context, photoUrl) {
                ImageRequest.Builder(context)
                    .data(photoUrl)
                    .httpHeaders(requestHeaders)
                    .build()
            }
            AsyncImage(
                model = imageRequest,
                contentDescription = contentDescription,
                modifier = modifier,
                contentScale = contentScale,
                onError = { onError(it.result.throwable) },
            )
        }
    }
}
