package com.google.firebase.example.fpnv

/** Whether the app should enable a Firebase PNV test session at startup. */
enum class TestSessionDecision {
    /** Debug build with a test token: call `enableTestSession()`. */
    ENABLE,

    /** Release builds never use test mode. */
    SKIP_RELEASE_BUILD,

    /**
     * Debug build without a test token. Calling `enableTestSession()` with an
     * empty token would throw `INVALID_TEST_NUMBER_ID`, so skip it and warn.
     */
    SKIP_MISSING_TOKEN,
}

fun testSessionDecision(isDebugBuild: Boolean, testToken: String): TestSessionDecision =
    when {
        !isDebugBuild -> TestSessionDecision.SKIP_RELEASE_BUILD
        testToken.isBlank() -> TestSessionDecision.SKIP_MISSING_TOKEN
        else -> TestSessionDecision.ENABLE
    }
