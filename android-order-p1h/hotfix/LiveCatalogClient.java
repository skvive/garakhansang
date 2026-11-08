package site.lexid.garakhansang.order;

import android.os.Handler;
import android.os.Looper;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;

/** Official approved products shared with garakmall.lexid.site.
 * No demo fallback and no buyer account, payments or personal information sent.
 */
public final class LiveCatalogClient {
    public static final String ENDPOINT = "https://garakmall.lexid.site/api/mobile/v1/catalog";
    private static final int LIMIT_BYTES=1024*1024;
    private final Handler main = new Handler(Looper.getMainLooper());
    private final AtomicBoolean loading = new AtomicBoolean(false);
    private volatile Snapshot last;
    private volatile String etag = "";

    public interface Callback { void finished(Snapshot snapshot, String error); }

    public static final class Item {
        public final String sku, merchant, name, description, category, imageUrl;
        public final int priceKrw, stock;
        Item(JSONObject o) throws JSONException {
            sku=o.getString("sku").trim();
            merchant=o.getString("merchant_name").trim();
            name=o.getString("name").trim();
            description=o.optString("description","");
            category=o.optString("category_name","");
            imageUrl=o.getString("image_url");
            priceKrw=o.getInt("price_krw");stock=o.getInt("stock");
            if(!sku.matches("[A-Za-z0-9_-]{3,100}")||sku.length()>100||
               name.length()>160||merchant.length()>100||name.isEmpty()||
               priceKrw<=0||stock<=0||!imageUrl.startsWith("https://")||
               !o.optBoolean("merchant_verified",false)||o.optBoolean("can_checkout",true))
                throw new JSONException("Invalid verified merchant product");
        }
    }

    public static final class Snapshot {
        public final List<Item> items;
        public final String revision;
        Snapshot(List<Item> products,String etag){
            items=Collections.unmodifiableList(new ArrayList<>(products));
            revision=etag;
        }
        Item find(String sku){
            for(Item item:items)if(item.sku.equals(sku))return item;
            return null;
        }
    }

    public static Snapshot parse(String json,String etag) throws JSONException {
        JSONObject o=new JSONObject(json);
        if(o.getInt("schema_version")!=1||
           !"verified_neon_release_ready".equals(o.getString("source"))||
           o.optBoolean("order_service_ready",true)||
           o.optBoolean("delivery_tracking_ready",true))
            throw new JSONException("Unexpected published source or live order state");
        JSONArray a=o.getJSONArray("items");
        if(a.length()>500)throw new JSONException("Too many items");
        ArrayList<Item> items=new ArrayList<>();
        Set<String> ids=new HashSet<>();
        for(int i=0;i<a.length();i++){
            Item p=new Item(a.getJSONObject(i));
            if(!ids.add(p.sku))throw new JSONException("Duplicate SKU");
            items.add(p);
        }
        return new Snapshot(items,etag);
    }

    public void refresh(Callback done){
        if(!loading.compareAndSet(false,true))return;
        new Thread(()->{
            Snapshot result=null;
            String message=null;
            HttpURLConnection connection=null;
            try{
                URL url=new URL(ENDPOINT);
                if(!"https".equals(url.getProtocol()))throw new Exception("HTTPS required");
                connection=(HttpURLConnection)url.openConnection();
                connection.setConnectTimeout(7000);
                connection.setReadTimeout(9000);
                connection.setInstanceFollowRedirects(false);
                connection.setUseCaches(false);
                connection.setRequestProperty("Accept","application/json");
                connection.setRequestProperty("Cache-Control","no-store");
                Snapshot known=last;
                if(known!=null && !etag.isEmpty())connection.setRequestProperty("If-None-Match",etag);
                int status=connection.getResponseCode();
                if(status==304 && known!=null) result=known;
                else if(status==200){
                    try(InputStream in=connection.getInputStream();
                        ByteArrayOutputStream bytes=new ByteArrayOutputStream()){
                        byte[] block=new byte[8192];int n;
                        while((n=in.read(block))!=-1){
                            if(bytes.size()+n>LIMIT_BYTES)throw new Exception("Catalog response too large");
                            bytes.write(block,0,n);
                        }
                        result=parse(new String(bytes.toByteArray(),StandardCharsets.UTF_8),
                                     connection.getHeaderField("ETag"));
                        etag=result.revision==null?"":result.revision;
                    }
                }else throw new Exception("Catalog service status "+status);
            }catch(Exception error){
                // Offline/error: never present a stale price or unapproved item as live.
                last=null;etag="";
                message="공식 상품 동기화에 실패했습니다. 네트워크 또는 서버 설정을 확인해 주세요.";
            }finally{
                if(connection!=null)connection.disconnect();
                if(message==null && result!=null)last=result;
                loading.set(false);
                final Snapshot immutable=result;
                final String err=message;
                main.post(()->{if(done!=null)done.finished(immutable,err);});
            }
        },"garak-verified-catalog").start();
    }
    public Snapshot latest(){return last;}
}
