package com.google.firebase.example.fpnv

import org.junit.Assert.assertEquals
import org.junit.Test

class FpnvTestSessionTest {

    @Test
    fun debugBuildWithToken_enablesTestSession() {
        assertEquals(
            TestSessionDecision.ENABLE,
            testSessionDecision(isDebugBuild = true, testToken = "abc123")
        )
    }

    @Test
    fun debugBuildWithEmptyToken_skipsBecauseTokenIsMissing() {
        // enableTestSession("") would throw INVALID_TEST_NUMBER_ID (55507).
        assertEquals(
            TestSessionDecision.SKIP_MISSING_TOKEN,
            testSessionDecision(isDebugBuild = true, testToken = "")
        )
    }

    @Test
    fun debugBuildWithBlankToken_skipsBecauseTokenIsMissing() {
        assertEquals(
            TestSessionDecision.SKIP_MISSING_TOKEN,
            testSessionDecision(isDebugBuild = true, testToken = "   ")
        )
    }

    @Test
    fun releaseBuild_neverEnablesTestSession_evenWithToken() {
        assertEquals(
            TestSessionDecision.SKIP_RELEASE_BUILD,
            testSessionDecision(isDebugBuild = false, testToken = "abc123")
        )
    }

    @Test
    fun releaseBuildWithEmptyToken_skipsAsReleaseBuild() {
        assertEquals(
            TestSessionDecision.SKIP_RELEASE_BUILD,
            testSessionDecision(isDebugBuild = false, testToken = "")
        )
    }
}
