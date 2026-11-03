package dev.thatfire.composea2ui.a2ui

/**
 * Incrementally separates conversational Markdown/plain text from A2UI v0.9 JSON protocol
 * messages (`createSurface`, `updateComponents`, `updateDataModel`, `deleteSurface`) as chunks
 * stream in from the generative model.
 */
internal object A2uiStreamExtractor {

    private val A2UI_MESSAGE_KEYS = setOf(
        "createSurface",
        "updateComponents",
        "updateDataModel",
        "deleteSurface",
    )

    private val JSON_FENCE_LANGUAGES = setOf("", "json", "a2ui", "jsonl")

    internal data class ExtractedA2uiMessage(
        val json: String,
        val createdSurfaceId: String? = null,
    )

    internal data class ExtractionResult(
        val displayText: String,
        val a2uiMessages: List<ExtractedA2uiMessage>,
    )

    fun extract(rawText: String, isStreaming: Boolean): ExtractionResult {
        if (rawText.isEmpty()) {
            return ExtractionResult(displayText = "", a2uiMessages = emptyList())
        }

        val textBuilder = StringBuilder()
        val messages = mutableListOf<ExtractedA2uiMessage>()
        var cursor = 0

        while (cursor < rawText.length) {
            // 1. Check for Markdown code fence (``` or longer)
            if (isFenceStartAt(rawText, cursor)) {
                val tickCount = countBackticks(rawText, cursor)
                val headerStart = cursor + tickCount
                val headerNewline = rawText.indexOf('\n', headerStart)

                if (headerNewline == -1) {
                    // Opening fence header line is still incomplete
                    val partialLang = rawText.substring(headerStart).trim().lowercase()
                    val mightBeJsonFence = JSON_FENCE_LANGUAGES.any { it.startsWith(partialLang) }
                    if (isStreaming && mightBeJsonFence) {
                        // Hide incomplete opening ```json fence while streaming
                        break
                    } else {
                        textBuilder.append(rawText, cursor, rawText.length)
                        break
                    }
                }

                val lang = rawText.substring(headerStart, headerNewline).trim().lowercase()
                val bodyStart = headerNewline + 1
                val closingFence = findClosingFence(rawText, bodyStart, tickCount)

                if (closingFence == null) {
                    // Unclosed Markdown fence at the end of rawText
                    val partialBody = rawText.substring(bodyStart)
                    if (lang in JSON_FENCE_LANGUAGES) {
                        val extracted = extractA2uiMessagesFromBlock(
                            block = partialBody,
                            includeBrokenA2uiFallback = !isStreaming,
                        )
                        if (extracted.isNotEmpty()) {
                            messages.addAll(extracted)
                            break
                        }
                        if (isStreaming) {
                            // Hide in-progress JSON fence while streaming
                            break
                        }
                    }
                    // Stream ended and fence had no A2UI messages: preserve raw text
                    textBuilder.append(rawText, cursor, rawText.length)
                    break
                } else {
                    val fenceBody = rawText.substring(bodyStart, closingFence.bodyEnd)
                    if (lang in JSON_FENCE_LANGUAGES) {
                        val extracted = extractA2uiMessagesFromBlock(
                            block = fenceBody,
                            includeBrokenA2uiFallback = true,
                        )
                        if (extracted.isNotEmpty()) {
                            messages.addAll(extracted)
                            cursor = closingFence.afterFenceIndex
                            continue
                        }
                    }
                    // Regular non-A2UI code block: keep in conversational text
                    textBuilder.append(rawText, cursor, closingFence.afterFenceIndex)
                    cursor = closingFence.afterFenceIndex
                    continue
                }
            }

            // 2. Check for trailing 1-2 backticks right at EOF while streaming
            if (isStreaming && rawText[cursor] == '`') {
                val ticks = countBackticks(rawText, cursor)
                if (ticks < 3 && cursor + ticks == rawText.length && isAtLineStart(rawText, cursor)) {
                    break
                }
            }

            // 3. Check for unfenced top-level A2UI JSON object starting at '{'
            if (rawText[cursor] == '{' && isStandaloneJsonStart(rawText, cursor)) {
                val objEnd = skipJsonValue(rawText, cursor)
                if (objEnd != -1) {
                    val candidate = rawText.substring(cursor, objEnd)
                    val metadata = parseA2uiObjectMetadata(candidate)
                    if (metadata.isA2ui) {
                        messages.add(
                            ExtractedA2uiMessage(
                                json = candidate,
                                createdSurfaceId = metadata.createdSurfaceId,
                            )
                        )
                        cursor = objEnd
                        continue
                    }
                } else if (isStreaming && looksLikeStreamingA2uiObject(rawText, cursor)) {
                    // Hide incomplete unfenced A2UI JSON object while streaming
                    break
                }
            }

            textBuilder.append(rawText[cursor])
            cursor++
        }

        val normalizedText = normalizeDisplayText(textBuilder.toString())
        return ExtractionResult(
            displayText = normalizedText,
            a2uiMessages = messages,
        )
    }

