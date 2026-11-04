package dev.thatfire.composea2ui.a2ui.catalog

import androidx.annotation.OptIn
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.a2ui.catalog.A2uiAudioPlayerRenderer
import androidx.compose.material3.a2ui.catalog.A2uiVideoRenderer
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.media3.common.MediaItem
import androidx.media3.common.MediaMetadata
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.common.util.UnstableApi
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.compose.material3.MiniController
import androidx.media3.ui.compose.material3.Player as Media3Player

/**
 * Renders A2UI Basic Catalog `Video` components using Media3 ExoPlayer and its Material 3 UI.
 */
internal object Media3A2uiVideoRenderer : A2uiVideoRenderer {
    @OptIn(UnstableApi::class)
    @Composable
    override fun Video(
        url: String,
        modifier: Modifier,
        onError: (throwable: Throwable?) -> Unit,
    ) {
        val context = LocalContext.current
        val currentOnError by rememberUpdatedState(onError)
        val exoPlayer = remember(context) { ExoPlayer.Builder(context).build() }

        DisposableEffect(exoPlayer) {
            val listener = object : Player.Listener {
                override fun onPlayerError(error: PlaybackException) {
                    currentOnError(error)
                }
            }
            exoPlayer.addListener(listener)
            onDispose {
                exoPlayer.removeListener(listener)
                exoPlayer.release()
            }
        }

        LaunchedEffect(exoPlayer, url) {
            exoPlayer.setMediaItem(MediaItem.fromUri(url))
            exoPlayer.prepare()
        }

        Media3Player(
            player = exoPlayer,
            modifier = modifier
                .fillMaxWidth()
                .aspectRatio(16f / 9f),
        )
    }
}

/**
 * Renders A2UI Basic Catalog `AudioPlayer` components using Media3 ExoPlayer and its Material 3
 * `MiniController`.
 */
internal object Media3A2uiAudioPlayerRenderer : A2uiAudioPlayerRenderer {
    @OptIn(UnstableApi::class)
    @Composable
    override fun AudioPlayer(
        url: String,
        contentDescription: String?,
        modifier: Modifier,
        onError: (throwable: Throwable?) -> Unit,
    ) {
        val context = LocalContext.current
        val currentOnError by rememberUpdatedState(onError)
        val exoPlayer = remember(context) { ExoPlayer.Builder(context).build() }

        DisposableEffect(exoPlayer) {
            val listener = object : Player.Listener {
                override fun onPlayerError(error: PlaybackException) {
                    currentOnError(error)
                }
            }
            exoPlayer.addListener(listener)
            onDispose {
                exoPlayer.removeListener(listener)
                exoPlayer.release()
            }
        }

        LaunchedEffect(exoPlayer, url, contentDescription) {
            val title = contentDescription?.takeIf { it.isNotBlank() }
                ?: url.substringAfterLast('/').ifEmpty { "Audio" }
            val mediaItem = MediaItem.Builder()
                .setUri(url)
                .setMediaMetadata(
                    MediaMetadata.Builder()
                        .setTitle(title)
                        .build()
                )
                .build()
            exoPlayer.setMediaItem(mediaItem)
            exoPlayer.prepare()
        }

        MiniController(
            player = exoPlayer,
            modifier = modifier.fillMaxWidth(),
        )
    }
}
