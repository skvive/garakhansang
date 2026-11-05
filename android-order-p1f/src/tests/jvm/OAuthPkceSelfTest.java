import site.lexid.garakhansang.order.OAuthPkce;
import java.net.URI;
import java.net.URLDecoder;
import java.util.HashMap;
import java.util.Map;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;

public class OAuthPkceSelfTest {
    static int count=0;
    static void expect(boolean b,String why) { count++; if(!b)throw new AssertionError(why); }
    static void rejects(Runnable f,String why){
        count++;try{f.run();throw new AssertionError("Expected rejection: "+why);}
        catch(IllegalArgumentException okay){}
    }
    static Map<String,String> params(String url)throws Exception {
        Map<String,String> r=new HashMap<>();
        for(String kv:new URI(url).getRawQuery().split("&")){
            String[] pair=kv.split("=",2);r.put(URLDecoder.decode(pair[0],"UTF-8"),URLDecoder.decode(pair[1],"UTF-8"));
        }return r;
    }
    public static void main(String[] args)throws Exception {
        final String issuer="https://branch.neonauth.aws.neon.tech/neondb/auth";
        final String authorize=issuer+"/oauth2/authorize";
        final String callback="https://garak.lexid.site/app/oauth/callback";
        final String resource="https://dev-api.lexid.site";
        OAuthPkce.Pending pending=OAuthPkce.begin(issuer,authorize,"public-test-client",callback,resource);
        Map<String,String> params=params(pending.authorizationUrl);
        expect("code".equals(params.get("response_type")),"authorization code only");
        expect("S256".equals(params.get("code_challenge_method")),"PKCE S256 mandatory");
        expect("openid profile email".equals(params.get("scope")),"OIDC scope");
        expect(params.get("state").length()>=40,"strong state");
        expect(params.get("nonce").length()>=40,"strong nonce");
        expect(resource.equals(params.get("resource")),"audience pinned");
        OAuthPkce.Result verified=pending.consumeCallback(callback+"?code=code1234&state="+params.get("state"));
        byte[] hash=MessageDigest.getInstance("SHA-256").digest(verified.codeVerifier.getBytes(StandardCharsets.US_ASCII));
        expect(params.get("code_challenge").equals(Base64.getUrlEncoder().withoutPadding().encodeToString(hash)),"challenge matches verifier");
        expect("code1234".equals(verified.authorizationCode),"code delivered once");
        rejects(()->pending.consumeCallback(callback+"?code=other&state="+params.get("state")),"replay");
        OAuthPkce.Pending wrongState=OAuthPkce.begin(issuer,authorize,"public-test-client",callback,resource);
        rejects(()->wrongState.consumeCallback(callback+"?code=abc&state=attacker"),"wrong state");
        OAuthPkce.Pending wrongHost=OAuthPkce.begin(issuer,authorize,"public-test-client",callback,resource);
        rejects(()->wrongHost.consumeCallback("https://attacker.lexid.site/app/oauth/callback?code=abc&state=x"),"wrong host");
        OAuthPkce.Pending dupe=OAuthPkce.begin(issuer,authorize,"public-test-client",callback,resource);
        Map<String,String> dupeParam=params(dupe.authorizationUrl);
        rejects(()->dupe.consumeCallback(callback+"?code=a&state="+dupeParam.get("state")+"&state="+dupeParam.get("state")),"duplicate state");
        rejects(()->OAuthPkce.begin("http://example.com/a","http://example.com/a/authorize","public-id",callback,resource),"http issuer");
        rejects(()->OAuthPkce.begin(issuer,"https://evil.neonauth.aws.neon.tech/oauth","public-id",callback,resource),"issuer mismatch");
        rejects(()->OAuthPkce.begin(issuer,authorize,"public-id","http://garak.lexid.site/callback",resource),"http redirect");
        rejects(()->OAuthPkce.begin(issuer,authorize,"public-id","https://garak.lexid.site",resource),"missing redirect path");
        System.out.println("OAuth PKCE JVM checks: "+count+" passed");
    }
}
