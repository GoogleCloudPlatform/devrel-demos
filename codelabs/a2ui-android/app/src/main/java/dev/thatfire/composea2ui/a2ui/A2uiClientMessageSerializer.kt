package dev.thatfire.composea2ui.a2ui

import androidx.a2ui.model.protocol.A2uiClientErrorMessage
import androidx.a2ui.model.protocol.A2uiClientEventMessage
import androidx.a2ui.model.protocol.A2uiClientToServerMessage
import androidx.a2ui.model.protocol.A2uiProtocolConstants
import java.time.Instant

/**
 * Serializes [A2uiClientToServerMessage] instances (`action` and `error` events emitted on
 * `A2uiMessageProcessor.outboundEvents`) into A2UI v0.9 JSON strings to send back to the agent.
 */
internal object A2uiClientMessageSerializer {

    private const val MAX_JSON_DEPTH = 32
    private const val INDENT = "  "

    fun serialize(
        message: A2uiClientToServerMessage,
        prettyPrint: Boolean = false,
    ): String {
        val payload: Map<String, Any?> = when (message) {
            is A2uiClientEventMessage -> {
                val actionMap = buildMap<String, Any?> {
                    put("name", message.type)
                    put("surfaceId", message.surfaceId)
                    put("sourceComponentId", message.componentId)
                    put("timestamp", Instant.ofEpochMilli(message.timestamp).toString())
                    put("context", message.context)
                }
                buildMap {
                    put("version", A2uiProtocolConstants.PROTOCOL_VERSION)
                    put("action", actionMap)
                    message.clientDataModel?.let { dataModel ->
                        putAll(dataModel.toPayloadMap())
                    }
                }
            }

            is A2uiClientErrorMessage -> {
                val errorMap = buildMap<String, Any?> {
                    put("code", message.code)
                    put("surfaceId", message.surfaceId)
                    put("message", message.message)
                    for ((key, value) in message.context) {
                        if (!containsKey(key)) {
                            put(key, value)
                        }
                    }
                }
                mapOf(
                    "version" to A2uiProtocolConstants.PROTOCOL_VERSION,
                    "error" to errorMap,
                )
            }
        }

        return buildString {
            appendJsonValue(payload, depth = 0, prettyPrint = prettyPrint)
        }
    }

    private fun StringBuilder.appendJsonValue(
        value: Any?,
        depth: Int,
        prettyPrint: Boolean,
    ) {
        if (depth > MAX_JSON_DEPTH) {
            append("null")
            return
        }
        when (value) {
            null -> append("null")
            is Boolean -> append(value)
            is Number -> {
                val doubleVal = value.toDouble()
                if (doubleVal.isNaN() || doubleVal.isInfinite()) {
                    append("null")
                } else {
                    append(value)
                }
            }

            is String -> appendJsonString(value)
            is Map<*, *> -> {
                val entries = value.entries.filter { it.key != null }
                if (entries.isEmpty()) {
                    append("{}")
                    return
                }
                append('{')
                val childIndent = if (prettyPrint) INDENT.repeat(depth + 1) else ""
                entries.forEachIndexed { index, (k, v) ->
                    if (index > 0) append(',')
                    if (prettyPrint) {
                        append('\n')
                        append(childIndent)
                    }
                    appendJsonString(k.toString())
                    append(if (prettyPrint) ": " else ":")
                    appendJsonValue(v, depth + 1, prettyPrint)
                }
                if (prettyPrint) {
                    append('\n')
                    append(INDENT.repeat(depth))
                }
                append('}')
            }

            is Iterable<*> -> {
                val items = value.toList()
                if (items.isEmpty()) {
                    append("[]")
                    return
                }
                append('[')
                val childIndent = if (prettyPrint) INDENT.repeat(depth + 1) else ""
                items.forEachIndexed { index, item ->
                    if (index > 0) append(',')
                    if (prettyPrint) {
                        append('\n')
                        append(childIndent)
                    }
                    appendJsonValue(item, depth + 1, prettyPrint)
                }
                if (prettyPrint) {
                    append('\n')
                    append(INDENT.repeat(depth))
                }
                append(']')
            }

            is Array<*> -> {
                if (value.isEmpty()) {
                    append("[]")
                    return
                }
                append('[')
                val childIndent = if (prettyPrint) INDENT.repeat(depth + 1) else ""
                for (i in value.indices) {
                    if (i > 0) append(',')
                    if (prettyPrint) {
                        append('\n')
                        append(childIndent)
                    }
                    appendJsonValue(value[i], depth + 1, prettyPrint)
                }
                if (prettyPrint) {
                    append('\n')
                    append(INDENT.repeat(depth))
                }
                append(']')
            }

            else -> appendJsonString(value.toString())
        }
    }

    private fun StringBuilder.appendJsonString(value: String) {
        append('"')
        for (ch in value) {
            when (ch) {
                '"' -> append("\\\"")
                '\\' -> append("\\\\")
                '\b' -> append("\\b")
                '\u000C' -> append("\\f")
                '\n' -> append("\\n")
                '\r' -> append("\\r")
                '\t' -> append("\\t")
                else -> {
                    if (ch < ' ') {
                        append("\\u")
                        append(ch.code.toString(16).padStart(4, '0'))
                    } else {
                        append(ch)
                    }
                }
            }
        }
        append('"')
    }
}
