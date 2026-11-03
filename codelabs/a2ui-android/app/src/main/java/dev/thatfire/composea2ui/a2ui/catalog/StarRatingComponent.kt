package dev.thatfire.composea2ui.a2ui.catalog

import androidx.a2ui.compose.runtime.A2uiComponentProperties
import androidx.a2ui.compose.runtime.A2uiComponentScope
import androidx.a2ui.compose.runtime.A2uiProperty
import androidx.a2ui.compose.ui.A2uiComponent
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import dev.thatfire.composea2ui.ui.components.StarRating

object StarRatingComponent : A2uiComponent {
    override val name: String
        get() = "StarRating"

    override val description: String
        get() = "A row of stars representing a rating. " +
            "Set the value to a path to let the user change it."

    private val valueProperty = A2uiProperty.dynamicNumber(
        key = "value",
        required = true,
        description = "The current rating value, 0 to max",
    )

    private val maxProperty = A2uiProperty.number(
        key = "max",
        defaultValue = 5,
        description = "Max number of stars to show",
    )

    override val properties: List<A2uiProperty<*>>
        get() = listOf(valueProperty, maxProperty)

    @Composable
    override fun A2uiComponentScope.Content(
        properties: A2uiComponentProperties,
        modifier: Modifier,
    ) {
        val max = properties[maxProperty]?.toInt() ?: 5
        val value = properties.bind(valueProperty)?.toInt() ?: 0
        val onValueChange = properties.bindUpdater(valueProperty)

        StarRating(
            rating = value,
            max = max,
            onRatingChange = onValueChange,
            modifier = modifier,
        )
    }
}
