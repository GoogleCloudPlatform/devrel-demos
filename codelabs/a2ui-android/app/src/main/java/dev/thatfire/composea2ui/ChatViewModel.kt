package dev.thatfire.composea2ui

import android.app.Application
import androidx.a2ui.compose.runtime.A2uiMessageParser
import androidx.a2ui.compose.ui.A2uiMessageProcessor
import androidx.a2ui.model.processor.processInput
import androidx.a2ui.model.protocol.A2uiClientToServerMessage
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.google.firebase.Firebase
import com.google.firebase.ai.Chat
import com.google.firebase.ai.ai
import com.google.firebase.ai.type.GenerativeBackend
import com.google.firebase.ai.type.content
import dev.thatfire.composea2ui.a2ui.buildSystemInstruction
import dev.thatfire.composea2ui.a2ui.catalog.createCatalog
import dev.thatfire.composea2ui.a2ui.clearSurfaces
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class ChatViewModel(application: Application) : AndroidViewModel(application) {

    // TODO(developer): Step #3 - Instantiate catalog, processor, and parser

    private val generativeModel = Firebase.ai(backend = GenerativeBackend.googleAI())
        .generativeModel(
            modelName = "gemini-3.5-flash-lite",
            // TODO(developer): Step #2 - Add A2UI system instructions
        )

    private var chat: Chat = generativeModel.startChat()

    private val chatState = ChatState(
        scope = viewModelScope,
        // TODO(developer): Step #3 - Listen to activeSurfaces and process A2UI JSON messages
    )
    val uiState: StateFlow<ChatUiState> = chatState.uiState

    init {
        // TODO(developer): Step #3 - Process incoming A2UI messages off the main thread

        // TODO(developer): Step #4 - Forward user actions and validation errors back to the agent
    }

    fun sendMessage(prompt: String) {
        chatState.sendMessage(prompt) { chat.sendMessageStream(it) }
    }

    @Suppress("UnusedPrivateMember")
    private fun sendClientMessage(message: A2uiClientToServerMessage) {
        chatState.sendClientMessage(message) { chat.sendMessageStream(it) }
    }

    fun clearChat() {
        chatState.clear()
        // TODO(developer): Step #3 - Clear active A2UI surfaces
        chat = generativeModel.startChat()
    }
}
