package dev.thatfire.composea2ui.a2ui

import androidx.a2ui.model.protocol.A2uiClientDataModel
import androidx.a2ui.model.protocol.A2uiClientErrorMessage
import androidx.a2ui.model.protocol.A2uiClientEventMessage
import java.time.Instant
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class A2uiClientMessageSerializerTest {

    @Test
    fun `serializes A2uiClientEventMessage with context and clientDataModel`() {
        val event = A2uiClientEventMessage(
            type = "confirmReservation",
            surfaceId = "tokyo-dinner-booking",
            componentId = "reserve-btn",
            timestamp = Instant.parse("2026-10-27T02:57:39.077Z").toEpochMilli(),
            context = linkedMapOf(
                "partySize" to 4,
                "time" to listOf("19:30"),
            ),
            clientDataModel = A2uiClientDataModel(
                surfaces = mapOf("tokyo-dinner-booking" to mapOf("partySize" to 4)),
            ),
        )

        val json = A2uiClientMessageSerializer.serialize(event)

        assertTrue(json.contains("\"version\":\"v0.9\""))
        assertTrue(json.contains("\"name\":\"confirmReservation\""))
        assertTrue(json.contains("\"surfaceId\":\"tokyo-dinner-booking\""))
        assertTrue(json.contains("\"sourceComponentId\":\"reserve-btn\""))
        assertTrue(json.contains("\"timestamp\":\"2026-10-27T02:57:39.077Z\""))
        assertTrue(json.contains("\"context\":{\"partySize\":4,\"time\":[\"19:30\"]}"))
        assertTrue(json.contains("\"a2uiClientDataModel\":{\"v0.9\":{\"surfaces\":{\"tokyo-dinner-booking\":{\"partySize\":4}}}}"))

        val prettyJson = A2uiClientMessageSerializer.serialize(event, prettyPrint = true)
        assertTrue(prettyJson.contains("  \"version\": \"v0.9\""))
        assertTrue(prettyJson.contains("    \"name\": \"confirmReservation\""))
    }

    @Test
    fun `serializes VALIDATION_FAILED A2uiClientErrorMessage with path`() {
        val error = A2uiClientErrorMessage(
            code = "VALIDATION_FAILED",
            surfaceId = "tokyo-photos",
            message = "Component type \"UnknownType\" not found\nin catalog",
            context = mapOf("path" to "/components/unsupported-component"),
        )

        val json = A2uiClientMessageSerializer.serialize(error)

        assertEquals(
            "{\"version\":\"v0.9\",\"error\":{\"code\":\"VALIDATION_FAILED\"," +
                "\"surfaceId\":\"tokyo-photos\"," +
                "\"message\":\"Component type \\\"UnknownType\\\" not found\\nin catalog\"," +
                "\"path\":\"/components/unsupported-component\"}}",
            json,
        )
    }
}
