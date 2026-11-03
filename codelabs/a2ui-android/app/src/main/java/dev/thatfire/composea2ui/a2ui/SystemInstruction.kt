package dev.thatfire.composea2ui.a2ui

import android.content.res.Resources
import androidx.a2ui.compose.ui.A2uiCatalog
import androidx.a2ui.compose.ui.toJsonSchemaString
import androidx.annotation.RawRes
import dev.thatfire.composea2ui.R

fun buildSystemInstruction(resources: Resources, catalog: A2uiCatalog): String = buildString {
    appendLine(resources.readRawText(R.raw.agent_instructions))
    appendLine("## A2UI JSON schemas")
    appendLine("### Server-to-client messages")
    appendLine(resources.readRawText(R.raw.a2ui_server_to_client_schema))
    appendLine("### Common types")
    appendLine(resources.readRawText(R.raw.a2ui_common_types_schema))
    appendLine("### Component catalog")
    appendLine(catalog.toJsonSchemaString())
    appendLine()
    appendLine("## Examples")
    append(resources.readExamples(catalogId = catalog.id))
}

private fun Resources.readRawText(@RawRes id: Int): String =
    openRawResource(id).bufferedReader().use { it.readText() }

private fun Resources.readExamples(catalogId: String): String =
    readRawText(R.raw.a2ui_examples).replace("{{CATALOG_ID}}", catalogId)
