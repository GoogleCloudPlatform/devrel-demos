package dev.thatfire.composea2ui.a2ui.catalog

import androidx.a2ui.compose.runtime.A2uiComponentScope
import androidx.a2ui.compose.runtime.A2uiComponentState
import androidx.a2ui.compose.ui.A2uiComponent
import androidx.a2ui.compose.ui.catalog.A2uiBasicCatalogV1
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import dev.thatfire.composea2ui.ui.components.CustomButton

object CustomButtonComponent : A2uiBasicCatalogV1.Button {
    @Composable
    override fun A2uiComponentScope.TypedContent(
        childId: String,
        variant: A2uiBasicCatalogV1.Button.Variant,
        action: Map<String, Any?>,
        accessibility: A2uiBasicCatalogV1.AccessibilityAttributes?,
        checks: List<A2uiBasicCatalogV1.CheckRule>,
        modifier: Modifier,
    ) {
        val allChecksPassed = checks.all { it.condition }
        val childState = observeA2uiComponentState(childId)

        CustomButton(
            onClick = { dispatchAction(action) },
            enabled = allChecksPassed && childState is A2uiComponentState.Success,
            modifier = modifier,
        ) {
            if (childState is A2uiComponentState.Success) {
                A2uiComponent(childState.component)
            }
        }
    }
}
