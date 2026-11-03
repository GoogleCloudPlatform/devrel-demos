package dev.thatfire.composea2ui

import android.util.Log
import androidx.a2ui.model.processor.A2uiSurfaceModel
import androidx.a2ui.model.protocol.A2uiClientErrorMessage
import androidx.a2ui.model.protocol.A2uiClientEventMessage
import androidx.a2ui.model.protocol.A2uiClientToServerMessage
import com.google.firebase.ai.type.GenerateContentResponse
import dev.thatfire.composea2ui.a2ui.A2uiClientMessageSerializer
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
import kotlinx.coroutines.yield

/**
 * Manages the chat message list, streaming text accumulation, outbound client action/error
 * forwarding, and optional A2UI JSON extraction and surface binding so [ChatViewModel] stays
 * focused on Firebase AI Logic and A2UI setup.
 */
class ChatState(
    private val scope: CoroutineScope,
    private val surfaces: StateFlow<List<A2uiSurfaceModel>> = EmptySurfaces,
    private val onA2uiMessage: ((String) -> Unit)? = null,
) {
    private val _messages = MutableStateFlow<List<ChatMessage>>(emptyList())
    private val _isGenerating = MutableStateFlow(false)
    private var generationJob: Job? = null

    private val pendingErrors = mutableListOf<A2uiClientErrorMessage>()
    private var consecutiveErrorRetries = 0

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

        consecutiveErrorRetries = 0
        pendingErrors.clear()

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

        startStreamingTurn(
            initialPayload = prompt,
            modelMessageId = modelMessageId,
            streamResponse = streamResponse,
        )
    }

    /**
     * Sends an outbound A2UI client-to-server message (`action` or `error`) back to the agent.
     *
     * User actions start a new model reply turn, while validation/runtime errors self-correct the
     * active model reply in place (bounded by [MAX_CONSECUTIVE_ERROR_RETRIES] to avoid loops).
     */
    fun sendClientMessage(
        message: A2uiClientToServerMessage,
        streamResponse: (prompt: String) -> Flow<GenerateContentResponse>,
    ) {
        when (message) {
            is A2uiClientEventMessage -> {
                if (_isGenerating.value) return
                consecutiveErrorRetries = 0
                pendingErrors.clear()

                val payload = A2uiClientMessageSerializer.serialize(message, prettyPrint = true)
                val actionMessage = ChatMessage(
                    text = payload,
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
                _messages.update { it + actionMessage + modelPlaceholder }

                startStreamingTurn(
                    initialPayload = payload,
                    modelMessageId = modelMessageId,
                    streamResponse = streamResponse,
                )
            }

            is A2uiClientErrorMessage -> {
                if (_isGenerating.value) {
                    // Queue validation/runtime errors that arrive mid-stream so they are sent
                    // sequentially right after the current stream finishes.
                    if (pendingErrors.size < MAX_BUFFERED_ERRORS_PER_TURN) {
                        pendingErrors.add(message)
                    }
                    return
                }

                if (consecutiveErrorRetries >= MAX_CONSECUTIVE_ERROR_RETRIES) {
                    Log.w(TAG, "Skipping A2UI self-correction after reaching retry limit (${message.code})")
                    return
                }
                consecutiveErrorRetries++

                val payload = A2uiClientMessageSerializer.serialize(message)
                val existingModel = _messages.value.lastOrNull { it.participant == Participant.MODEL }
                val modelMessageId = if (existingModel != null) {
                    _messages.update { currentMessages ->
                        currentMessages.map { item ->
                            if (item.id == existingModel.id) item.copy(isStreaming = true) else item
                        }
                    }
                    existingModel.id
                } else {
                    val newId = UUID.randomUUID().toString()
                    _messages.update {
                        it + ChatMessage(
                            id = newId,
                            text = "",
                            participant = Participant.MODEL,
                            isStreaming = true,
                        )
                    }
                    newId
                }

                _isGenerating.value = true
                startStreamingTurn(
                    initialPayload = payload,
                    modelMessageId = modelMessageId,
                    streamResponse = streamResponse,
                )
            }
        }
    }

    fun clear() {
        generationJob?.cancel()
        generationJob = null
        pendingErrors.clear()
        consecutiveErrorRetries = 0
        _isGenerating.value = false
        _messages.value = emptyList()
    }

    private fun startStreamingTurn(
        initialPayload: String,
        modelMessageId: String,
        streamResponse: (prompt: String) -> Flow<GenerateContentResponse>,
    ) {
        generationJob = scope.launch {
            var nextPayload: String? = initialPayload

            while (nextPayload != null) {
                val payload = nextPayload
                nextPayload = null

                val existingMessage = _messages.value.find { it.id == modelMessageId }
                val baseText = existingMessage?.text.orEmpty()
                val createdSurfaceIds = existingMessage?.surfaceIds?.toMutableList() ?: mutableListOf()
                val priorHasA2ui = existingMessage?.hasA2uiMessages ?: false

                val responseBuilder = StringBuilder()
                var dispatchedCount = 0
                val a2uiHandler = onA2uiMessage

                fun combineDisplayText(turnText: String): String {
                    return when {
                        baseText.isEmpty() -> turnText
                        turnText.isEmpty() -> baseText
                        else -> "$baseText\n\n$turnText"
                    }
                }

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
                    streamResponse(payload).collect { chunk ->
                        val chunkText = chunk.text
                        if (!chunkText.isNullOrEmpty()) {
                            responseBuilder.append(chunkText)
                            val fullText = responseBuilder.toString()

                            if (a2uiHandler == null) {
                                _messages.update { currentMessages ->
                                    updateMessagesWithReply(
                                        messages = currentMessages,
                                        modelMessageId = modelMessageId,
                                        text = combineDisplayText(fullText),
                                        isStreaming = true,
                                        turnSurfaceIds = createdSurfaceIds.toList(),
                                        hasA2uiMessages = priorHasA2ui,
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
                                        text = combineDisplayText(extraction.displayText),
                                        isStreaming = true,
                                        turnSurfaceIds = createdSurfaceIds.toList(),
                                        hasA2uiMessages = priorHasA2ui || dispatchedCount > 0,
                                    )
                                }
                            }
                        }
                    }

                    // Allow background A2uiMessageProcessor validation to enqueue any errors
                    yield()

                    val willRetryQueuedErrors =
                        pendingErrors.isNotEmpty() &&
                            consecutiveErrorRetries < MAX_CONSECUTIVE_ERROR_RETRIES

                    if (a2uiHandler == null) {
                        val combined = combineDisplayText(responseBuilder.toString())
                        val finalText = combined.ifBlank { "No text response was returned." }
                        _messages.update { currentMessages ->
                            updateMessagesWithReply(
                                messages = currentMessages,
                                modelMessageId = modelMessageId,
                                text = finalText,
                                isStreaming = willRetryQueuedErrors,
                                turnSurfaceIds = createdSurfaceIds.toList(),
                                hasA2uiMessages = priorHasA2ui,
                            )
                        }
                    } else {
                        val finalExtraction = A2uiStreamExtractor.extract(
                            rawText = responseBuilder.toString(),
                            isStreaming = false,
                        )
                        dispatchNewMessages(finalExtraction.a2uiMessages)
                        yield()

                        val hasQueuedErrorsAfterFinal =
                            pendingErrors.isNotEmpty() &&
                                consecutiveErrorRetries < MAX_CONSECUTIVE_ERROR_RETRIES

                        val hasA2ui = priorHasA2ui || dispatchedCount > 0
                        val combined = combineDisplayText(finalExtraction.displayText)
                        val finalText = if (!hasA2ui && combined.isBlank()) {
                            "No text response was returned."
                        } else {
                            combined
                        }
                        _messages.update { currentMessages ->
                            updateMessagesWithReply(
                                messages = currentMessages,
                                modelMessageId = modelMessageId,
                                text = finalText,
                                isStreaming = hasQueuedErrorsAfterFinal,
                                turnSurfaceIds = createdSurfaceIds.toList(),
                                hasA2uiMessages = hasA2ui,
                            )
                        }
                    }

                    if (pendingErrors.isNotEmpty()) {
                        if (consecutiveErrorRetries < MAX_CONSECUTIVE_ERROR_RETRIES) {
                            consecutiveErrorRetries++
                            val queued = pendingErrors.toList()
                            pendingErrors.clear()
                            nextPayload = queued.joinToString("\n\n") {
                                A2uiClientMessageSerializer.serialize(it)
                            }
                        } else {
                            Log.w(TAG, "Dropping ${pendingErrors.size} A2UI error(s); retry limit reached")
                            pendingErrors.clear()
                        }
                    }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    Log.w(TAG, "Chat request failed (${e::class.java.simpleName})")
                    pendingErrors.clear()
                    _messages.update { currentMessages ->
                        if (responseBuilder.isEmpty() && baseText.isEmpty() && !priorHasA2ui) {
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
                    break
                }
            }

            _isGenerating.value = false
        }
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
        const val MAX_CONSECUTIVE_ERROR_RETRIES = 2
        const val MAX_BUFFERED_ERRORS_PER_TURN = 5
        const val GENERIC_ERROR_MESSAGE =
            "Couldn't generate a reply. Please verify your network connection, Firebase AI Logic setup, and App Check configuration."
        val EmptySurfaces = MutableStateFlow<List<A2uiSurfaceModel>>(emptyList())
    }
}
