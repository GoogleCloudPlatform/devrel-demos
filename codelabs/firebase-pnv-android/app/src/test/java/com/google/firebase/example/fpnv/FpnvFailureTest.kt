package com.google.firebase.example.fpnv

import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialUnknownException
import com.google.firebase.pnv.FirebasePnvStatusCodes
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.IOException

class FpnvFailureTest {

    // classifyFpnvFailure() takes the errorCode and cause of a
    // FirebasePhoneNumberVerificationException (or a null errorCode for any other
    // exception). FirebasePhoneNumberVerificationException itself can't be
    // constructed in a local JVM test because its superclass calls Android APIs.
    //
    // The numeric values below are the FirebasePnvStatusCodes constants. They
    // are written out so that this test also documents the codes.

    @Test
    fun credentialManagerErrorCausedByCancellation_isConsentDeclined() {
        val cause = GetCredentialCancellationException("dismissed")
        assertEquals(FpnvFailure.ConsentDeclined, classifyFpnvFailure(55506, cause))
    }

    @Test
    fun credentialManagerErrorWithOtherCause_isOtherFailure() {
        val cause = GetCredentialUnknownException("boom")
        assertEquals(FpnvFailure.Other(55506), classifyFpnvFailure(55506, cause))
    }

    @Test
    fun credentialManagerErrorWithoutCause_isOtherFailure() {
        assertEquals(FpnvFailure.Other(55506), classifyFpnvFailure(55506, null))
    }

    @Test
    fun invalidTestNumberId_isTestTokenRejected() {
        // An expired test token fails getVerifiedPhoneNumber() with 55507.
        assertEquals(FpnvFailure.TestTokenRejected, classifyFpnvFailure(55507, null))
    }

    @Test
    fun activityContextRequired_isActivityContextRequired() {
        assertEquals(
            FpnvFailure.ActivityContextRequired,
            classifyFpnvFailure(55509, null)
        )
    }

    @Test
    fun carrierNotSupported_isOtherFailureWithCode() {
        assertEquals(FpnvFailure.Other(55501), classifyFpnvFailure(55501, null))
    }

    @Test
    fun googlePlayServicesNetworkError_isOtherFailureWithCode() {
        // CommonStatusCodes.NETWORK_ERROR
        assertEquals(FpnvFailure.Other(7), classifyFpnvFailure(7, null))
    }

    @Test
    fun nonFpnvException_isOtherFailureWithoutCode() {
        assertEquals(FpnvFailure.Other(null), classifyFpnvFailure(null, IOException("offline")))
    }

    @Test
    fun documentedCodes_matchSdkConstants() {
        assertEquals(55506, FirebasePnvStatusCodes.CREDENTIAL_MANAGER_ERROR)
        assertEquals(55507, FirebasePnvStatusCodes.INVALID_TEST_NUMBER_ID)
        assertEquals(55509, FirebasePnvStatusCodes.ACTIVITY_CONTEXT_REQUIRED)
    }

    @Test
    fun consentDeclined_offersManualRetry() {
        assertTrue(FpnvFailure.ConsentDeclined.canRetry)
    }

    @Test
    fun otherFailure_offersRetry() {
        assertTrue(FpnvFailure.Other(7).canRetry)
    }

    @Test
    fun testTokenRejected_doesNotOfferRetry() {
        // Retrying can't help until the developer generates a new token and rebuilds.
        assertFalse(FpnvFailure.TestTokenRejected.canRetry)
    }

    @Test
    fun activityContextRequired_doesNotOfferRetry() {
        // This is an app bug, not a runtime condition.
        assertFalse(FpnvFailure.ActivityContextRequired.canRetry)
    }

    @Test
    fun testTokenRejected_messageTellsDeveloperToGenerateNewToken() {
        val message = FpnvFailure.TestTokenRejected.userMessage
        assertTrue(message, message.contains("test token"))
        assertTrue(message, message.contains("local.properties"))
    }

    @Test
    fun otherFailure_messageIncludesErrorCode() {
        val message = FpnvFailure.Other(55501).userMessage
        assertTrue(message, message.contains("55501"))
    }

    @Test
    fun otherFailureWithoutCode_messageHasNoNullCode() {
        val message = FpnvFailure.Other(null).userMessage
        assertFalse(message, message.contains("null"))
    }
}
