package dev.thatfire.composea2ui.ui.components

import androidx.compose.foundation.layout.Row
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.twotone.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import dev.thatfire.composea2ui.R
import dev.thatfire.composea2ui.ui.theme.ComposeA2UITheme

private const val MAX_STARS = 10

@Composable
fun StarRating(
    rating: Int,
    max: Int = 5,
    onRatingChange: ((Int) -> Unit)?,
    modifier: Modifier = Modifier,
) {
    val clampedMax = max.coerceIn(1, MAX_STARS)
    val clampedRating = rating.coerceIn(0, clampedMax)

    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        for (star in 1..clampedMax) {
            val isSelected = star <= clampedRating
            IconButton(
                onClick = { onRatingChange?.invoke(star) },
                enabled = onRatingChange != null,
            ) {
                Icon(
                    imageVector = if (isSelected) Icons.Filled.Star else Icons.TwoTone.Star,
                    contentDescription = stringResource(
                        R.string.star_rating_item_description,
                        star,
                        clampedMax,
                    ),
                    tint = if (isSelected) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.outline
                    },
                )
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun StarRatingPreview() {
    ComposeA2UITheme {
        StarRating(
            rating = 3,
            max = 5,
            onRatingChange = {},
        )
    }
}
