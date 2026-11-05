package site.lexid.garakhansang.order;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.net.URLEncoder;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Strict, read-only HTTPS connector. Disabled by default. No account/order/payment data. */
public final class MobileApiClient {
    public interface Callback { void onResult(JSONObject data, String error); }
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final String baseUrl;
    private final String disabledReason;

    public MobileApiClient(Context context) {
        String url = "", reason = "API 연결이 비활성화되었습니다. 개발자 설정을 먼저 검증하세요.";
        try (InputStream input=context.getAssets().open("mobile_api_config.json")) {
            ByteArrayOutputStream buffer=new ByteArrayOutputStream();
            byte[] chunk=new byte[1024]; int n;
            while((n=input.read(chunk))!=-1){
                if(buffer.size()+n>8192)throw new IOException("설정 파일이 비정상적으로 큽니다.");
                buffer.write(chunk,0,n);
            }
            JSONObject conf=new JSONObject(buffer.toString("UTF-8"));
            if(conf.optBoolean("enabled",false)) {
                String requested=conf.optString("base_url","").trim();
                URI parsed=new URI(requested);
                JSONArray hosts=conf.optJSONArray("allowed_hosts");
                boolean allowed=false;
                if(hosts!=null)for(int i=0;i<hosts.length();i++){
                    if(parsed.getHost()!=null && parsed.getHost().equalsIgnoreCase(hosts.optString(i,"")))allowed=true;
                }
                if(!"https".equalsIgnoreCase(parsed.getScheme()) || parsed.getHost()==null
                    || parsed.getRawUserInfo()!=null || parsed.getRawQuery()!=null
                    || parsed.getRawFragment()!=null || parsed.getPort()>0 && parsed.getPort()!=443
                    || !allowed || parsed.getPath()!=null && !parsed.getPath().isEmpty()
                       && !"/".equals(parsed.getPath())) {
                    reason="허용된 HTTPS API 호스트 설정이 올바르지 않습니다.";
                } else {
                    url="https://"+parsed.getHost().toLowerCase(java.util.Locale.ROOT);
                    reason="";
                }
            }
        } catch (Exception ignored) { reason="API 보안 설정을 읽지 못했습니다."; }
        baseUrl=url;
        disabledReason=reason;
    }

    public boolean isEnabled(){return !baseUrl.isEmpty();}
    public String status(){return isEnabled()?"HTTPS 읽기 전용 연결 구성됨 · 서버 동작 미확인":disabledReason;}

    public void bootstrap(Callback callback){get("/api/v1/mobile/bootstrap",callback);}
    public void authStatus(Callback callback){get("/api/v1/mobile/auth/status",callback);}
    public void markets(Callback callback){get("/api/v1/mobile/markets",callback);}
    public void merchants(Callback callback){get("/api/v1/mobile/merchants",callback);}
    public void products(Callback callback){get("/api/v1/mobile/products",callback);}
    private boolean validMarketId(String marketId) {
        return marketId!=null && marketId.matches("[A-Za-z0-9_-]{1,60}");
    }
    private String encode(String text) {
        try {
            // URLEncoder.encode(String,Charset) is not available on all API 26 devices.
            return URLEncoder.encode(text, "UTF-8").replace("+", "%20");
        } catch (java.io.UnsupportedEncodingException impossible) {
            throw new IllegalStateException("UTF-8 not available");
        }
    }
    private void invalidQuery(Callback callback) {
        main.post(()->callback.onResult(null,"개발용 시장·매장 선택값이 올바르지 않습니다."));
    }
    /** Refuses arbitrary paths, URLs, and unvalidated market IDs. */
    public void merchants(String marketId, Callback callback) {
        if(!validMarketId(marketId)){invalidQuery(callback);return;}
        get("/api/v1/mobile/merchants?market_id="+encode(marketId),callback);
    }
    public void products(String marketId, String merchantName, Callback callback) {
        if(!validMarketId(marketId) || merchantName==null || merchantName.trim().isEmpty()
            || merchantName.length()>90 || merchantName.indexOf('\n')>=0 || merchantName.indexOf('\r')>=0){
            invalidQuery(callback);return;
        }
        get("/api/v1/mobile/products?market_id="+encode(marketId)+"&merchant_name="+encode(merchantName),callback);
    }
    public void serviceability(String postalCode, Callback callback){
        if(postalCode==null || !postalCode.matches("[0-9]{5}")){
            main.post(()->callback.onResult(null,"우편번호는 숫자 5자리로 입력하세요."));
            return;
        }
        get("/api/v1/mobile/serviceability?postal_code="+postalCode,callback);
    }

    /** Ephemeral Bearer-only readiness check. No token is saved or logged. */
    public void verifySession(String accessToken, Callback callback) {
        if (accessToken==null || accessToken.length()>12000
            || !accessToken.matches("[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+\\.[A-Za-z0-9_-]+")) {
            main.post(()->callback.onResult(null,"로그인이 필요합니다. 공개 시연 앱은 로그인 비활성화 상태입니다."));
            return;
        }
        get("/api/v1/mobile/auth/session",accessToken,callback);
    }
    private void get(String path, Callback callback){get(path,null,callback);}
    private void get(String path, String ephemeralBearer, Callback callback){
        if(!isEnabled()){
            main.post(()->callback.onResult(null,disabledReason)); return;
        }
        executor.execute(()->{
            JSONObject parsed=null; String error=null;
            HttpURLConnection connection=null;
            try {
                URL target=new URL(baseUrl+path);
                connection=(HttpURLConnection)target.openConnection();
                connection.setRequestMethod("GET");
                connection.setInstanceFollowRedirects(false);
                connection.setConnectTimeout(4500);
                connection.setReadTimeout(5000);
                connection.setUseCaches(false);
                connection.setRequestProperty("Accept","application/json");
                if(ephemeralBearer!=null)connection.setRequestProperty("Authorization","Bearer "+ephemeralBearer);
                int status=connection.getResponseCode();
                if(status!=200)throw new IOException("HTTP "+status+" · 서비스 API 이용 불가");
                String contentType=connection.getContentType();
                if(contentType==null || !contentType.toLowerCase(java.util.Locale.ROOT).contains("application/json"))
                    throw new IOException("JSON API 응답이 아닙니다.");
                try(InputStream input=connection.getInputStream()){
                    ByteArrayOutputStream buffer=new ByteArrayOutputStream();
                    byte[] chunk=new byte[4096]; int n;
                    while((n=input.read(chunk))!=-1){
                        if(buffer.size()+n>196608)throw new IOException("응답 크기가 제한을 초과했습니다.");
                        buffer.write(chunk,0,n);
                    }
                    JSONObject response=new JSONObject(buffer.toString(StandardCharsets.UTF_8.name()));
                    parsed=response.optJSONObject("data");
                    if(parsed==null)throw new IOException("모바일 API 응답 형식이 다릅니다.");
                }
            } catch(Exception e) {
                // Do not display URL, token, or raw exception message to the customer.
                error=e instanceof IOException && e.getMessage()!=null
                    && (e.getMessage().startsWith("HTTP ") || e.getMessage().startsWith("JSON ")
                    || e.getMessage().startsWith("응답 크기") || e.getMessage().startsWith("모바일 API"))
                    ? e.getMessage() : "HTTPS 서버에 연결할 수 없습니다. 연결 설정을 점검하세요.";
            } finally { if(connection!=null)connection.disconnect(); }
            final JSONObject safeData=parsed; final String safeError=error;
            main.post(()->callback.onResult(safeData,safeError));
        });
    }
    public void close(){executor.shutdownNow();}
}
