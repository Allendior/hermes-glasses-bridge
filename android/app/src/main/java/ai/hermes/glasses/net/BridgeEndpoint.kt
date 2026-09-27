package ai.hermes.glasses.net

import java.net.URI

/** Validates that bearer credentials are only sent through TLS or to a tailnet/local address. */
object BridgeEndpoint {
    fun normalize(value: String): String {
        val uri = try {
            URI(value.trim())
        } catch (_: Exception) {
            throw IllegalArgumentException("Enter a valid bridge URL")
        }
        val scheme = uri.scheme?.lowercase()
        val host = uri.host ?: throw IllegalArgumentException("Bridge URL needs a host")
        require(scheme == "http" || scheme == "https") { "Bridge URL must use http or https" }
        require(uri.userInfo == null && uri.query == null && uri.fragment == null) {
            "Bridge URL cannot include credentials, a query, or a fragment"
        }
        require(uri.path.isNullOrEmpty() || uri.path == "/") { "Bridge URL cannot include a path" }
        if (scheme == "http") {
            require(isPrivateDestination(host)) {
                "Plain HTTP is allowed only for a Tailscale or local address"
            }
        }
        val port = if (uri.port == -1) "" else ":${uri.port}"
        return "$scheme://$host$port"
    }

    private fun isPrivateDestination(host: String): Boolean {
        if (host == "localhost" || host == "127.0.0.1" || host == "10.0.2.2") return true
        val octets = host.split('.').mapNotNull(String::toIntOrNull)
        return octets.size == 4 && octets.all { it in 0..255 } &&
            octets[0] == 100 && octets[1] in 64..127
    }
}
