package com.google.firebase.example.fpnv

import android.Manifest
import android.content.Context
import androidx.annotation.RequiresPermission
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.firebase.Firebase
import com.google.firebase.ai.ai
import com.google.firebase.ai.type.FunctionCallPart
import com.google.firebase.ai.type.FunctionDeclaration
import com.google.firebase.ai.type.FunctionResponsePart
import com.google.firebase.ai.type.GenerativeBackend
import com.google.firebase.ai.type.LiveSession
import com.google.firebase.ai.type.PublicPreviewAPI
import com.google.firebase.ai.type.ResponseModality
import com.google.firebase.ai.type.Schema
import com.google.firebase.ai.type.Tool
import com.google.firebase.ai.type.content
import com.google.firebase.ai.type.liveGenerationConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonPrimitive

data class Restaurant(
    val name: String,
    val cuisine: String,
    val area: String,
    val description: String
)

data class Reservation(
    val restaurant: String,
    val name: String,
    val date: String,
    val time: String,
    val partySize: Int,
    val phoneNumber: String? = null
)

data class ChatUiState(
    val isCallActive: Boolean = false,
    val isConnecting: Boolean = false,
    val availableRestaurants: List<Restaurant> = emptyList(),
    val reservations: List<Reservation> = emptyList(),
    val pendingReservation: Reservation? = null,
    val isVerifying: Boolean = false,
    val error: String? = null
)

