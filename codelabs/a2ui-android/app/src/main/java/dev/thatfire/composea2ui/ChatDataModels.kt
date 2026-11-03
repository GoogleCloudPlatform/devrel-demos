package dev.thatfire.composea2ui

import androidx.a2ui.model.processor.A2uiSurfaceModel
import java.util.UUID

const val MAX_MESSAGE_LENGTH = 8_000

enum class Participant {
    USER,
    MODEL,
    ERROR,
}

data class ChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val text: String,
    val participant: Participant,
    val isStreaming: Boolean = false,
    val surfaceIds: List<String> = emptyList(),
    val surfaceModels: List<A2uiSurfaceModel> = emptyList(),
    val hasA2uiMessages: Boolean = false,
)

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val isGenerating: Boolean = false,
)