    private fun extractA2uiMessagesFromBlock(
        block: String,
        includeBrokenA2uiFallback: Boolean,
    ): List<ExtractedA2uiMessage> {
        val extracted = mutableListOf<ExtractedA2uiMessage>()
        val trimmedStart = skipWhitespace(block, 0)
        if (trimmedStart >= block.length) return emptyList()

        // If the model wrapped messages in a JSON array `[ {...}, {...} ]`, step inside `[`
        var index = if (block[trimmedStart] == '[') trimmedStart + 1 else trimmedStart

        while (index < block.length) {
            index = skipWhitespaceAndDelimiters(block, index)
            if (index >= block.length || block[index] == ']') break
            if (block[index] != '{') {
                // Advance to next '{' if any prose/comments slipped into fence
                val nextBrace = block.indexOf('{', index)
                if (nextBrace == -1) break
                index = nextBrace
            }

            val objEnd = skipJsonValue(block, index)
            if (objEnd == -1) {
                // Incomplete trailing object inside block
                if (includeBrokenA2uiFallback && extracted.isEmpty()) {
                    val remainder = block.substring(index).trim()
                    if (containsA2uiKeyword(remainder)) {
                        extracted.add(ExtractedA2uiMessage(json = remainder))
                    }
                }
                break
            }

            val candidate = block.substring(index, objEnd)
            val metadata = parseA2uiObjectMetadata(candidate)
            if (metadata.isA2ui) {
                extracted.add(
                    ExtractedA2uiMessage(
                        json = candidate,
                        createdSurfaceId = metadata.createdSurfaceId,
                    )
                )
            } else if (includeBrokenA2uiFallback && containsA2uiKeyword(candidate)) {
                // Malformed A2UI payload: still forward to processor so validation error is handled
                extracted.add(ExtractedA2uiMessage(json = candidate))
            }
            index = objEnd
        }

        return extracted
    }

    private data class ClosingFenceMatch(
        val bodyEnd: Int,
        val afterFenceIndex: Int,
    )

    /**
     * Finds a CommonMark closing fence (` ``` `) at the start of a line (allowing up to 3 leading
     * spaces/tabs) followed only by optional spaces/tabs and newline or EOF.
     */
    private fun findClosingFence(
        text: String,
        searchStart: Int,
        minTicks: Int,
    ): ClosingFenceMatch? {
        var lineStart = searchStart
        while (lineStart < text.length) {
            var pos = lineStart
            var indent = 0
            while (pos < text.length && (text[pos] == ' ' || text[pos] == '\t') && indent < 4) {
                pos++
                indent++
            }
            if (indent < 4 && pos < text.length && text[pos] == '`') {
                val ticks = countBackticks(text, pos)
                if (ticks >= minTicks) {
                    var afterTicks = pos + ticks
                    while (afterTicks < text.length && (text[afterTicks] == ' ' || text[afterTicks] == '\t')) {
                        afterTicks++
                    }
                    if (afterTicks < text.length && text[afterTicks] == '\r') {
                        afterTicks++
                    }
                    if (afterTicks == text.length || text[afterTicks] == '\n') {
                        val afterFence = if (afterTicks < text.length) afterTicks + 1 else afterTicks
                        val bodyEnd = if (lineStart > searchStart && text[lineStart - 1] == '\n') {
                            if (lineStart - 2 >= searchStart && text[lineStart - 2] == '\r') {
                                lineStart - 2
                            } else {
                                lineStart - 1
                            }
                        } else {
                            lineStart
                        }
                        return ClosingFenceMatch(bodyEnd = bodyEnd, afterFenceIndex = afterFence)
                    }
                }
            }
            val nextNewline = text.indexOf('\n', lineStart)
            if (nextNewline == -1) return null
            lineStart = nextNewline + 1
        }
        return null
    }

