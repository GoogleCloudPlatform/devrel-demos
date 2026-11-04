package dev.thatfire.composea2ui

import androidx.compose.foundation.gestures.scrollBy
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.Badge
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.a2ui.A2uiSurface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import dev.thatfire.composea2ui.ui.theme.ComposeA2UITheme

private val MaxSurfaceHeight = 760.dp

@Composable
fun ChatScreen(
    modifier: Modifier = Modifier,
    viewModel: ChatViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    ChatScreenContent(
        uiState = uiState,
        onSendMessage = viewModel::sendMessage,
        onClearChat = viewModel::clearChat,
        modifier = modifier,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreenContent(
    uiState: ChatUiState,
    onSendMessage: (String) -> Unit,
    modifier: Modifier = Modifier,
    onClearChat: () -> Unit = {},
) {
    var inputText by rememberSaveable { mutableStateOf("") }
    val listState = rememberLazyListState()

    val submitMessage = {
        val trimmed = inputText.trim()
        if (trimmed.isNotEmpty() && !uiState.isGenerating) {
            onSendMessage(trimmed)
            inputText = ""
        }
    }

    LaunchedEffect(uiState.messages.size) {
        if (uiState.messages.isNotEmpty()) {
            listState.animateScrollToItem(uiState.messages.lastIndex)
        }
    }

    val lastMessage = uiState.messages.lastOrNull()
    LaunchedEffect(lastMessage?.text, lastMessage?.surfaceModels?.size, lastMessage?.isStreaming) {
        if (uiState.messages.isNotEmpty()) {
            val layoutInfo = listState.layoutInfo
            val lastVisible = layoutInfo.visibleItemsInfo.lastOrNull()
            if (lastVisible != null && lastVisible.index == uiState.messages.lastIndex) {
                val viewportEnd = layoutInfo.viewportEndOffset - layoutInfo.afterContentPadding
                val itemBottom = lastVisible.offset + lastVisible.size
                if (itemBottom > viewportEnd) {
                    listState.scrollBy((itemBottom - viewportEnd).toFloat())
                }
            }
        }
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        Text(text = stringResource(R.string.app_name))
                    }
                },
                actions = {
                    if (uiState.messages.isNotEmpty()) {
                        TextButton(onClick = onClearChat) {
                            Text(
                                text = stringResource(R.string.clear_chat),
                                color = MaterialTheme.colorScheme.onPrimaryContainer,
                            )
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                    titleContentColor = MaterialTheme.colorScheme.onPrimaryContainer,
                ),
            )
        },
        bottomBar = {
            Surface(tonalElevation = 2.dp) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .imePadding()
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    OutlinedTextField(
                        value = inputText,
                        onValueChange = { updated ->
                            if (updated.length <= MAX_MESSAGE_LENGTH) {
                                inputText = updated
                            }
                        },
                        modifier = Modifier.weight(1f),
                        placeholder = { Text(stringResource(R.string.message_placeholder)) },
                        maxLines = 4,
                        keyboardOptions = KeyboardOptions(
                            capitalization = KeyboardCapitalization.Sentences,
                            imeAction = ImeAction.Send,
                        ),
                        keyboardActions = KeyboardActions(
                            onSend = { submitMessage() },
                        ),
                    )
                    Button(
                        onClick = submitMessage,
                        enabled = inputText.isNotBlank() && !uiState.isGenerating,
                    ) {
                        Text(text = stringResource(R.string.send))
                    }
                }
            }
        },
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
        ) {
            if (uiState.messages.isEmpty()) {
                Text(
                    text = stringResource(R.string.empty_chat_prompt),
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    modifier = Modifier
                        .align(Alignment.Center)
                        .padding(horizontal = 32.dp),
                )
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(
                        items = uiState.messages,
                        key = { it.id },
                    ) { message ->
                        ChatBubble(message = message)
                    }
                }
            }
        }
    }
}

