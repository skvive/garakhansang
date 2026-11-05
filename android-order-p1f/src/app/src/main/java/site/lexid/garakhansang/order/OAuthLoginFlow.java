package site.lexid.garakhansang.order;

/**
 * Fail-closed, in-memory OAuth browser hand-off coordinator for a future
 * VERIFIED Android HTTPS App Link and registered Neon Auth PUBLIC client.
 *
 * This class never opens a browser, registers an Android intent filter, saves
 * a token or enables login. A trusted Android Activity may integrate it ONLY
 * after checking verified domain ownership and all three readiness gates.
 * Android process death cancels the attempt and requires a fresh login.
 */
public final class OAuthLoginFlow {
    public static final class VerifiedConfiguration {
        public final String issuer, authorizationEndpoint, tokenEndpoint;
        public final String publicClientId, redirectUri, resource;
        public final boolean verifiedAppLink, registeredPublicClient, devAuthReady;

        public VerifiedConfiguration(String issuer, String authorizationEndpoint,
                String tokenEndpoint, String publicClientId, String redirectUri,
                String resource, boolean verifiedAppLink,
                boolean registeredPublicClient, boolean devAuthReady) {
            this.issuer = issuer;
            this.authorizationEndpoint = authorizationEndpoint;
            this.tokenEndpoint = tokenEndpoint;
            this.publicClientId = publicClientId;
            this.redirectUri = redirectUri;
            this.resource = resource;
            this.verifiedAppLink = verifiedAppLink;
            this.registeredPublicClient = registeredPublicClient;
            this.devAuthReady = devAuthReady;
        }

        public boolean isReady() {
            return verifiedAppLink && registeredPublicClient && devAuthReady;
        }
    }

    private OAuthPkce.Pending pending;
    private VerifiedConfiguration configuration;

    /** Returns a browser URL, not an access token. Starts nothing if a gate fails. */
    public synchronized String begin(VerifiedConfiguration config) {
        cancel();
        if (config == null || !config.isReady())
            throw new IllegalStateException("Verified App Link / OAuth client / development auth required");
        // Build an authorization request using the existing S256/state implementation.
        OAuthPkce.Pending attempt = OAuthPkce.begin(config.issuer,
                config.authorizationEndpoint, config.publicClientId,
                config.redirectUri, config.resource);
        pending = attempt;
        configuration = config;
        return attempt.authorizationUrl;
    }

    /** Consume the exact HTTPS callback once; rejects mismatched state and replay. */
    public synchronized OAuthCodeExchange.Request consumeVerifiedCallback(String url) {
        OAuthPkce.Pending attempt = pending;
        VerifiedConfiguration config = configuration;
        cancel(); // always consume, even on an invalid callback
        if (attempt == null || config == null || !config.isReady())
            throw new IllegalStateException("No valid pending OAuth request");
        OAuthPkce.Result result = attempt.consumeCallback(url);
        return OAuthCodeExchange.prepare(config.issuer, config.tokenEndpoint,
                config.publicClientId, config.redirectUri, config.resource, result);
    }

    public synchronized void cancel() {
        pending = null;
        configuration = null;
    }

    public synchronized boolean hasPendingRequest() {
        return pending != null;
    }
}