    private fun isFenceStartAt(text: String, index: Int): Boolean {
        return index + 2 < text.length &&
            text[index] == '`' &&
            text[index + 1] == '`' &&
            text[index + 2] == '`' &&
            isAtLineStart(text, index)
    }

    private fun isAtLineStart(text: String, index: Int): Boolean {
        var pos = index - 1
        while (pos >= 0 && (text[pos] == ' ' || text[pos] == '\t')) {
            pos--
        }
        return pos < 0 || text[pos] == '\n'
    }

    private fun isStandaloneJsonStart(text: String, index: Int): Boolean {
        return isAtLineStart(text, index)
    }

    private fun looksLikeStreamingA2uiObject(text: String, braceIndex: Int): Boolean {
        val tail = text.substring(braceIndex)
        if (containsA2uiKeyword(tail) || tail.contains("\"version\"")) {
            return true
        }
        // Very early in streaming `{ \n "ver...` before the full first key arrives
        val afterBrace = skipWhitespace(tail, 1)
        if (afterBrace >= tail.length) return true
        return tail[afterBrace] == '"' && tail.length - braceIndex < 48
    }

    private fun containsA2uiKeyword(text: String): Boolean {
        return A2UI_MESSAGE_KEYS.any { key -> text.contains("\"$key\"") }
    }

    private fun countBackticks(text: String, start: Int): Int {
        var pos = start
        while (pos < text.length && text[pos] == '`') {
            pos++
        }
        return pos - start
    }

    private fun normalizeDisplayText(raw: String): String {
        val trimmed = raw.trim()
        if (trimmed.isEmpty()) return ""
        return trimmed.replace(Regex("\n{3,}"), "\n\n")
    }

    private data class A2uiObjectMetadata(
        val isA2ui: Boolean,
        val createdSurfaceId: String? = null,
    )

    /**
     * Iteratively inspects the top-level properties of a balanced JSON object without recursion.
     */
    private fun parseA2uiObjectMetadata(json: String): A2uiObjectMetadata {
        val nonA2ui = A2uiObjectMetadata(isA2ui = false)
        var index = skipWhitespace(json, 0)
        if (index >= json.length || json[index] != '{') return nonA2ui
        index++

        var isA2ui = false
        var createdSurfaceId: String? = null

        while (index < json.length) {
            index = skipWhitespace(json, index)
            if (index >= json.length) return nonA2ui
            if (json[index] == '}') break

            val (key, afterKey) = readJsonString(json, index) ?: return nonA2ui
            index = skipWhitespace(json, afterKey)
            if (index >= json.length || json[index] != ':') return nonA2ui
            index = skipWhitespace(json, index + 1)
            if (index >= json.length) return nonA2ui

            val valueEnd = skipJsonValue(json, index)
            if (valueEnd == -1) return nonA2ui

            if (key in A2UI_MESSAGE_KEYS) {
                isA2ui = true
                if (key == "createSurface" && json[index] == '{') {
                    createdSurfaceId = readStringPropertyFromObject(
                        json = json,
                        objectStart = index,
                        objectEnd = valueEnd,
                        targetKey = "surfaceId",
                    )
                }
            }

            index = skipWhitespace(json, valueEnd)
            if (index < json.length && json[index] == ',') {
                index++
            } else if (index < json.length && json[index] == '}') {
                break
            } else {
                return nonA2ui
            }
        }

        return A2uiObjectMetadata(isA2ui = isA2ui, createdSurfaceId = createdSurfaceId)
    }

