package dev.thatfire.composea2ui.a2ui

import androidx.a2ui.model.processor.A2uiMessageProcessor
import androidx.a2ui.model.protocol.A2uiDeleteSurfaceMessage

/** Deletes all currently active A2UI surfaces managed by this processor. */
fun A2uiMessageProcessor.clearSurfaces() {
    activeSurfaces.value.forEach { surface ->
        processMessage(A2uiDeleteSurfaceMessage(surfaceId = surface.id))
    }
}
