package site.lexid.garakhansang.order;

import java.net.URI;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * PKCE S256 URL/state helper for a FUTURE registered Neon Auth public OAuth client.
 *
 * No authorization or token exchange is started in v1.7. The Neon OAuth provider,
 * a public client, and an Android VERIFIED HTTPS App Link are mandatory first.
 * This code never uses WebView, client secrets, implicit flow, or stores tokens.
 */
public final class OAuthPkce {
    private OAuthPkce() {}
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final long MAX_AGE_MS = 10 * 60 * 1000L;

    private static URI checkedHttps(String input) {
        try {
            URI uri = new URI(input);
            if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null
                || uri.getHost().isEmpty() || uri.getRawUserInfo() != null
                || uri.getRawQuery() != null || uri.getRawFragment() != null
                || (uri.getPort() != -1 && uri.getPort() != 443)
                || input.length() > 1024) {
                throw new IllegalArgumentException("HTTPS/OAuth endpoint 설정 오류");
            }
            return uri;
        } catch (java.net.URISyntaxException | NullPointerException exc) {
            throw new IllegalArgumentException("OAuth endpoint 설정 오류", exc);
        }
    }
    private static String nonce() {
        byte[] entropy = new byte[32];
        RANDOM.nextBytes(entropy);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(entropy);
    }
    private static String sha256Base64(String value) {
        try {
            byte[] hash=MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.US_ASCII));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(hash);
        } catch (java.security.NoSuchAlgorithmException exc) {
            throw new IllegalStateException("SHA-256 is mandatory", exc);
        }
    }
    private static String url(String s) {
        try { return URLEncoder.encode(s, "UTF-8").replace("+", "%20"); }
        catch (java.io.UnsupportedEncodingException e) { throw new IllegalStateException(e); }
    }

    public static Pending begin(String issuer, String authorizationEndpoint,
                                String clientId, String verifiedRedirectUri, String resource) {
        URI origin=checkedHttps(issuer);
        URI authorization=checkedHttps(authorizationEndpoint);
        URI redirect=checkedHttps(verifiedRedirectUri);
        if (!origin.getHost().equalsIgnoreCase(authorization.getHost())
            || !authorization.getPath().startsWith(origin.getPath().replaceAll("/$", "")+"/")
            || clientId == null || !clientId.matches("[a-zA-Z0-9._~-]{3,256}")
            || resource == null || resource.isEmpty()) {
            throw new IllegalArgumentException("Issuer / authorization / client / resource mismatch");
        }
        checkedHttps(resource); // API resource must be a public HTTPS origin/path
        if (redirect.getPath() == null || redirect.getPath().equals("/") || redirect.getPath().isEmpty())
            throw new IllegalArgumentException("Verified HTTPS App Link path is required");
        String verifier=nonce(),state=nonce(),requestNonce=nonce();
        StringBuilder b=new StringBuilder(authorization.toString());
        b.append("?response_type=code&client_id=").append(url(clientId));
        b.append("&redirect_uri=").append(url(redirect.toString()));
        b.append("&scope=").append(url("openid profile email"));
        b.append("&code_challenge_method=S256&code_challenge=").append(url(sha256Base64(verifier)));
        b.append("&state=").append(url(state)).append("&nonce=").append(url(requestNonce));
        b.append("&resource=").append(url(resource));
        return new Pending(b.toString(),redirect,verifier,state,System.currentTimeMillis());
    }

    public static final class Pending {
        public final String authorizationUrl;
        private final URI redirect;
        private final String verifier;
        private final String state;
        private final long createdAt;
        private final AtomicBoolean used=new AtomicBoolean(false);
        private Pending(String authorizationUrl,URI redirect,String verifier,String state,long at){
            this.authorizationUrl=authorizationUrl;this.redirect=redirect;
            this.verifier=verifier;this.state=state;this.createdAt=at;
        }
        /** One-time, state-bound result. Caller must exchange code on the registered token endpoint with verifier. */
        public Result consumeCallback(String candidate) {
            if (!used.compareAndSet(false,true)) throw new IllegalArgumentException("OAuth callback already consumed");
            if (System.currentTimeMillis()-createdAt>MAX_AGE_MS) throw new IllegalArgumentException("OAuth login expired");
            try {
                URI got=new URI(candidate);
                if (!redirect.getScheme().equalsIgnoreCase(got.getScheme())
                    || !redirect.getHost().equalsIgnoreCase(got.getHost())
                    || redirect.getPort()!=got.getPort()
                    || !redirect.getRawPath().equals(got.getRawPath())
                    || got.getRawFragment()!=null || got.getRawUserInfo()!=null) {
                    throw new IllegalArgumentException("OAuth redirect mismatch");
                }
                Map<String,String> params=new HashMap<>();
                if (got.getRawQuery()==null || got.getRawQuery().length()>8192)
                    throw new IllegalArgumentException("OAuth callback query missing/oversized");
                for (String part:got.getRawQuery().split("&",-1)) {
                    String[] kv=part.split("=",2);
                    if(kv.length!=2)throw new IllegalArgumentException("Malformed OAuth callback query");
                    String key=URLDecoder.decode(kv[0],"UTF-8");
                    if(params.putIfAbsent(key,URLDecoder.decode(kv[1],"UTF-8"))!=null)
                        throw new IllegalArgumentException("Repeated OAuth callback parameter");
                }
                if (params.containsKey("error"))throw new IllegalArgumentException("OAuth authorization refused");
                String receivedState=params.get("state"),code=params.get("code");
                if (receivedState==null || !MessageDigest.isEqual(state.getBytes(StandardCharsets.UTF_8),
                        receivedState.getBytes(StandardCharsets.UTF_8)))
                    throw new IllegalArgumentException("OAuth state mismatch");
                if (code==null || code.isEmpty() || code.length()>4096 || code.indexOf('\n')>=0 || code.indexOf('\r')>=0)
                    throw new IllegalArgumentException("Invalid authorization code");
                return new Result(code,verifier);
            } catch (java.net.URISyntaxException | java.io.UnsupportedEncodingException | NullPointerException e) {
                throw new IllegalArgumentException("Malformed OAuth callback",e);
            }
        }
    }
    public static final class Result {
        public final String authorizationCode;
        public final String codeVerifier;
        private Result(String code,String verifier){this.authorizationCode=code;this.codeVerifier=verifier;}
    }
}
