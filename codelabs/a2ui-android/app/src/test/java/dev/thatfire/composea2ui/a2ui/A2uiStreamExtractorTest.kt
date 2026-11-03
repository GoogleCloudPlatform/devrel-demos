package dev.thatfire.composea2ui.a2ui

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class A2uiStreamExtractorTest {

    @Test
    fun `extracts fenced A2UI messages and strips fences from conversational text`() {
        val raw = """
            Here is a weekend itinerary card for Tokyo!

            ```json
            {
              "version": "v0.9",
              "createSurface": {
                "surfaceId": "tokyo-weekend-planner",
                "catalogId": "https://a2ui.org/specification/v0_9/basic_catalog.json",
                "sendDataModel": true
              }
            }
            ```

            ```json
            {
              "version": "v0.9",
              "updateComponents": {
                "surfaceId": "tokyo-weekend-planner",
                "components": [
                  {
                    "id": "root",
                    "component": "Card",
                    "child": "title"
                  },
                  {
                    "id": "title",
                    "component": "Text",
                    "text": "Tokyo Weekend"
                  }
                ]
              }
            }
            ```

            ```json
            {
              "version": "v0.9",
              "updateDataModel": {
                "surfaceId": "tokyo-weekend-planner",
                "path": "/guests",
                "value": 2
              }
            }
            ```
        """.trimIndent()

        val result = A2uiStreamExtractor.extract(rawText = raw, isStreaming = false)

        assertEquals("Here is a weekend itinerary card for Tokyo!", result.displayText)
        assertEquals(3, result.a2uiMessages.size)
        assertEquals("tokyo-weekend-planner", result.a2uiMessages[0].createdSurfaceId)
        assertNull(result.a2uiMessages[1].createdSurfaceId)
        assertNull(result.a2uiMessages[2].createdSurfaceId)
        assertTrue(result.a2uiMessages[0].json.contains("\"createSurface\""))
        assertTrue(result.a2uiMessages[1].json.contains("\"updateComponents\""))
        assertTrue(result.a2uiMessages[2].json.contains("\"updateDataModel\""))
    }

    @Test
    fun `character by character streaming never leaks raw JSON and grows monotonically`() {
        val fullResponse = """
            Sure, here's a dinner reservation form.

            ```json
            {
              "version": "v0.9",
              "createSurface": {
                "surfaceId": "dinner-reservation",
                "catalogId": "https://a2ui.org/specification/v0_9/basic_catalog.json"
              }
            }
            ```

            ```json
            {
              "version": "v0.9",
              "updateDataModel": {
                "surfaceId": "dinner-reservation",
                "path": "/partySize",
                "value": 4
              }
            }
            ```
        """.trimIndent()

        var previousMessages = emptyList<A2uiStreamExtractor.ExtractedA2uiMessage>()

        for (len in 1..fullResponse.length) {
            val prefix = fullResponse.substring(0, len)
            val result = A2uiStreamExtractor.extract(rawText = prefix, isStreaming = true)

            assertFalse(
                "Leaked fence or JSON at length $len: '${result.displayText}'",
                result.displayText.contains("```") || result.displayText.contains("createSurface"),
            )
            assertTrue(
                "Messages must grow monotonically at length $len",
                result.a2uiMessages.size >= previousMessages.size,
            )
            assertEquals(
                "Previously extracted messages must remain identical",
                previousMessages,
                result.a2uiMessages.take(previousMessages.size),
            )
            previousMessages = result.a2uiMessages
        }

        val finalResult = A2uiStreamExtractor.extract(rawText = fullResponse, isStreaming = false)
        assertEquals("Sure, here's a dinner reservation form.", finalResult.displayText)
        assertEquals(2, finalResult.a2uiMessages.size)
        assertEquals("dinner-reservation", finalResult.a2uiMessages[0].createdSurfaceId)
    }

    @Test
    fun `updateDataModel only turn produces empty displayText and no createdSurfaceId`() {
        val raw = """
            ```json
            {
              "version": "v0.9",
              "updateDataModel": {
                "surfaceId": "dinner-reservation",
                "path": "/partySize",
                "value": 6
              }
            }
            ```
        """.trimIndent()

        val result = A2uiStreamExtractor.extract(rawText = raw, isStreaming = false)

        assertEquals("", result.displayText)
        assertEquals(1, result.a2uiMessages.size)
        assertNull(result.a2uiMessages[0].createdSurfaceId)
    }

    @Test
    fun `preserves non-A2UI code blocks and non-A2UI JSON in displayText`() {
        val raw = """
            Here is an example Kotlin snippet and JSON config:

            ```kotlin
            fun greet() = println("Hello")
            ```

            ```json
            {
              "name": "demo",
              "description": "Mentions createSurface in string value only"
            }
            ```
        """.trimIndent()

        val result = A2uiStreamExtractor.extract(rawText = raw, isStreaming = false)

        assertEquals(0, result.a2uiMessages.size)
        assertTrue(result.displayText.contains("```kotlin"))
        assertTrue(result.displayText.contains("\"name\": \"demo\""))
    }

    @Test
    fun `extracts multiple objects in single fence, JSON arrays, and unfenced A2UI JSON`() {
        val multiInOneFence = """
            Booking ready:
            ```json
            [
              {"version":"v0.9","createSurface":{"catalogId":"cat","surfaceId":"s1"}},
              {"version":"v0.9","deleteSurface":{"surfaceId":"s1"}}
            ]
            ```
        """.trimIndent()

        val arrayResult = A2uiStreamExtractor.extract(multiInOneFence, isStreaming = false)
        assertEquals("Booking ready:", arrayResult.displayText)
        assertEquals(2, arrayResult.a2uiMessages.size)
        assertEquals("s1", arrayResult.a2uiMessages[0].createdSurfaceId)

        val unfenced = """
            Updated count!
            {"version":"v0.9","updateDataModel":{"surfaceId":"s1","path":"/count","value":5}}
        """.trimIndent()

        val unfencedResult = A2uiStreamExtractor.extract(unfenced, isStreaming = false)
        assertEquals("Updated count!", unfencedResult.displayText)
        assertEquals(1, unfencedResult.a2uiMessages.size)
    }
}
