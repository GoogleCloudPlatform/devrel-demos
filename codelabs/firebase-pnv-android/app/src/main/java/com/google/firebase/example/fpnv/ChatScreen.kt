package com.google.firebase.example.fpnv

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Face
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Place
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SuggestionChip
import androidx.compose.material3.SuggestionChipDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(viewModel: ChatViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    var showPermissionRationale by remember { mutableStateOf(false) }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) viewModel.startCall(context)
    }

    if (showPermissionRationale) {
        AlertDialog(
            onDismissRequest = { showPermissionRationale = false },
            title = { Text("Microphone Access") },
            text = { Text("TeraBites Concierge needs your microphone to search and book restaurants by voice.") },
            confirmButton = {
                TextButton(onClick = {
                    showPermissionRationale = false
                    permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                }) { Text("Allow") }
            },
            dismissButton = {
                TextButton(onClick = { showPermissionRationale = false }) { Text("Cancel") }
            }
        )
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        stringResource(R.string.app_name).uppercase(),
                        style = MaterialTheme.typography.titleLarge.copy(
                            fontWeight = FontWeight.Black,
                            letterSpacing = 2.sp
                        )
                    )
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                )
            )
        },
        bottomBar = {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp),
                contentAlignment = Alignment.Center
            ) {
                CallControls(
                    isCallActive = uiState.isCallActive,
                    isConnecting = uiState.isConnecting,
                    onStartCall = {
                        val status = ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
                        if (status == PackageManager.PERMISSION_GRANTED) {
                            viewModel.startCall(context)
                        } else {
                            showPermissionRationale = true
                        }
                    },
                    onStopCall = viewModel::stopCall
                )
            }
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .background(
                    Brush.verticalGradient(
                        listOf(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.2f), MaterialTheme.colorScheme.surface)
                    )
                )
        ) {
            LazyColumn(
                modifier = Modifier.weight(1f).fillMaxWidth(),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Active Call Indicator
                if (uiState.isCallActive) {
                    item {
                        ActiveCallStatusCard()
                    }
                }

                // Step 1 & 2: Pending Reservation Dashboard
                if (uiState.pendingReservation != null) {
                    item {
                        SectionHeader("Review & Verify Booking", Icons.Default.Refresh)
                    }
                    item {
                        ReservationCard(
                            reservation = uiState.pendingReservation!!,
                            isPending = true,
                            onRetry = {
                                viewModel.retry()
                            }
                        )
                    }
                }

                // Available Restaurants Dashboard
                if (uiState.availableRestaurants.isNotEmpty()) {
                    item {
                        SectionHeader("Available Restaurants", Icons.Default.Place)
                    }
                    items(uiState.availableRestaurants) { restaurant ->
                        RestaurantCard(restaurant)
                    }
                }

                // Step 3: Finalized Reservations Dashboard
                if (uiState.reservations.isNotEmpty()) {
                    item {
                        SectionHeader("My Reservations", Icons.Default.Menu)
                    }
                    items(uiState.reservations) { reservation ->
                        ReservationCard(
                            reservation = reservation,
                            isPending = false,
                            onRetry = {
                                viewModel.retry()
                            }
                        )
                    }
                }

                // Empty State
                if (uiState.availableRestaurants.isEmpty() && uiState.reservations.isEmpty() && uiState.pendingReservation == null && !uiState.isCallActive) {
                    item {
                        EmptyState()
                    }
                }

                uiState.error?.let { error ->
                    item {
                        ErrorMessage(error)
                    }
                }
            }
        }
    }
}

@Composable
fun SectionHeader(title: String, icon: ImageVector) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(bottom = 4.dp)
    ) {
        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
        Spacer(Modifier.width(8.dp))
        Text(
            text = title.uppercase(),
            style = MaterialTheme.typography.labelLarge.copy(
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp
            ),
            color = MaterialTheme.colorScheme.primary
        )
    }
}

