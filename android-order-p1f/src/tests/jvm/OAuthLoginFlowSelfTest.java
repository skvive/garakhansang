import site.lexid.garakhansang.order.OAuthLoginFlow;
import java.net.URI;
import java.net.URLDecoder;
import java.util.HashMap;
import java.util.Map;

public final class OAuthLoginFlowSelfTest {
    private static int checked=0;
    private static void ok(boolean good,String why){checked++;if(!good)throw new AssertionError(why);}
    private static void reject(Runnable fn,String why){checked++;try{fn.run();throw new AssertionError("accepted "+why);}catch(IllegalStateException|IllegalArgumentException expected){}}
    private static OAuthLoginFlow.VerifiedConfiguration conf(boolean link,boolean client,boolean auth){
        return new OAuthLoginFlow.VerifiedConfiguration("https://stage.example.com/neondb/auth",
            "https://stage.example.com/neondb/auth/oauth2/authorize",
            "https://stage.example.com/neondb/auth/oauth2/token", "public-client-123",
            "https://login.example.com/order/oauth/callback", "https://api.example.com/mobile",
            link,client,auth);
    }
    private static Map<String,String> query(String link) throws Exception {
        Map<String,String> out=new HashMap<>();
        for(String part:new URI(link).getRawQuery().split("&")){
            String[] kv=part.split("=",2);
            out.put(URLDecoder.decode(kv[0],"UTF-8"),URLDecoder.decode(kv[1],"UTF-8"));
        }
        return out;
    }
    private static String callback(String state){
        return "https://login.example.com/order/oauth/callback?state="+state+"&code=safe-auth-code";
    }
    public static void main(String...args) throws Exception {
        OAuthLoginFlow flow=new OAuthLoginFlow();
        ok(!flow.hasPendingRequest(),"initially no session");
        reject(()->flow.begin(null),"null config");
        reject(()->flow.begin(conf(false,true,true)),"unverified app link");
        reject(()->flow.begin(conf(true,false,true)),"unregistered client");
        reject(()->flow.begin(conf(true,true,false)),"auth unavailable");
        ok(!flow.hasPendingRequest(),"rejects without state");
        String start=flow.begin(conf(true,true,true));
        ok(start.contains("code_challenge_method=S256"),"S256 required");
        ok(flow.hasPendingRequest(),"pending");
        Map<String,String> params=query(start);
        ok(params.get("state")!=null && params.get("state").length()>=40,"strong state");
        reject(()->flow.consumeVerifiedCallback(callback("attacker")),"wrong state");
        ok(!flow.hasPendingRequest(),"wrong state consumed pending");
        reject(()->flow.consumeVerifiedCallback(callback(params.get("state"))),"replay after rejection");
        start=flow.begin(conf(true,true,true));
        Map<String,String> p2=query(start);
        reject(()->flow.consumeVerifiedCallback("http://login.example.com/order/oauth/callback?state="+p2.get("state")+"&code=x"),"http callback");
        ok(!flow.hasPendingRequest(),"unsafe scheme consumed");
        start=flow.begin(conf(true,true,true));
        Map<String,String> p3=query(start);
        String body=flow.consumeVerifiedCallback(callback(p3.get("state"))).formBody;
        ok(body.contains("grant_type=authorization_code"),"authorization-code only");
        ok(body.contains("code_verifier="),"PKCE verifier sent");
        ok(body.contains("client_id=public-client-123"),"public client only");
        ok(!body.contains("client_secret"),"no client secret");
        ok(!flow.hasPendingRequest(),"successful request consumed");
        reject(()->flow.consumeVerifiedCallback(callback(p3.get("state"))),"replay after success");
        start=flow.begin(conf(true,true,true));
        String cancelledState=query(start).get("state");
        flow.cancel();
        reject(()->flow.consumeVerifiedCallback(callback(cancelledState)),"cancel stops callback");
        ok(!flow.hasPendingRequest(),"cancellation cleared pending");
        System.out.println("OAuth P1E login coordinator: "+checked+" checks passed");
    }
}
