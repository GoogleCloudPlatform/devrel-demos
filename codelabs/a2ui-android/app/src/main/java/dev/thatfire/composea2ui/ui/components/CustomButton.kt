package dev.thatfire.composea2ui.ui.components

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import dev.thatfire.composea2ui.ui.theme.ComposeA2UITheme

private val ButtonShape = RoundedCornerShape(14.dp)

private val EnabledGradientStops = listOf(
    Color(0xFF0284C7),
    Color(0xFF6366F1),
    Color(0xFFA855F7),
    Color(0xFFEC4899),
)

private val DisabledGradientStops = listOf(
    Color(0xFF64748B),
    Color(0xFF94A3B8),
)

private val RimHighlightBrush = Brush.verticalGradient(
    colors = listOf(
        Color.White.copy(alpha = 0.85f),
        Color.White.copy(alpha = 0.25f),
    ),
)

@Composable
fun CustomButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    content: @Composable RowScope.() -> Unit,
) {
    val infiniteTransition = rememberInfiniteTransition(label = "CustomButtonShine")
    val shineProgress by infiniteTransition.animateFloat(
        initialValue = -0.5f,
        targetValue = 1.5f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 2200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart,
        ),
        label = "CustomButtonShineSweep",
    )

    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier
            .padding(vertical = 4.dp)
            .defaultMinSize(minHeight = 48.dp)
            .shadow(
                elevation = if (enabled) 6.dp else 0.dp,
                shape = ButtonShape,
            )
            .clip(ButtonShape)
            .drawBehind {
                // 1. Vibrant multi-stop diagonal gradient base
                drawRect(
                    brush = Brush.linearGradient(
                        colors = if (enabled) EnabledGradientStops else DisabledGradientStops,
                        start = Offset.Zero,
                        end = Offset(size.width, size.height * 1.4f),
                    ),
                )

                if (enabled) {
                    // 2. Top-edge glossy specular reflection
                    drawRect(
                        brush = Brush.verticalGradient(
                            0.0f to Color.White.copy(alpha = 0.36f),
                            0.48f to Color.White.copy(alpha = 0.08f),
                            0.50f to Color.Transparent,
                            1.0f to Color.Transparent,
                        ),
                    )

                    // 3. Animated diagonal light glint sweeping across the surface
                    val sweepWidth = size.width * 0.45f
                    val centerX = size.width * shineProgress
                    drawRect(
                        brush = Brush.linearGradient(
                            colors = listOf(
                                Color.Transparent,
                                Color.White.copy(alpha = 0.48f),
                                Color.Transparent,
                            ),
                            start = Offset(centerX - sweepWidth, 0f),
                            end = Offset(centerX + sweepWidth, size.height),
                        ),
                    )
                }
            }
            .border(
                width = 1.5.dp,
                brush = RimHighlightBrush,
                shape = ButtonShape,
            ),
        shape = ButtonShape,
        colors = ButtonDefaults.buttonColors(
            containerColor = Color.Transparent,
            contentColor = Color.White,
            disabledContainerColor = Color.Transparent,
            disabledContentColor = Color.White.copy(alpha = 0.7f),
        ),
        contentPadding = PaddingValues(horizontal = 24.dp, vertical = 12.dp),
        content = content,
    )
}

@Preview(showBackground = true)
@Composable
private fun CustomButtonPreview() {
    ComposeA2UITheme {
        CustomButton(onClick = {}) {
            Text(text = "Save Ratings")
        }
    }
}
