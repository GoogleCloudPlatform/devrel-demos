package dev.thatfire.composea2ui

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.google.firebase.Firebase
import com.google.firebase.ai.Chat
import com.google.firebase.ai.ai
import com.google.firebase.ai.type.GenerativeBackend
import com.google.firebase.ai.type.content
import dev.thatfire.composea2ui.a2ui.buildSystemInstruction
import dev.thatfire.composea2ui.a2ui.catalog.createCatalog
import java.util.UUID
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class Participant {
    USER,
    MODEL,
    ERROR
}

data class ChatMessage(
    val id: String = UUID.randomUUID().toString(),
    val text: String,
    val participant: Participant,
    val isStreaming: Boolean = false
)

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val isGenerating: Boolean = false
)

class ChatViewModel(application: Application) : AndroidViewModel(application) {

    private val catalog = createCatalog(application)

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private val chat: Chat by lazy {
        val systemPrompt = buildSystemInstruction(
            resources = getApplication<Application>().resources,
            catalog = catalog,
        )
        Firebase.ai(backend = GenerativeBackend.googleAI())
            .generativeModel(
                modelName = MODEL_NAME,
                systemInstruction = content { text(systemPrompt) },
            )
            .startChat()
    }

    fun sendMessage(rawInput: String) {
        val prompt = rawInput.trim().take(MAX_MESSAGE_LENGTH)
        if (prompt.isEmpty() || _uiState.value.isGenerating) return

        val userMessage = ChatMessage(
            text = prompt,
            participant = Participant.USER
        )
        val modelMessageId = UUID.randomUUID().toString()
        val modelPlaceholder = ChatMessage(
            id = modelMessageId,
            text = "",
            participant = Participant.MODEL,
            isStreaming = true
        )

        _uiState.update { state ->
            state.copy(
                messages = state.messages + userMessage + modelPlaceholder,
                isGenerating = true
            )
        }

        viewModelScope.launch {
            val responseBuilder = StringBuilder()
            try {
                chat.sendMessageStream(prompt).collect { chunk ->
                    val chunkText = chunk.text
                    if (!chunkText.isNullOrEmpty()) {
                        responseBuilder.append(chunkText)
                        val currentText = responseBuilder.toString()
                        _uiState.update { state ->
                            state.copy(
                                messages = state.messages.map { message ->
                                    if (message.id == modelMessageId) {
                                        message.copy(text = currentText)
                                    } else {
                                        message
                                    }
                                }
                            )
                        }
                    }
                }

                _uiState.update { state ->
                    state.copy(
                        isGenerating = false,
                        messages = state.messages.map { message ->
                            if (message.id == modelMessageId) {
                                val finalText = message.text.ifBlank {
                                    "No text response was returned."
                                }
                                message.copy(text = finalText, isStreaming = false)
                            } else {
                                message
                            }
                        }
                    )
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                Log.w(TAG, "Chat request failed (${e::class.java.simpleName})")
                _uiState.update { state ->
                    val updatedMessages = if (responseBuilder.isEmpty()) {
                        state.messages.map { message ->
                            if (message.id == modelMessageId) {
                                message.copy(
                                    text = GENERIC_ERROR_MESSAGE,
                                    participant = Participant.ERROR,
                                    isStreaming = false
                                )
                            } else {
                                message
                            }
                        }
                    } else {
                        state.messages.map { message ->
                            if (message.id == modelMessageId) {
                                message.copy(isStreaming = false)
                            } else {
                                message
                            }
                        } + ChatMessage(
                            text = GENERIC_ERROR_MESSAGE,
                            participant = Participant.ERROR
                        )
                    }
                    state.copy(
                        isGenerating = false,
                        messages = updatedMessages
                    )
                }
            }
        }
    }

    companion object {
        private const val TAG = "ChatViewModel"
        private const val MODEL_NAME = "gemini-3.8-flash"
        const val MAX_MESSAGE_LENGTH = 8_000
        private const val GENERIC_ERROR_MESSAGE =
            "Couldn't generate a reply. Please verify your network connection, Firebase AI Logic setup, and App Check configuration."
    }
}