@Composable
fun ChatBubble(
    message: ChatMessage,
    modifier: Modifier = Modifier,
) {
    val isUser = message.participant == Participant.USER
    val isModel = message.participant == Participant.MODEL
    val horizontalAlignment = if (isUser) Alignment.End else Alignment.Start

    val senderLabel = when (message.participant) {
        Participant.USER -> stringResource(R.string.sender_user)
        Participant.MODEL -> stringResource(R.string.sender_model)
        Participant.ERROR -> stringResource(R.string.sender_error)
    }

    val labelColor = when (message.participant) {
        Participant.USER -> MaterialTheme.colorScheme.primary
        Participant.MODEL -> MaterialTheme.colorScheme.tertiary
        Participant.ERROR -> MaterialTheme.colorScheme.error
    }

    val cardColors = when (message.participant) {
        Participant.USER -> CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary,
        )
        Participant.MODEL -> CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.secondaryContainer,
            contentColor = MaterialTheme.colorScheme.onSecondaryContainer,
        )
        Participant.ERROR -> CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer,
            contentColor = MaterialTheme.colorScheme.onErrorContainer,
        )
    }

    BoxWithConstraints(
        modifier = modifier.fillMaxWidth(),
        contentAlignment = if (isUser) Alignment.CenterEnd else Alignment.CenterStart,
    ) {
        val maxBubbleWidth = maxWidth * 0.82f

        if (isModel) {
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.Start,
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text(
                    text = senderLabel,
                    style = MaterialTheme.typography.labelMedium,
                    color = labelColor,
                    modifier = Modifier.padding(horizontal = 4.dp),
                )

                if (message.text.isNotEmpty()) {
                    Card(
                        modifier = Modifier.widthIn(max = maxBubbleWidth),
                        shape = MaterialTheme.shapes.large,
                        colors = cardColors,
                    ) {
                        Box(modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
                            SelectionContainer {
                                Text(
                                    text = message.text,
                                    style = MaterialTheme.typography.bodyLarge,
                                )
                            }
                        }
                    }
                }

                message.surfaceModels.forEach { surfaceModel ->
                    key(surfaceModel.id) {
                        A2uiSurface(
                            surfaceModel = surfaceModel,
                            modifier = Modifier
                                .fillMaxWidth()
                                .heightIn(max = MaxSurfaceHeight),
                        )
                    }
                }

                if (message.isStreaming) {
                    LinearProgressIndicator(
                        modifier = Modifier.fillMaxWidth(),
                        color = MaterialTheme.colorScheme.tertiary,
                        trackColor = MaterialTheme.colorScheme.secondaryContainer,
                    )
                } else if (message.hasA2uiMessages && message.text.isEmpty() && message.surfaceIds.isEmpty()) {
                    Text(
                        text = stringResource(R.string.updated_the_ui_above),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 4.dp),
                    )
                }
            }
        } else {
            Column(
                modifier = Modifier.widthIn(max = maxBubbleWidth),
                horizontalAlignment = horizontalAlignment,
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Text(
                    text = senderLabel,
                    style = MaterialTheme.typography.labelMedium,
                    color = labelColor,
                    modifier = Modifier.padding(horizontal = 4.dp),
                )
                Card(
                    shape = MaterialTheme.shapes.large,
                    colors = cardColors,
                ) {
                    Box(modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
                        SelectionContainer {
                            Text(
                                text = message.text,
                                style = MaterialTheme.typography.bodyLarge,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun ChatScreenPreview() {
    ComposeA2UITheme {
        ChatScreenContent(
            uiState = ChatUiState(
                messages = listOf(
                    ChatMessage(
                        text = "Plan a dinner reservation for 4 guests tonight.",
                        participant = Participant.USER,
                    ),
                    ChatMessage(
                        text = "Here is a reservation card you can customize.",
                        participant = Participant.MODEL,
                    ),
                    ChatMessage(
                        text = "Make it 6 guests.",
                        participant = Participant.USER,
                    ),
                    ChatMessage(
                        text = "",
                        participant = Participant.MODEL,
                        hasA2uiMessages = true,
                    ),
                ),
            ),
            onSendMessage = {},
        )
    }
}
