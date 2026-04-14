package com.google.firebase.example.fpnv

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.Text
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation3.runtime.NavEntry
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.ui.NavDisplay
import com.google.firebase.example.fpnv.ui.theme.TeraBitesTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            TeraBitesTheme {
                val backStack = rememberNavBackStack(Chat)
                
                NavDisplay(
                    backStack = backStack,
                    onBack = { if (backStack.isNotEmpty()) backStack.removeAt(backStack.lastIndex) },
                    entryProvider = { key ->
                        when (key) {
                            is Chat -> NavEntry(key) {
                                val viewModel: ChatViewModel = viewModel()
                                ChatScreen(viewModel = viewModel)
                            }
                            else -> NavEntry(key) { Text("Unknown route: $key") }
                        }
                    }
                )
            }
        }
    }
}