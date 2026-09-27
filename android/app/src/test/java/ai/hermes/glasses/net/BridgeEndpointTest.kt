package ai.hermes.glasses.net

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class BridgeEndpointTest {
    @Test
    fun acceptsTailnetHttpAddress() {
        assertEquals(
            "http://100.106.184.56:8788",
            BridgeEndpoint.normalize("http://100.106.184.56:8788/"),
        )
    }

    @Test
    fun acceptsPublicHttpsAddress() {
        assertEquals("https://voice.example.com", BridgeEndpoint.normalize("https://voice.example.com"))
    }

    @Test
    fun rejectsPublicCleartextAddress() {
        assertThrows(IllegalArgumentException::class.java) {
            BridgeEndpoint.normalize("http://203.0.113.8:8788")
        }
    }

    @Test
    fun rejectsPathThatCouldRedirectCredentials() {
        assertThrows(IllegalArgumentException::class.java) {
            BridgeEndpoint.normalize("http://100.64.0.1:8788/not-the-bridge")
        }
    }
}