    private fun readStringPropertyFromObject(
        json: String,
        objectStart: Int,
        objectEnd: Int,
        targetKey: String,
    ): String? {
        var index = skipWhitespace(json, objectStart + 1)
        while (index < objectEnd) {
            if (json[index] == '}') return null
            val (key, afterKey) = readJsonString(json, index) ?: return null
            index = skipWhitespace(json, afterKey)
            if (index >= objectEnd || json[index] != ':') return null
            index = skipWhitespace(json, index + 1)
            if (index >= objectEnd) return null

            if (key == targetKey && json[index] == '"') {
                return readJsonString(json, index)?.first
            }

            val valueEnd = skipJsonValue(json, index)
            if (valueEnd == -1 || valueEnd > objectEnd) return null
            index = skipWhitespace(json, valueEnd)
            if (index < objectEnd && json[index] == ',') {
                index = skipWhitespace(json, index + 1)
            } else {
                break
            }
        }
        return null
    }

    /**
     * Iteratively skips a single JSON value starting at [start], returning the exclusive end index
     * or `-1` if the value is incomplete or malformed.
     */
    private fun skipJsonValue(s: String, start: Int): Int {
        val index = skipWhitespace(s, start)
        if (index >= s.length) return -1

        return when (s[index]) {
            '{', '[' -> {
                var depth = 0
                var inString = false
                var escaped = false
                for (pos in index until s.length) {
                    val ch = s[pos]
                    if (inString) {
                        if (escaped) {
                            escaped = false
                        } else if (ch == '\\') {
                            escaped = true
                        } else if (ch == '"') {
                            inString = false
                        }
                    } else {
                        when (ch) {
                            '"' -> inString = true
                            '{', '[' -> depth++
                            '}', ']' -> {
                                depth--
                                if (depth == 0) return pos + 1
                                if (depth < 0) return -1
                            }
                        }
                    }
                }
                -1
            }

            '"' -> {
                var escaped = false
                for (pos in (index + 1) until s.length) {
                    val ch = s[pos]
                    if (escaped) {
                        escaped = false
                    } else if (ch == '\\') {
                        escaped = true
                    } else if (ch == '"') {
                        return pos + 1
                    }
                }
                -1
            }

            else -> {
                var pos = index
                while (pos < s.length) {
                    val ch = s[pos]
                    if (ch.isJsonWhitespace() || ch == ',' || ch == '}' || ch == ']') break
                    pos++
                }
                if (pos == index) -1 else pos
            }
        }
    }

    private fun readJsonString(s: String, start: Int): Pair<String, Int>? {
        if (start >= s.length || s[start] != '"') return null
        val builder = StringBuilder()
        var pos = start + 1
        while (pos < s.length) {
            when (val ch = s[pos]) {
                '"' -> return builder.toString() to (pos + 1)
                '\\' -> {
                    pos++
                    if (pos >= s.length) return null
                    when (val esc = s[pos]) {
                        '"', '\\', '/' -> builder.append(esc)
                        'b' -> builder.append('\b')
                        'f' -> builder.append('\u000C')
                        'n' -> builder.append('\n')
                        'r' -> builder.append('\r')
                        't' -> builder.append('\t')
                        'u' -> {
                            if (pos + 4 >= s.length) return null
                            val hex = s.substring(pos + 1, pos + 5)
                            val code = hex.toIntOrNull(16) ?: return null
                            builder.append(code.toChar())
                            pos += 4
                        }

                        else -> builder.append(esc)
                    }
                }

                else -> builder.append(ch)
            }
            pos++
        }
        return null
    }

    private fun skipWhitespace(s: String, start: Int): Int {
        var pos = start
        while (pos < s.length && s[pos].isJsonWhitespace()) {
            pos++
        }
        return pos
    }

    private fun skipWhitespaceAndDelimiters(s: String, start: Int): Int {
        var pos = start
        while (pos < s.length && (s[pos].isJsonWhitespace() || s[pos] == ',')) {
            pos++
        }
        return pos
    }

    private fun Char.isJsonWhitespace(): Boolean {
        return this == ' ' || this == '\t' || this == '\n' || this == '\r'
    }
}
