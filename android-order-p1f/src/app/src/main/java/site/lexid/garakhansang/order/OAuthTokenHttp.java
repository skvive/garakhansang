package site.lexid.garakhansang.order;

import android.os.Handler;
import android.os.Looper;
import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import javax.net.ssl.HttpsURLConnection;

/**
 * Dormant HTTPS token exchange transport. Never invoked by the v1.8 UI.
 *
 * Only after OAuth server, public client and Android Verified App Link are
 * configured should a coordinator exchange a one-time OAuthPkce.Result.
 * No refresh tokens, cookies, client secrets or persistent sessions.
 */
public final class OAuthTokenHttp {
    public interface Callback { void completed(OAuthCodeExchange.Token token, String safeError); }
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    public void exchange(OAuthCodeExchange.Request request, Callback callback) {
        executor.execute(()->{
            OAuthCodeExchange.Token token=null;
            String error="인증 서버 검증이 완료되지 않았습니다.";
            HttpsURLConnection connection=null;
            try {
                URL endpoint=new URL(request.tokenEndpoint);
                if (!"https".equalsIgnoreCase(endpoint.getProtocol())) throw new IOException("TLS required");
                connection=(HttpsURLConnection)endpoint.openConnection();
                connection.setInstanceFollowRedirects(false);
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(5000);
                connection.setReadTimeout(5000);
                connection.setUseCaches(false);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type","application/x-www-form-urlencoded; charset=UTF-8");
                connection.setRequestProperty("Accept","application/json");
                connection.setRequestProperty("Cache-Control","no-store");
                byte[] form=request.formBody.getBytes(StandardCharsets.UTF_8);
                connection.setFixedLengthStreamingMode(form.length);
                try(OutputStream output=connection.getOutputStream()){output.write(form);}
                if(connection.getResponseCode()!=200)throw new IOException("OAuth token endpoint rejected request");
                String type=connection.getContentType();
                if(type==null || !type.toLowerCase(Locale.ROOT).startsWith("application/json"))
                    throw new IOException("Unexpected OAuth token format");
                try(InputStream input=connection.getInputStream()){
                    ByteArrayOutputStream bytes=new ByteArrayOutputStream();
                    byte[] chunk=new byte[2048];int n;
                    while((n=input.read(chunk))!=-1){
                        if(bytes.size()+n>16384)throw new IOException("OAuth token payload too large");
                        bytes.write(chunk,0,n);
                    }
                    JSONObject reply=new JSONObject(bytes.toString(StandardCharsets.UTF_8.name()));
                    token=OAuthCodeExchange.validatedToken(reply.optString("token_type",""),
                        reply.optString("access_token",""),reply.optLong("expires_in",0));
                }
                error=null;
            } catch(Exception ignored) {
                // Never return endpoint URL, auth code, verifier, token or JSON to UI/logs.
                error="인증 요청에 실패했습니다. 다시 로그인하세요.";
            } finally {if(connection!=null)connection.disconnect();}
            OAuthCodeExchange.Token safeToken=token;
            String safeError=error;
            main.post(()->callback.completed(safeToken,safeError));
        });
    }
    public void close(){executor.shutdownNow();}
}
