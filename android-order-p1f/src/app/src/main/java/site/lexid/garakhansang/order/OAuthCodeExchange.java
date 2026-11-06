package site.lexid.garakhansang.order;

import java.net.URI;
import java.net.URISyntaxException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Locale;

/**
 * Immutable OAuth authorization-code/PKCE exchange contract.
 *
 * Deliberately contains no network or persistence. A future installed-app
 * integration may call OAuthTokenHttp after the OAuth issuer, client, callback,
 * HTTPS Digital Asset Link and server audience have all been verified.
 * It MUST NOT use client_secret or accept bearer tokens as identity locally.
 */
public final class OAuthCodeExchange {
    private OAuthCodeExchange() {}
    private static final int MAX_TOKEN_CHARS = 16384;

    private static URI https(String value, boolean pathRequired) {
        try {
            URI uri = new URI(value);
            if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost()==null
                || uri.getHost().length()>253 || uri.getHost().isEmpty()
                || uri.getRawUserInfo()!=null || uri.getRawQuery()!=null || uri.getRawFragment()!=null
                || (uri.getPort()!=-1 && uri.getPort()!=443) || value.length()>1024
                || (pathRequired && (uri.getRawPath()==null || uri.getRawPath().isEmpty()
                    || uri.getRawPath().equals("/")))) {
                throw new IllegalArgumentException("Unverified HTTPS OAuth endpoint");
            }
            return uri;
        } catch (URISyntaxException | NullPointerException e) {
            throw new IllegalArgumentException("Invalid OAuth HTTPS endpoint",e);
        }
    }
    private static String encoded(String value) {
        try { return URLEncoder.encode(value,"UTF-8").replace("+","%20"); }
        catch (java.io.UnsupportedEncodingException e) { throw new IllegalStateException(e); }
    }

    public static Request prepare(String issuerUrl, String tokenEndpointUrl,
                                  String publicClientId, String redirectUri,
                                  String resource, OAuthPkce.Result callback) {
        URI issuer = https(issuerUrl,true);
        URI tokenEndpoint = https(tokenEndpointUrl,true);
        URI redirect = https(redirectUri,true);
        https(resource,false);
        if (!issuer.getHost().equalsIgnoreCase(tokenEndpoint.getHost())
            || !tokenEndpoint.getRawPath().startsWith(issuer.getRawPath().replaceAll("/$", "") + "/")
            || redirect.getRawPath().contains("..")
            || publicClientId == null || !publicClientId.matches("[A-Za-z0-9._~-]{3,256}")
            || callback==null || callback.authorizationCode==null
            || callback.authorizationCode.isEmpty() || callback.authorizationCode.length()>4096
            || callback.authorizationCode.indexOf('\n')>=0 || callback.authorizationCode.indexOf('\r')>=0
            || callback.codeVerifier==null
            || !callback.codeVerifier.matches("[A-Za-z0-9_-]{43,128}")) {
            throw new IllegalArgumentException("OAuth token exchange configuration rejected");
        }
        for (int i=0;i<callback.authorizationCode.length();i++) {
            if (Character.isISOControl(callback.authorizationCode.charAt(i)))
                throw new IllegalArgumentException("Authorization code control character");
        }
        String body = "grant_type=authorization_code&code="+encoded(callback.authorizationCode)
            +"&client_id="+encoded(publicClientId)
            +"&redirect_uri="+encoded(redirect.toString())
            +"&code_verifier="+encoded(callback.codeVerifier)
            +"&resource="+encoded(resource);
        if (body.length()>15000) throw new IllegalArgumentException("OAuth request too large");
        return new Request(tokenEndpoint.toString(),body);
    }

    public static Token validatedToken(String tokenType, String accessToken, long expiresInSeconds) {
        if (!"Bearer".equals(tokenType) || accessToken==null || accessToken.length()<8
            || accessToken.length()>MAX_TOKEN_CHARS
            || !accessToken.matches("[A-Za-z0-9._~+/-]+(?:\\.[A-Za-z0-9_-]+){0,3}={0,2}")
            || expiresInSeconds<1 || expiresInSeconds>86400) {
            throw new IllegalArgumentException("Unusable OAuth access token response");
        }
        // Token is intentionally ephemeral and has no toString() implementation containing data.
        return new Token(accessToken,expiresInSeconds);
    }

    public static final class Request {
        public final String tokenEndpoint;
        public final String formBody;
        private Request(String endpoint,String body) { tokenEndpoint=endpoint;formBody=body; }
        @Override public String toString() { return "OAuthCodeExchange.Request(redacted)"; }
    }
    public static final class Token {
        private final String secret;
        private final long expiresInSeconds;
        private Token(String secret,long seconds){this.secret=secret;this.expiresInSeconds=seconds;}
        /** Only pass this to a validated HTTPS resource API; never log or persist. */
        public String ephemeralBearer(){return secret;}
        public long expiresInSeconds(){return expiresInSeconds;}
        @Override public String toString(){return "OAuthCodeExchange.Token(redacted)";}
    }
}
