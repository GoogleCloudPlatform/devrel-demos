package com.google.firebase.example.fpnv

import android.app.Application
import android.util.Log
import com.google.firebase.pnv.FirebasePhoneNumberVerification

class TeraBitesApplication : Application() {
    override fun onCreate() {
        super.onCreate()

        // Enable a Firebase PNV test session once per app process. A second call
        // to enableTestSession() throws TEST_SESSION_ALREADY_ENABLED, so don't
        // call it from an Activity, which can be recreated (for example, when the
        // screen rotates).
        when (testSessionDecision(BuildConfig.DEBUG, BuildConfig.FPNV_TEST_TOKEN)) {
            TestSessionDecision.ENABLE ->
                FirebasePhoneNumberVerification.getInstance()
                    .enableTestSession(BuildConfig.FPNV_TEST_TOKEN)
            TestSessionDecision.SKIP_MISSING_TOKEN ->
                Log.w(
                    TAG,
                    "No Firebase PNV test token; test mode is off. Add " +
                        "fpnv.testToken to local.properties and rebuild."
                )
            TestSessionDecision.SKIP_RELEASE_BUILD -> Unit
        }
    }

    private companion object {
        const val TAG = "TeraBitesApplication"
    }
}
