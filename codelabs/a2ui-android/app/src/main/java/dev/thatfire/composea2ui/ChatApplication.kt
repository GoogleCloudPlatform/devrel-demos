package dev.thatfire.composea2ui

import android.app.Application
import com.google.firebase.Firebase
import com.google.firebase.initialize

class ChatApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        Firebase.initialize(context = this)
        installAppCheckProvider()
    }
}
