package dev.thatfire.composea2ui

import android.util.Log
import androidx.a2ui.model.processor.A2uiSurfaceModel
import com.google.firebase.ai.type.GenerateContentResponse
import dev.thatfire.composea2ui.a2ui.A2uiStreamExtractor
import java.util.UUID
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Manages the chat message list, streaming text accumulation, and optional A2UI JSON extraction
 * and surface binding so [ChatViewModel] stays focused on Firebase AI Logic and A2UI setup.
 */
class ChatState(
    private val scope: CoroutineScope,
    private val surfaces: StateFlow<List<A2uiSurfaceModel>> = EmptySurfaces,
    private val onA2uiMessage: ((String) -> Unit)? = null,
) {
    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    private val _isGenerating = MutableStateFlow(false)
    private var generationJob: Job? = null

    val uiState: StateFlow<ChatUiState> = combine(
        _messages,
        _isGenerating,
        surfaces,
    ) { messages, isGenerating, activeSurfaces ->
        val surfacesById = activeSurfaces.associateBy { it.id }
        ChatUiState(
            messages = messages.map { message ->
                if (message.surfaceIds.isEmpty()) {
                    message
                } else {
                    message.copy(
                        surfaceModels = message.surfaceIds.mapNotNull { surfacesById[it] },
                    )
                }
            },
            isGenerating = isGenerating,
        )
    }.stateIn(
        scope = scope,
        started = SharingStarted.WhileSubscribed(5_000),
        initialValue = ChatUiState(),
    )

    fun sendMessage(
        rawInput: String,
        streamResponse: (prompt: String) -> Flow<GenerateContentResponse>,
    ) {
        val prompt = rawInput.trim().take(MAX_MESSAGE_LENGTH)
        if (prompt.isEmpty() || _isGenerating.value) return

        val userMessage = ChatMessage(
            text = prompt,
            participant = Participant.USER,
        )
        val modelMessageId = UUID.randomUUID().toString()
        val modelPlaceholder = ChatMessage(
            id = modelMessageId,
            text = "",
            participant = Participant.MODEL,
            isStreaming = true,
        )

        _isGenerating.value = true
        _messages.update { it + userMessage + modelPlaceholder }

        generationJob = scope.launch {
            val responseBuilder = StringBuilder()
            var dispatchedCount = 0
            val createdSurfaceIds = mutableListOf<String>()
            val a2uiHandler = onA2uiMessage

            fun dispatchNewMessages(extracted: List<A2uiStreamExtractor.ExtractedA2uiMessage>) {
                val handler = a2uiHandler ?: return
                while (dispatchedCount < extracted.size) {
                    val item = extracted[dispatchedCount]
                    dispatchedCount++
                    item.createdSurfaceId?.let { surfaceId ->
                        val alreadyActive = surfaces.value.any { it.id == surfaceId }
                        if (!alreadyActive && surfaceId !in createdSurfaceIds) {
                            createdSurfaceIds.add(surfaceId)
                        }
                    }
                    handler(item.json)
                }
            }

            try {
                streamResponse(prompt).collect { chunk ->
                    val chunkText = chunk.text
                    if (!chunkText.isNullOrEmpty()) {
                        responseBuilder.append(chunkText)
                        val fullText = responseBuilder.toString()

                        if (a2uiHandler == null) {
                            _messages.update { currentMessages ->
                                updateMessagesWithReply(
                                    messages = currentMessages,
                                    modelMessageId = modelMessageId,
                                    text = fullText,
                                    isStreaming = true,
                                    turnSurfaceIds = emptyList(),
                                    hasA2uiMessages = false,
                                )
                            }
                        } else {
                            val extraction = A2uiStreamExtractor.extract(
                                rawText = fullText,
                                isStreaming = true,
                            )
                            dispatchNewMessages(extraction.a2uiMessages)
                            _messages.update { currentMessages ->
                                updateMessagesWithReply(
                                    messages = currentMessages,
                                    modelMessageId = modelMessageId,
                                    text = extraction.displayText,
                                    isStreaming = true,
                                    turnSurfaceIds = createdSurfaceIds.toList(),
                                    hasA2uiMessages = dispatchedCount > 0,
                                )
                            }
                        }
                    }
                }

                if (a2uiHandler == null) {
                    val finalText = responseBuilder.toString().ifBlank {
                        "No text response was returned."
                    }
                    _messages.update { currentMessages ->
                        updateMessagesWithReply(
                            messages = currentMessages,
                            modelMessageId = modelMessageId,
                            text = finalText,
                            isStreaming = false,
                            turnSurfaceIds = emptyList(),
                            hasA2uiMessages = false,
                        )
                    }
                } else {
                    val finalExtraction = A2uiStreamExtractor.extract(
                        rawText = responseBuilder.toString(),
                        isStreaming = false,
                    )
                    dispatchNewMessages(finalExtraction.a2uiMessages)
                    val hasA2ui = dispatchedCount > 0
                    val finalText = if (!hasA2ui && finalExtraction.displayText.isBlank()) {
                        "No text response was returned."
                    } else {
                        finalExtraction.displayText
                    }
                    _messages.update { currentMessages ->
                        updateMessagesWithReply(
                            messages = currentMessages,
                            modelMessageId = modelMessageId,
                            text = finalText,
                            isStreaming = false,
                            turnSurfaceIds = createdSurfaceIds.toList(),
                            hasA2uiMessages = hasA2ui,
                        )
                    }
                }
                _isGenerating.value = false
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                Log.w(TAG, "Chat request failed (${e::class.java.simpleName})")
                _messages.update { currentMessages ->
                    if (responseBuilder.isEmpty()) {
                        currentMessages.map { message ->
                            if (message.id == modelMessageId) {
                                message.copy(
                                    text = GENERIC_ERROR_MESSAGE,
                                    participant = Participant.ERROR,
                                    isStreaming = false,
                                )
                            } else {
                                message
                            }
                        }
                    } else {
                        currentMessages.map { message ->
                            if (message.id == modelMessageId) {
                                message.copy(isStreaming = false)
                            } else {
                                message
                            }
                        } + ChatMessage(
                            text = GENERIC_ERROR_MESSAGE,
                            participant = Participant.ERROR,
                        )
                    }
                }
                _isGenerating.value = false
            }
        }
    }

    fun clear() {
        generationJob?.cancel()
        generationJob = null
        _isGenerating.value = false
        _messages.value = emptyList()
    }

    private fun updateMessagesWithReply(
        messages: List<ChatMessage>,
        modelMessageId: String,
        text: String,
        isStreaming: Boolean,
        turnSurfaceIds: List<String>,
        hasA2uiMessages: Boolean,
    ): List<ChatMessage> {
        val claimedIds = turnSurfaceIds.toSet()
        return messages.map { message ->
            when {
                message.id == modelMessageId -> message.copy(
                    text = text,
                    isStreaming = isStreaming,
                    surfaceIds = turnSurfaceIds,
                    hasA2uiMessages = hasA2uiMessages,
                )

                claimedIds.isNotEmpty() && message.surfaceIds.any { it in claimedIds } ->
                    message.copy(surfaceIds = message.surfaceIds - claimedIds)

                else -> message
            }
        }
    }

    private companion object {
        const val TAG = "ChatState"
        const val GENERIC_ERROR_MESSAGE =
            "Couldn't generate a reply. Please verify your network connection, Firebase AI Logic setup, and App Check configuration."
        val EmptySurfaces = MutableStateFlow<List<A2uiSurfaceModel>>(emptyList())
    }
}