@Composable
fun RestaurantCard(restaurant: Restaurant) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(restaurant.name, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
            Text("${restaurant.cuisine} • ${restaurant.area}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(Modifier.height(8.dp))
            Text(restaurant.description, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
fun ReservationCard(
    reservation: Reservation,
    isPending: Boolean = false,
    onRetry: () -> Unit
) {
    val backgroundColor = if (isPending)
        MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.7f)
    else
        MaterialTheme.colorScheme.surfaceVariant

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = backgroundColor),
        elevation = CardDefaults.cardElevation(defaultElevation = if (isPending) 4.dp else 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(reservation.restaurant, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
                if (isPending) {
                    SuggestionChip(
                        onClick = {},
                        label = { Text("PENDING", style = MaterialTheme.typography.labelSmall) },
                        colors = SuggestionChipDefaults.suggestionChipColors(containerColor = MaterialTheme.colorScheme.primary, labelColor = MaterialTheme.colorScheme.onPrimary)
                    )
                }
            }

            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                IconText(Icons.Default.Person, reservation.name)
                IconText(Icons.Default.Face, "${reservation.partySize} Guests")
            }
            Spacer(Modifier.height(4.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                IconText(Icons.Default.DateRange, reservation.date)
                IconText(Icons.Default.Info, reservation.time)
            }

            if (reservation.phoneNumber != null) {
                Spacer(Modifier.height(12.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.Check, contentDescription = null, tint = Color(0xFF2E7D32), modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("Verified: ${reservation.phoneNumber}", style = MaterialTheme.typography.bodySmall, color = Color(0xFF1B5E20))
                }
            } else if (isPending) {
                Spacer(Modifier.height(12.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.primary)
                    Spacer(Modifier.width(8.dp))
                    Text("Awaiting phone verification...", style = MaterialTheme.typography.bodySmall, fontStyle = androidx.compose.ui.text.font.FontStyle.Italic)
                    TextButton(
                        onClick =  {
                            onRetry()
                        }
                    ) {
                        Text("Retry")
                    }
                }
            }
        }
    }
}

@Composable
fun IconText(icon: ImageVector, text: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, modifier = Modifier.size(14.dp), tint = MaterialTheme.colorScheme.primary)
        Spacer(Modifier.width(4.dp))
        Text(text, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
fun ActiveCallStatusCard() {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primary)
    ) {
        Row(
            modifier = Modifier.padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(Icons.Default.Phone, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimary)
            Spacer(Modifier.width(12.dp))
            Text("Conversation in Progress...", color = MaterialTheme.colorScheme.onPrimary, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
fun EmptyState() {
    Column(
        modifier = Modifier.fillMaxWidth().padding(vertical = 64.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(Icons.Default.Place, contentDescription = null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f))
        Spacer(Modifier.height(16.dp))
        Text("Your personal Vegas concierge is ready.", color = MaterialTheme.colorScheme.outline)
        Text("Start a call to explore and book.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.outline.copy(alpha = 0.7f))
    }
}

@Composable
fun ErrorMessage(error: String) {
    Box(
        modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(MaterialTheme.colorScheme.errorContainer).padding(16.dp)
    ) {
        Text(error, color = MaterialTheme.colorScheme.onErrorContainer, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
fun CallControls(
    isCallActive: Boolean,
    isConnecting: Boolean,
    onStartCall: () -> Unit,
    onStopCall: () -> Unit
) {
    if (!isCallActive) {
        Button(
            onClick = onStartCall,
            enabled = !isConnecting,
            modifier = Modifier.height(56.dp).fillMaxWidth(0.8f),
            shape = RoundedCornerShape(28.dp)
        ) {
            if (isConnecting) {
                CircularProgressIndicator(modifier = Modifier.size(24.dp), color = MaterialTheme.colorScheme.onPrimary, strokeWidth = 2.dp)
            } else {
                Icon(Icons.Default.Phone, contentDescription = null)
                Spacer(Modifier.width(12.dp))
                Text("START CONCIERGE CALL", fontWeight = FontWeight.Bold)
            }
        }
    } else {
        Button(
            onClick = onStopCall,
            modifier = Modifier.height(56.dp).fillMaxWidth(0.8f),
            shape = RoundedCornerShape(28.dp),
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
        ) {
            Icon(Icons.Default.Phone, contentDescription = null)
            Spacer(Modifier.width(12.dp))
            Text("END SESSION", fontWeight = FontWeight.Bold)
        }
    }
}
