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
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import coil3.compose.AsyncImage
import java.io.IOException

fun createCatalog(context: Context): A2uiCatalog {
    return materialA2uiBasicCatalogV1(
        image = MaterialA2uiBasicCatalogV1Defaults.image(CoilA2uiImageRenderer),
        video = MaterialA2uiBasicCatalogV1Defaults.video(Media3A2uiVideoRenderer),
        audioPlayer = MaterialA2uiBasicCatalogV1Defaults.audioPlayer(Media3A2uiAudioPlayerRenderer),
        functions = A2uiBasicCatalogV1.Functions(context),
    )
}

/**
 * Loads images with Coil, the image loading library that the app already uses.
 * For a Wikipedia article, it loads the article's lead photo.
 */
private object CoilA2uiImageRenderer : A2uiImageRenderer {
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
            AsyncImage(
                model = photoUrl,
                contentDescription = contentDescription,
                modifier = modifier,
                contentScale = contentScale,
                onError = { onError(it.result.throwable) },
            )
        }
    }
}
