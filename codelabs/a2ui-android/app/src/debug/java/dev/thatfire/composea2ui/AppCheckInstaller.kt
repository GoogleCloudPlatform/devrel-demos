package dev.thatfire.composea2ui

import com.google.firebase.Firebase
import com.google.firebase.appcheck.appCheck
import com.google.firebase.appcheck.debug.DebugAppCheckProviderFactory

internal fun installAppCheckProvider() {
    Firebase.appCheck.installAppCheckProviderFactory(
        DebugAppCheckProviderFactory.getInstance()
    )
}
