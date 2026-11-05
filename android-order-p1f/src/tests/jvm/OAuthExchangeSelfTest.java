import site.lexid.garakhansang.order.OAuthCodeExchange;
import site.lexid.garakhansang.order.OAuthPkce;
import java.net.URI;
import java.net.URLDecoder;
import java.util.LinkedHashMap;
import java.util.Map;

public final class OAuthExchangeSelfTest {
    static int count=0;
    private static void ok(boolean pass,String reason){count++;if(!pass)throw new AssertionError(reason);}
    private static void rejects(Runnable code,String reason){count++;try{code.run();throw new AssertionError("accepted "+reason);}catch(IllegalArgumentException expected){}}
    private static Map<String,String> params(String qs) throws Exception {
        Map<String,String> m=new LinkedHashMap<>();
        for(String pair:qs.split("&")){
            String[] p=pair.split("=",2);
            m.put(URLDecoder.decode(p[0],"UTF-8"), URLDecoder.decode(p.length>1?p[1]:"","UTF-8"));
        }
        return m;
    }
    public static void main(String... args) throws Exception {
        String issuer="https://stage.neonauth.example/neondb/auth";
        String auth=issuer+"/oauth2/authorize";
        String token=issuer+"/oauth2/token";
        String redirect="https://garak.lexid.site/order/oauth/callback";
        String resource="https://api-stage.lexid.site";
        OAuthPkce.Pending pending=OAuthPkce.begin(issuer,auth,"gho-public-test",redirect,resource);
        Map<String,String> authArgs=params(new URI(pending.authorizationUrl).getRawQuery());
        OAuthPkce.Result result=pending.consumeCallback(redirect+"?code=one_time_authorization_code&state="+authArgs.get("state"));
        OAuthCodeExchange.Request request=OAuthCodeExchange.prepare(issuer,token,"gho-public-test",redirect,resource,result);
        Map<String,String> form=params(request.formBody);
        ok(request.tokenEndpoint.equals(token),"exact endpoint");
        ok(form.get("grant_type").equals("authorization_code"),"code grant");
        ok(form.get("code").equals("one_time_authorization_code"),"code forwarding");
        ok(form.get("code_verifier").equals(result.codeVerifier),"PKCE forwarding");
        ok(form.get("client_id").equals("gho-public-test"),"public client ID");
        ok(form.get("redirect_uri").equals(redirect),"identical redirect URI");
        ok(form.get("resource").equals(resource),"resource audience");
        ok(!form.containsKey("client_secret") && !form.containsKey("refresh_token"),"no secret or refresh token");
        ok(!request.toString().contains(result.authorizationCode),"request toString must redact code");
        ok(!request.toString().contains(result.codeVerifier),"request toString must redact verifier");
        rejects(()->OAuthCodeExchange.prepare(issuer,"http://stage.neonauth.example/neondb/auth/oauth2/token","gho-public-test",redirect,resource,result),"HTTP token endpoint");
        rejects(()->OAuthCodeExchange.prepare(issuer,"https://bad.example/neondb/auth/oauth2/token","gho-public-test",redirect,resource,result),"token issuer mismatch");
        rejects(()->OAuthCodeExchange.prepare(issuer,"https://stage.neonauth.example/neondb/other/token","gho-public-test",redirect,resource,result),"token path mismatch");
        rejects(()->OAuthCodeExchange.prepare(issuer,token+"?open=1","gho-public-test",redirect,resource,result),"token query");
        rejects(()->OAuthCodeExchange.prepare(issuer,token,"bad%client",redirect,resource,result),"invalid client id");
        rejects(()->OAuthCodeExchange.prepare(issuer,token,"gho-public-test","http://garak.lexid.site/order/oauth/callback",resource,result),"HTTP redirect");
        rejects(()->OAuthCodeExchange.prepare(issuer,token,"gho-public-test",redirect,"http://api-stage.lexid.site",result),"HTTP resource");
        rejects(()->OAuthCodeExchange.prepare(issuer,token,"gho-public-test",redirect,resource,null),"null callback");
        OAuthCodeExchange.Token verified=OAuthCodeExchange.validatedToken("Bearer","eyJhbGciOiJFZERTQSJ9.eyJzdWIiOiJkZW1vIn0.signature",3600);
        ok(verified.expiresInSeconds()==3600,"token expiry");
        ok(verified.ephemeralBearer().startsWith("eyJ"),"token passed only by explicit method");
        ok(!verified.toString().contains("eyJ"),"redacted token string");
        rejects(()->OAuthCodeExchange.validatedToken("bearer","abc.def.ghi",3600),"token_type case enforced");
        rejects(()->OAuthCodeExchange.validatedToken("Basic","abc.def.ghi",3600),"token_type wrong");
        rejects(()->OAuthCodeExchange.validatedToken("Bearer","a\nbc.def.ghi",3600),"CR/LF forbidden");
        rejects(()->OAuthCodeExchange.validatedToken("Bearer","abc.def.ghi",0),"expired token");
        rejects(()->OAuthCodeExchange.validatedToken("Bearer","abc.def.ghi",86401),"excess expiry");
        rejects(()->OAuthCodeExchange.validatedToken("Bearer","abc.def.ghi",-1),"negative expiry");
        rejects(()->OAuthCodeExchange.validatedToken("Bearer","x".repeat(17000),3600),"oversize access token");
        System.out.println("OAuth code exchange JVM contract: "+count+" checks passed");
    }
}