@OptIn(PublicPreviewAPI::class)
class ChatViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private var liveSession: LiveSession? = null
    private var connectionJob: kotlinx.coroutines.Job? = null

    private var context: Context? = null

    // Fictitious restaurants in Las Vegas for the demo
    private val restaurants = listOf(
        Restaurant(
            "The Neon Bistro",
            "Modern American",
            "Downtown",
            "Vibrant eatery in the heart of Neon District."
        ),
        Restaurant(
            "Vegas Vault",
            "Steakhouse",
            "The Strip",
            "Indulge in premium cuts at the high-stakes table."
        ),
        Restaurant(
            "Lucky Ladle",
            "Ramen",
            "Arts District",
            "Authentic bowls with a creative twist of downtown flavor."
        ),
        Restaurant(
            "Flamingo Flavors",
            "Seafood",
            "Flamingo Rd",
            "Fresh ocean catch with a classic Vegas flair."
        ),
        Restaurant(
            "Cactus Cantina",
            "Mexican",
            "Summerlin",
            "Lively spot with the best margaritas in the valley."
        )
    )

    // Tool Declarations
    private val findRestaurantsDecl = FunctionDeclaration(
        name = "findRestaurants",
        description = "Search for restaurants in Las Vegas based on cuisine and area.",
        parameters = mapOf(
            "cuisine" to Schema.string("Desired cuisine type"),
            "area" to Schema.string("Preferred area in Las Vegas")
        )
    )

    private val confirmReservationDecl = FunctionDeclaration(
        name = "confirmReservation",
        description = "Step 1: Validate and show the user's booking details (name, restaurant, date, time, party size) on screen.",
        parameters = mapOf(
            "restaurantName" to Schema.string("Name of the restaurant"),
            "date" to Schema.string("Date of reservation in the format YYYY-MM-DD"),
            "time" to Schema.string("Time of reservation in the format HH:ss"),
            "name" to Schema.string("User's name"),
            "partySize" to Schema.string("Number of guests")
        )
    )

    private val verifyPhoneNumberDecl = FunctionDeclaration(
        name = "verifyPhoneNumber",
        description = "Step 2: Trigger the phone verification pop-up on the user's screen. Do not call this function more than once.",
        parameters = mapOf()
    )

    @RequiresPermission(Manifest.permission.RECORD_AUDIO)
    fun startCall(context: Context) {
        if (liveSession != null || _uiState.value.isConnecting) return
        this.context = context

        _uiState.update { it.copy(isConnecting = true, error = null) }
        connectionJob = viewModelScope.launch(Dispatchers.IO) {
            try {
                val model =
                    Firebase.ai(
                        backend = GenerativeBackend.googleAI()
                    ).liveModel(
                        modelName = "gemini-3.1-flash-live-preview",
                        generationConfig = liveGenerationConfig {
                            responseModality = ResponseModality.AUDIO
                        },
                        tools = listOf(
                            Tool.functionDeclarations(
                                listOf(
                                    findRestaurantsDecl,
                                    confirmReservationDecl,
                                    verifyPhoneNumberDecl
                                )
                            )
                        ),
                        systemInstruction = content {
                            text(
                                """
                            You are an elegant Las Vegas Restaurant Concierge.
                            
                            Your available restaurants are:
                            ${restaurants.joinToString("\n") { "- ${it.name} (${it.cuisine}, ${it.area}): ${it.description}" }}
                            
                            FOLLOW THIS STREAMLINED 2-STEP RESERVATION FLOW:
                            
                            Step 1: confirmReservation
                            Once the user provides the restaurant, name, date, time, and party size, call 'confirmReservation'. 
                            This will display their choices on the screen for review.
                            
                            Step 2: verifyPhoneNumber
                            Once step 1 is done, tell the user to check their screen for a phone verification pop-up.
                            Then call 'verifyPhoneNumber'. This is the FINAL step.
                            Once verified, the booking is automatically saved.
                            Do not call this function more than once.
                            
                            Always stay in persona. Greet the user with Vegas flair.
                        """.trimIndent()
                            )
                        }
                    )
                val session = model.connect()
                liveSession = session
                session.startAudioConversation(
                    functionCallHandler = ::functionCallHandler,
//                    enableInterruptions = true
                )
                _uiState.update { it.copy(isConnecting = false, isCallActive = true) }
            } catch (e: Exception) {
                _uiState.update { it.copy(isConnecting = false, error = e.message) }
            }
        }
    }

    fun functionCallHandler(call: FunctionCallPart): FunctionResponsePart {
        return when (call.name) {
            "findRestaurants" -> {
                val cuisine = call.args["cuisine"]?.jsonPrimitive?.content ?: ""
                val area = call.args["area"]?.jsonPrimitive?.content ?: ""
                val filtered = restaurants.filter {
                    it.cuisine.contains(cuisine, ignoreCase = true) && it.area.contains(
                        area,
                        ignoreCase = true
                    )
                }
                _uiState.update { it.copy(availableRestaurants = filtered) }
                FunctionResponsePart(
                    call.name,
                    JsonObject(mapOf("results" to JsonPrimitive(filtered.joinToString("\n") { it.name })))
                )
            }

            "confirmReservation" -> {
                val restaurantName = call.args["restaurantName"]?.jsonPrimitive?.content ?: ""
                val date = call.args["date"]?.jsonPrimitive?.content ?: ""
                val time = call.args["time"]?.jsonPrimitive?.content ?: ""
                val name = call.args["name"]?.jsonPrimitive?.content ?: ""
                val partySize = call.args["partySize"]?.jsonPrimitive?.content?.toIntOrNull() ?: 1

                val pending = Reservation(restaurantName, name, date, time, partySize)
                _uiState.update { it.copy(pendingReservation = pending) }

                FunctionResponsePart(
                    call.name,
                    JsonObject(
                        mapOf(
                            "success" to JsonPrimitive(true),
                            "message" to JsonPrimitive("Details shown on screen. Tell the user to look at their screen to verify the phone number.")
                        )
                    )
                )
            }

            "verifyPhoneNumber" -> {
                runBlocking {
                    try {
                        val verifiedNum = verifyPhoneNumber()
                        FunctionResponsePart(
                            call.name,
                            JsonObject(
                                mapOf(
                                    "success" to JsonPrimitive(true),
                                    "phoneNumber" to JsonPrimitive(verifiedNum),
                                    "message" to JsonPrimitive("Verification successful. Reservation saved.")
                                )
                            )
                        )
                    } catch (e: Exception) {
                        e.printStackTrace()
                        FunctionResponsePart(
                            call.name,
                            JsonObject(
                                mapOf(
                                    "success" to JsonPrimitive(false),
                                    "phoneNumber" to JsonPrimitive("null"),
                                    "message" to JsonPrimitive("Error: ${e.message}")
                                )
                            )
                        )
                    }
                }
            }

            else -> FunctionResponsePart(
                call.name,
                JsonObject(mapOf("error" to JsonPrimitive("Unknown tool")))
            )
        }
    }

    suspend fun verifyPhoneNumber(): String {
        _uiState.update { it.copy(isVerifying = true) }
        // Call FPNV
        val phoneNumber = TODO("Call Firebase PNV to verify the user's phone number")

        _uiState.update { state ->
            val pending = state.pendingReservation
            if (pending != null) {
                state.copy(
                    reservations = state.reservations + pending.copy(phoneNumber = phoneNumber),
                    pendingReservation = null
                )
            } else {
                state // Should not happen in correct flow
            }
        }
        return phoneNumber
    }

    fun stopCall() {
        connectionJob?.cancel()
        viewModelScope.launch {
            try {
                liveSession?.close()
                liveSession = null
                _uiState.update { it.copy(isCallActive = false, isConnecting = false) }
            } catch (e: Exception) {
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        connectionJob?.cancel()
        runBlocking {
            try {
                liveSession?.close()
            } catch (e: Exception) {
            }
        }
        liveSession = null
    }
}
