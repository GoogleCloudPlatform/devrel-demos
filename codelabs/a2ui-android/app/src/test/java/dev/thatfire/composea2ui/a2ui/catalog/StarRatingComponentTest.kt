package dev.thatfire.composea2ui.a2ui.catalog

import androidx.a2ui.compose.ui.A2uiCatalog
import androidx.a2ui.compose.ui.toJsonSchemaString
import org.junit.Assert.assertEquals
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test

class StarRatingComponentTest {

    @Test
    fun `exports CustomButtonComponent and StarRating schema inside custom A2uiCatalog`() {
        val catalog = A2uiCatalog(
            catalogId = CUSTOM_CATALOG_ID,
            components = listOf(CustomButtonComponent, StarRatingComponent),
        )

        assertEquals("https://example.com/catalogv1", catalog.id)
        assertSame(CustomButtonComponent, catalog.components["Button"])
        assertSame(StarRatingComponent, catalog.components["StarRating"])

        val schema = catalog.toJsonSchemaString()
        assertTrue(schema.contains("https://example.com/catalogv1"))
        assertTrue(schema.contains("\"Button\""))
        assertTrue(schema.contains("\"StarRating\""))
        assertTrue(schema.contains("\"value\""))
        assertTrue(schema.contains("\"max\""))
    }
}
