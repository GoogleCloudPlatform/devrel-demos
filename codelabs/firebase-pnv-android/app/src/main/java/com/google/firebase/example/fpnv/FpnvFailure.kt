package com.google.firebase.example.fpnv

import androidx.credentials.exceptions.GetCredentialCancellationException
import com.google.firebase.pnv.FirebasePhoneNumberVerificationException
import com.google.firebase.pnv.FirebasePnvStatusCodes

/**
 * The ways a call to `getVerifiedPhoneNumber()` can fail that this app treats
 * differently. See https://firebase.google.com/docs/phone-number-verification/android/handle-errors
 */
sealed interface FpnvFailure {
    /** Whether to show a Retry button. The app never retries automatically. */
    val canRetry: Boolean

    /** Message shown on the reservation card and passed to the voice agent. */
    val userMessage: String

    /**
     * CREDENTIAL_MANAGER_ERROR caused by GetCredentialCancellationException: the
     * user most likely dismissed the consent screen. Don't retry automatically,
     * because the user would see the consent screen again.
     */
    data object ConsentDeclined : FpnvFailure {
        override val canRetry = true
        override val userMessage =
            "You didn't share your phone number. Tap Retry to try again. " +
                "(In a production app, offer another way to verify, such as SMS.)"
    }

    /**
     * INVALID_TEST_NUMBER_ID: test mode only. The backend rejected the test
     * token, usually because it expired (test tokens have a 7 day TTL).
     */
    data object TestTokenRejected : FpnvFailure {
        override val canRetry = false
        override val userMessage =
            "Firebase PNV rejected the test token. It might have expired. " +
                "Generate a new test token in the Firebase console, update " +
                "fpnv.testToken in local.properties, and rebuild the app."
    }

    /**
     * ACTIVITY_CONTEXT_REQUIRED: `getVerifiedPhoneNumber()` was called with a
     * Context that isn't an Activity. This is an app bug.
     */
    data object ActivityContextRequired : FpnvFailure {
        override val canRetry = false
        override val userMessage =
            "App error: Firebase PNV needs an Activity to show the consent screen."
    }

    /**
     * Everything else, such as an unsupported carrier or a network error. In a
     * production app, fall back to another verification method, such as SMS.
     *
     * @property errorCode The FirebasePnvStatusCodes or CommonStatusCodes value,
     *   or null if the exception wasn't a FirebasePhoneNumberVerificationException.
     */
    data class Other(val errorCode: Int?) : FpnvFailure {
        override val canRetry = true
        override val userMessage =
            "Couldn't verify your phone number with Firebase PNV" +
                (if (errorCode != null) " (error $errorCode)" else "") +
                ". Tap Retry to try again. (In a production app, offer another " +
                "way to verify, such as SMS.)"
    }
}

/**
 * Classifies a failure from the error code and cause of a
 * [FirebasePhoneNumberVerificationException]. Pass a null [errorCode] for any
 * other exception.
 */
fun classifyFpnvFailure(errorCode: Int?, cause: Throwable?): FpnvFailure =
    when (errorCode) {
        FirebasePnvStatusCodes.CREDENTIAL_MANAGER_ERROR ->
            if (cause is GetCredentialCancellationException) {
                FpnvFailure.ConsentDeclined
            } else {
                FpnvFailure.Other(errorCode)
            }
        FirebasePnvStatusCodes.INVALID_TEST_NUMBER_ID -> FpnvFailure.TestTokenRejected
        FirebasePnvStatusCodes.ACTIVITY_CONTEXT_REQUIRED -> FpnvFailure.ActivityContextRequired
        else -> FpnvFailure.Other(errorCode)
    }

/** Classifies any exception from a failed Firebase PNV `Task`. */
fun Throwable.toFpnvFailure(): FpnvFailure =
    if (this is FirebasePhoneNumberVerificationException) {
        classifyFpnvFailure(errorCode, cause)
    } else {
        classifyFpnvFailure(null, this)
    }
