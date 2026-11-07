package site.lexid.garakhansang.order;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.os.Build;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.util.LruCache;
import java.io.InputStream;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.content.SharedPreferences;
import android.content.res.Configuration;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.inputmethod.InputMethodManager;
import android.content.Context;
import android.widget.*;
import android.text.InputFilter;
import android.text.InputType;
import org.json.JSONArray;
import org.json.JSONObject;
import java.util.*;

/** Offline native ordering demo: no checkout, no payment, no external data collection. */
public class MainActivity extends Activity {
    private static final int RED = 0xFFCA1020, INK = 0xFF2D211F, CREAM = 0xFFFFF7EC,
            MUTED = 0xFF7A6660, GREEN = 0xFF49753D, WHITE = Color.WHITE, LINE = 0xFFF0E5DD;
    // Source: original 47 menu/price rows supplied by the operator; all catalog entries are demo-only.
    private final String[] kinds = {
        "전체",
        "오늘의 한상",
        "회·모둠",
        "사이드",
        "광양수산 인기",
        "광양수산 1인 회",
        "광양수산 프리미엄 회",
        "광양수산 겨울 방어",
        "광양수산 제철 회",
        "광양수산 여름 제철",
        "광양수산 갑각류",
        "광양수산 계절 해산물",
        "광양수산 추가 메뉴"
    };
    private final String[] names = {
        "오늘의 한상 (1인)",
        "오늘의 한상 (2인)",
        "오늘의 반상",
        "모둠회 소 (2~3인)",
        "모둠회 중 (3~4인)",
        "광어회 (2인)",
        "연어회 (2인)",
        "매운탕 (2인)",
        "공기밥",
        "콜라/사이다 355ml",
        "프리미엄(특수부위) 활모듬회",
        "활새우회(손질 O) + 찍먹 소스",
        "1인 모듬회(4~5구성)",
        "(1인) 들깨전어회",
        "(1인) 대광어회",
        "(1인) 연어회",
        "(1인) 세꼬시회(도다리)",
        "(1인) 광어참돔회",
        "(1인) 광어우럭회",
        "(1인) 광어연어회",
        "자연산 대농어(2인분)",
        "최고급 생참치회(스페인)",
        "생참치 트리오회",
        "생참치 활모듬회",
        "생물의 끝 - 시그니처모듬회",
        "조합의 끝 - 오마카세",
        "지구방어회(특대방어)",
        "지구방어생참치회(지구방어·생참치)",
        "지구방어모듬회",
        "지구방광참회(방어·광어·참돔)",
        "지구방어삼색회(방어·광어·참돔·연어)",
        "지구방광우회(방어·광어·우럭)",
        "지구방광연회(방어·광어·연어)",
        "들깨전어회",
        "들깨전어모듬회",
        "들기름 깻잎 막회(무침)",
        "줄무늬전갱이회(시마아지)",
        "줄무늬전갱이모듬회",
        "줄무늬전갱이삼색회",
        "꽃게탕용 밀키트",
        "서해산 가을 활암꽃게(특대)",
        "치즈폭탄 갈릭마요 꽃게찜(특대)",
        "A급 러시아 프리모리 대게(마리당)",
        "A급 러시아 레드킹크랩(마리당)",
        "활새우(손질 X)",
        "쥐치 1kg(2인분)",
        "연어 타르타르 소스"
    };
    private final String[] units = {
        "오늘의 한상 · AI 메뉴 시안",
        "오늘의 한상 · AI 메뉴 시안",
        "오늘의 한상 · AI 메뉴 시안",
        "회·모둠 · AI 메뉴 시안",
        "회·모둠 · AI 메뉴 시안",
        "회·모둠 · AI 메뉴 시안",
        "회·모둠 · AI 메뉴 시안",
        "사이드 · AI 메뉴 시안",
        "사이드 · AI 메뉴 시안",
        "사이드 · AI 메뉴 시안",
        "광양수산 인기 · AI 메뉴 시안",
        "광양수산 인기 · AI 메뉴 시안",
        "광양수산 1인 회 · AI 메뉴 시안",
        "광양수산 1인 회 · AI 메뉴 시안",
        "광양수산 1인 회 · AI 메뉴 시안",
        "광양수산 1인 회 · AI 메뉴 시안",
        "광양수산 1인 회 · AI 메뉴 시안",
        "광양수산 1인 회 · AI 메뉴 시안",
        "광양수산 1인 회 · AI 메뉴 시안",
        "광양수산 1인 회 · AI 메뉴 시안",
        "광양수산 프리미엄 회 · AI 메뉴 시안",
        "광양수산 프리미엄 회 · AI 메뉴 시안",
        "광양수산 프리미엄 회 · AI 메뉴 시안",
        "광양수산 프리미엄 회 · AI 메뉴 시안",
        "광양수산 프리미엄 회 · AI 메뉴 시안",
        "광양수산 프리미엄 회 · AI 메뉴 시안",
        "광양수산 겨울 방어 · AI 메뉴 시안",
        "광양수산 겨울 방어 · AI 메뉴 시안",
        "광양수산 겨울 방어 · AI 메뉴 시안",
        "광양수산 겨울 방어 · AI 메뉴 시안",
        "광양수산 겨울 방어 · AI 메뉴 시안",
        "광양수산 겨울 방어 · AI 메뉴 시안",
        "광양수산 겨울 방어 · AI 메뉴 시안",
        "광양수산 제철 회 · AI 메뉴 시안",
        "광양수산 제철 회 · AI 메뉴 시안",
        "광양수산 제철 회 · AI 메뉴 시안",
        "광양수산 여름 제철 · AI 메뉴 시안",
        "광양수산 여름 제철 · AI 메뉴 시안",
        "광양수산 여름 제철 · AI 메뉴 시안",
        "광양수산 갑각류 · AI 메뉴 시안",
        "광양수산 갑각류 · AI 메뉴 시안",
        "광양수산 갑각류 · AI 메뉴 시안",
        "광양수산 갑각류 · AI 메뉴 시안",
        "광양수산 갑각류 · AI 메뉴 시안",
        "광양수산 계절 해산물 · AI 메뉴 시안",
        "광양수산 계절 해산물 · AI 메뉴 시안",
        "광양수산 추가 메뉴 · AI 메뉴 시안"
    };
    private final String[] descriptions = {
        "가락시장에서 당일 들어온 신선한 모둠회에 밥·국·반찬을 함께 담은 1인 한상입니다.",
        "가락시장에서 당일 들어온 신선한 모둠회 2인분에 밥·국·반찬을 함께 담았습니다.",
        "당일 시세 생선회 소 구성에 밥·국·반찬을 함께 담은 가성비 반상입니다.",
        "광어·우럭 등 당일 시세 활어로 구성한 모둠회 2~3인분입니다.",
        "활어와 선어를 고루 담은 푸짐한 모둠회 3~4인분입니다.",
        "가락시장 직송 활광어를 바로 썰어 담은 2인분 회입니다.",
        "부드럽고 고소한 노르웨이산 연어를 두툼하게 썬 2인분 회입니다.",
        "생선 뼈와 머리를 우려낸 칼칼한 매운탕 2인분입니다.",
        "",
        "",
        "특수부위 포함 활모듬회",
        "손질된 활새우와 소스",
        "초장·간장·막장·락교·초생강 구성",
        "들깨와 전어를 함께 즐기는 1인 회",
        "초장·간장·막장·락교·초생강 구성",
        "허브 숙성 연어 · 포장·소스 구성",
        "도다리 세꼬시 단품 구성",
        "광어·참돔 혼합",
        "광어·우럭 혼합",
        "광어·연어 혼합",
        "자연산 농어 2인 구성",
        "스페인산 생참치 단품 구성",
        "생참치와 다양한 부위를 곁들인 구성",
        "생참치와 활어 구성",
        "다양한 횟감으로 구성한 시그니처 메뉴",
        "여러 어종을 조합한 모둠회",
        "겨울 방어 특대급 회",
        "방어와 생참치 혼합 구성",
        "방어와 다양한 어종 혼합",
        "방어·광어·참돔 모둠",
        "캡처 표기명은 삼색회이나 4종 구성",
        "방어·광어·우럭 모둠",
        "방어·광어·연어 모둠",
        "제철 전어와 들깨 향을 더한 메뉴",
        "전어와 다른 어종을 함께 구성",
        "깻잎과 특제 소스를 곁들인 막회",
        "줄무늬전갱이 단품 회",
        "줄무늬전갱이·광어·참돔·숭어·연어 구성",
        "줄무늬전갱이와 여러 어종 혼합 구성",
        "꽃게 3마리·탕용 야채·양념장·조개 구성",
        "가을 활암꽃게 특대",
        "갈릭마요 소스와 치즈를 곁들인 꽃게찜",
        "1~1.2kg / 살수율 조건 당시 캡처 기재",
        "살수율 90% 이상 표기",
        "손질하지 않은 활새우",
        "1kg 기준 2인분 쥐치회",
        "곁들임 소스"
    };
    private final String[] catalogCategories = {
        "오늘의 한상",
        "오늘의 한상",
        "오늘의 한상",
        "회·모둠",
        "회·모둠",
        "회·모둠",
        "회·모둠",
        "사이드",
        "사이드",
        "사이드",
        "광양수산 인기",
        "광양수산 인기",
        "광양수산 1인 회",
        "광양수산 1인 회",
        "광양수산 1인 회",
        "광양수산 1인 회",
        "광양수산 1인 회",
        "광양수산 1인 회",
        "광양수산 1인 회",
        "광양수산 1인 회",
        "광양수산 프리미엄 회",
        "광양수산 프리미엄 회",
        "광양수산 프리미엄 회",
        "광양수산 프리미엄 회",
        "광양수산 프리미엄 회",
        "광양수산 프리미엄 회",
        "광양수산 겨울 방어",
        "광양수산 겨울 방어",
        "광양수산 겨울 방어",
        "광양수산 겨울 방어",
        "광양수산 겨울 방어",
        "광양수산 겨울 방어",
        "광양수산 겨울 방어",
        "광양수산 제철 회",
        "광양수산 제철 회",
        "광양수산 제철 회",
        "광양수산 여름 제철",
        "광양수산 여름 제철",
        "광양수산 여름 제철",
        "광양수산 갑각류",
        "광양수산 갑각류",
        "광양수산 갑각류",
        "광양수산 갑각류",
        "광양수산 갑각류",
        "광양수산 계절 해산물",
        "광양수산 계절 해산물",
        "광양수산 추가 메뉴"
    };
    private final int[] prices = {
        19900, 36900, 13900, 39900, 59900, 32900, 29900, 12900, 1000, 2000, 65000, 35000, 43000, 38000, 43000, 39000, 39000, 45000, 45000, 43000, 65000, 85000, 83000, 80000, 95000, 95000, 80000, 85000, 80000, 80000, 80000, 80000, 80000, 49000, 69000, 34000, 90000, 82000, 85000, 65000, 65000, 75000, 122000, 378000, 30000, 75000, 1000
    };
    // No real address, payment, or service area data is collected in this offline demonstration.
    private static final String[] DEMO_AREAS = {
        "가락시장 주변 (예시)", "송파구 (예시)", "강남구 (예시)"
    };
    private String page="home", category="전체", query="";
    private int selectedProduct=-1, detailQuantity=1;
    private String demoArea=DEMO_AREAS[0], fulfillment="배달";
    private final Set<Integer> favorites = new HashSet<>();
    private int[] cart = new int[names.length];
    private LinearLayout app, content;
    private SharedPreferences prefs;
    private MobileApiClient mobileApi;
    private String selectedRemoteMarketId="", selectedRemoteMarketName="";
    private String selectedRemoteMerchantName="";
    private JSONObject selectedRemoteProduct;
    private int remoteRequestSerial=0;
    private int addressRequestSerial=0, authRequestSerial=0, apiRequestSerial=0;
    // Bounded thumbnail cache avoids decoding 47 full-resolution images on each navigation.
    private final LruCache<String,Bitmap> thumbnails=new LruCache<String,Bitmap>(12*1024){
        @Override protected int sizeOf(String key, Bitmap bitmap){
            return Math.max(1,bitmap.getByteCount()/1024);
        }
    };

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(RED);
        getWindow().setNavigationBarColor(CREAM);
        // Request light status icons only after the decor view is attached.
        // PhoneWindow.getInsetsController() can throw in onCreate on Android 15.
        if (Build.VERSION.SDK_INT >= 35) {
            View decor = getWindow().getDecorView();
            decor.post(() -> {
                // Insets are visual polish, not a prerequisite for app startup.
                // Older devices can detach the decor during a quick relaunch.
                if (isFinishing() || isDestroyed() || !decor.isAttachedToWindow()) return;
                try {
                    WindowInsetsController controller = decor.getWindowInsetsController();
                    if (controller != null) controller.setSystemBarsAppearance(
                        WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS,
                        WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS);
                } catch (RuntimeException ignored) {
                    // Never crash the ordering UI just to style system bar icons.
                }
            });
        }
        prefs = getSharedPreferences("order_preview",MODE_PRIVATE);
        mobileApi = new MobileApiClient(this);
        for (int i=0;i<cart.length;i++) {
            cart[i]=Math.max(0,Math.min(99,previewInt("q"+i,0)));
            if (previewBoolean("fav"+i,false)) favorites.add(i);
        }
        int savedArea = previewInt("demo_area_index",0);
        demoArea=DEMO_AREAS[Math.max(0,Math.min(DEMO_AREAS.length-1,savedArea))];
        fulfillment="포장".equals(previewString("fulfillment","배달")) ? "포장" : "배달";
        if (b != null) {
            page=nonBlankOr(b.getString("page"),"home");
            category=nonBlankOr(b.getString("category"),"전체");
            query=b.getString("query") == null ? "" : b.getString("query");
            selectedProduct=Math.max(-1,Math.min(names.length-1,b.getInt("selectedProduct",-1)));
            detailQuantity=Math.max(1,Math.min(99,b.getInt("detailQuantity",1)));
        }
        render();
    }
    // Previous demo builds may have persisted values with different types. Keep
    // valid preferences and ignore only incompatible individual entries.
    private int previewInt(String key,int fallback){
        try { return prefs.getInt(key,fallback); }
        catch (ClassCastException ignored) { return fallback; }
    }
    private boolean previewBoolean(String key,boolean fallback){
        try { return prefs.getBoolean(key,fallback); }
        catch (ClassCastException ignored) { return fallback; }
    }
    private String previewString(String key,String fallback){
        try { return prefs.getString(key,fallback); }
        catch (ClassCastException ignored) { return fallback; }
    }
    private String nonBlankOr(String value,String fallback){
        return value==null || value.trim().isEmpty() ? fallback : value;
    }
    private int d(float n){return Math.round(getResources().getDisplayMetrics().density*n);}
    private GradientDrawable shape(int fill,int rad){GradientDrawable g=new GradientDrawable();g.setColor(fill);g.setCornerRadius(d(rad));return g;}
    private GradientDrawable bordered(int fill,int border,int rad){GradientDrawable g=shape(fill,rad);g.setStroke(d(1),border);return g;}
    private TextView text(String s,int sp,int color,boolean bold){TextView t=new TextView(this);t.setText(s);t.setTextSize(sp);t.setTextColor(color);t.setGravity(Gravity.CENTER_VERTICAL);if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);t.setIncludeFontPadding(true);return t;}
    private LinearLayout column(){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);return l;}
    private LinearLayout row(){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.HORIZONTAL);l.setGravity(Gravity.CENTER_VERTICAL);return l;}
    private LinearLayout.LayoutParams lp(int w,int h){return new LinearLayout.LayoutParams(w<0?w:d(w),h<0?h:d(h));}
    private void gap(LinearLayout l,int size){View v=new View(this);l.addView(v,lp(1,size));}
    private void sideMargins(View v,int start,int top,int end,int bottom){LinearLayout.LayoutParams p=(LinearLayout.LayoutParams)v.getLayoutParams();p.setMargins(d(start),d(top),d(end),d(bottom));v.setLayoutParams(p);}
    private ImageView photo(String file,int width,int height){
        ImageView im=new ImageView(this);
        String asset=file.endsWith(".jpg")?file:file+".webp";
        try {
            Bitmap bitmap=thumbnails.get(asset);
            if(bitmap==null){
                BitmapFactory.Options bounds=new BitmapFactory.Options();
                bounds.inJustDecodeBounds=true;
                try(InputStream in=getAssets().open(asset)){BitmapFactory.decodeStream(in,null,bounds);}
                int requested=Math.max(d(160),d(Math.max(width,height)));
                int sample=1;
                while(bounds.outWidth/(sample*2)>=requested && bounds.outHeight/(sample*2)>=requested)sample*=2;
                BitmapFactory.Options decode=new BitmapFactory.Options();
                decode.inSampleSize=sample;
                try(InputStream in=getAssets().open(asset)){bitmap=BitmapFactory.decodeStream(in,null,decode);}
                if(bitmap!=null)thumbnails.put(asset,bitmap);
            }
            if(bitmap!=null)im.setImageBitmap(bitmap);
        } catch(Exception ignored) {/* Android displays neutral placeholder if an asset is unavailable. */}
        im.setScaleType(ImageView.ScaleType.CENTER_CROP);
        im.setBackground(shape(LINE,12));
        im.setClipToOutline(true);
        im.setLayoutParams(lp(width,height));
        im.setContentDescription(file.startsWith("menu_")?"AI 생성 메뉴 참고 이미지":"브랜드 참고 이미지");
        return im;
    }
    private TextView pill(String label,boolean active,Runnable onClick){
        Button b=new Button(this);
        b.setText(label);b.setAllCaps(false);b.setTextSize(13);
        b.setTextColor(active?WHITE:INK);b.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        b.setGravity(Gravity.CENTER);b.setPadding(d(14),0,d(14),0);
        b.setBackground(shape(active?RED:0xFFF6EDE5,28));
        b.setMinWidth(d(48));b.setMinHeight(d(48));b.setOnClickListener(v->onClick.run());return b;
    }
    private TextView button(String label,int color,Runnable click){
        Button b=new Button(this);
        b.setText(label);b.setAllCaps(false);b.setTextSize(15);
        b.setTextColor(WHITE);b.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        b.setGravity(Gravity.CENTER);b.setPadding(d(12),0,d(12),0);
        b.setBackground(shape(color,14));b.setMinHeight(d(48));
        b.setOnClickListener(v->click.run());return b;
    }
    private int count(){int c=0;for(int n:cart)c+=n;return c;}
    private long cartTotal(){long sum=0;for(int i=0;i<cart.length;i++)sum+=(long)cart[i]*prices[i];return sum;}
    private String won(long price){return String.format(java.util.Locale.KOREA,"%,d원",price);}

    @Override protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state);
        state.putString("page",page);
        state.putString("category",category);
        state.putString("query",query);
        state.putInt("selectedProduct",selectedProduct);
        state.putInt("detailQuantity",detailQuantity);
    }
    private void save(){SharedPreferences.Editor e=prefs.edit();for(int i=0;i<cart.length;i++)e.putInt("q"+i,cart[i]);e.apply();}
    private void toggleFavorite(int i) {
        if (!favorites.add(i)) favorites.remove(i);
        prefs.edit().putBoolean("fav"+i,favorites.contains(i)).apply();
        render();
    }
    private void chooseDemoArea() {
        new AlertDialog.Builder(this).setTitle("시연 지역 · 주소/GPS 수집 없음")
            .setSingleChoiceItems(DEMO_AREAS, Arrays.asList(DEMO_AREAS).indexOf(demoArea),
                (dialog,which)->{
                    demoArea=DEMO_AREAS[which];
                    prefs.edit().putInt("demo_area_index",which).apply();
                    dialog.dismiss(); render();
                }).setNegativeButton("취소",null).show();
    }
    private void chooseFulfillment(String value) {
        fulfillment=value;
        prefs.edit().putString("fulfillment",fulfillment).apply();
        render();
    }
    private void open(String p){page=p;render();}
    private void render(){
        // Every navigation invalidates replies belonging to detached views.
        ++remoteRequestSerial; ++addressRequestSerial; ++authRequestSerial; ++apiRequestSerial;
        app=column();app.setBackgroundColor(CREAM);setContentView(app);
        // Android 15+ enforces edge-to-edge for target SDK 35+. Respect system bars
        // so the cart button and navigation labels do not overlap system UI.
        if (Build.VERSION.SDK_INT >= 35) {
            app.setOnApplyWindowInsetsListener((view, insets) -> {
                android.graphics.Insets bars = insets.getInsets(
                    WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                view.setPadding(0, bars.top, 0, bars.bottom);
                return insets;
            });
            app.requestApplyInsets();
        }
        header();
        ScrollView sc=new ScrollView(this);sc.setFillViewport(true);sc.setVerticalScrollBarEnabled(false);
        app.addView(sc,new LinearLayout.LayoutParams(-1,0,1));
        content=column();content.setPadding(d(18),d(15),d(18),d(20));sc.addView(content);
        switch(page){
            case "products": products(); break;
            case "store": store(); break;
            case "cart": cart(); break;
            case "product_detail": productDetail(); break;
            case "remote_product_detail": remoteProductDetail(); break;
            case "checkout": checkoutPreview(); break;
            case "orders": orders(); break;
            case "favorites": favoritesPage(); break;
            case "my": myPage(); break;
            case "info": info(); break;
            case "address": addressPage(); break;
            case "api": apiPage(); break;
            case "auth_preview": authPreviewPage(); break;
            case "remote_catalog": remoteCatalogPage(); break;
            default: home();
        }
        footer();
    }
    private void header(){
        LinearLayout bar=row();bar.setPadding(d(18),d(8),d(18),d(8));bar.setBackgroundColor(WHITE);app.addView(bar,lp(-1,64));
        ImageView icon=photo("order_brand_512",48,48);bar.addView(icon);icon.setOnClickListener(v->open("home"));
        LinearLayout labels=column();labels.setPadding(d(10),0,0,0);bar.addView(labels,new LinearLayout.LayoutParams(0,-2,1));
        labels.addView(text("가락한상 오더",20,INK,true));labels.addView(text("시장에서 식탁까지, 간편하게",11,MUTED,false));
        TextView bag=pill("장바구니 "+count(),true,()->open("cart"));bar.addView(bag,lp(-2,48));
        LinearLayout location=row();location.setPadding(d(18),d(7),d(18),d(8));
        location.setBackgroundColor(WHITE);app.addView(location,lp(-1,52));
        LinearLayout block=column();location.addView(block,new LinearLayout.LayoutParams(0,-2,1));
        block.addView(text("시연 지역 · "+demoArea+"  ▾",13,INK,true));
        block.addView(text("개발용 예시 지역 / 배달 가능 여부 미확인",11,MUTED,false));
        location.setOnClickListener(v->chooseDemoArea());
        TextView test=text("DEMO",11,WHITE,true);test.setPadding(d(10),d(6),d(10),d(6));
        test.setBackground(shape(0xFF6B514B,9));location.addView(test);
    }
    private void footer(){
        LinearLayout bar=row();bar.setPadding(d(10),d(5),d(10),d(8));bar.setBackground(bordered(WHITE,LINE,0));app.addView(bar,lp(-1,66));
        String[][] nav={{"⌂","홈","home"},{"▦","메뉴","products"},{"▤","장바구니","cart"},{"☷","주문내역","orders"},{"◉","마이","my"}};
        for(String[] item:nav){LinearLayout segment=column();segment.setGravity(Gravity.CENTER);TextView ico=text(item[0],22,page.equals(item[2])?RED:MUTED,true);ico.setGravity(Gravity.CENTER);segment.addView(ico);TextView t=text(item[1],11,page.equals(item[2])?RED:MUTED,true);t.setGravity(Gravity.CENTER);segment.addView(t);bar.addView(segment,new LinearLayout.LayoutParams(0,-1,1));segment.setContentDescription(item[1]+" 탭");segment.setFocusable(true);segment.setOnClickListener(v->open(item[2]));}
    }
    private void section(String title,String sub){TextView h=text(title,22,INK,true);content.addView(h,lp(-1,34));if(sub!=null){TextView s=text(sub,13,MUTED,false);s.setLineSpacing(d(2),1);content.addView(s,lp(-1,-2));}gap(content,14);}
    private void home(){
        fulfillmentChooser();
        gap(content,15);
        LinearLayout hero=column();hero.setPadding(d(17),d(15),d(17),d(18));hero.setBackground(shape(RED,20));content.addView(hero,lp(-1,-2));
        TextView badge=text("가락시장 한상차림",12,0xFFFFD8B8,true);hero.addView(badge);
        TextView h=text("오늘도 신선하게,\n가락한상 오더",28,WHITE,true);hero.addView(h);gap(hero,8);
        hero.addView(text("47개 상품 · 판매 승인 전 시연 카탈로그",14,WHITE,false));gap(hero,14);
        LinearLayout bar=row();hero.addView(bar,lp(-1,118));ImageView food=photo("food",-1,118);bar.addView(food,new LinearLayout.LayoutParams(-1,-1));
        gap(content,16);
        section("시장·매장 둘러보기","실제 입점 인증 및 배달 권역은 연결 전입니다");
        merchantCard();
        gap(content,10);
        content.addView(button("연결된 시장·매장 둘러보기 · 개발 P1",GREEN,()->open("remote_catalog")),lp(-1,49));
        gap(content,18);
        section("어떤 메뉴를 찾으세요?","가락한상 오더 47종 메뉴를 둘러보세요");
        LinearLayout cats=row();content.addView(cats,lp(-1,150));String[] tags={"오늘의 한상","회·모둠","광양수산 인기"};String[] files={"menu_01.jpg","menu_04.jpg","menu_11.jpg"};
        for(int i=0;i<3;i++){final String kind=tags[i];LinearLayout card=column();card.setPadding(d(4),d(4),d(4),d(4));cats.addView(card,new LinearLayout.LayoutParams(0,-1,1));ImageView ph=photo(files[i],-1,100);card.addView(ph,new LinearLayout.LayoutParams(-1,d(100)));TextView title=text(tags[i],15,INK,true);title.setGravity(Gravity.CENTER);card.addView(title,lp(-1,30));card.setOnClickListener(v->{category=kind;query="";open("products");});}
        gap(content,24);section("가락한상 추천", "AI 이미지 시안 · 운영가격 및 실제 구성 확인 필요");
        for(int i:new int[]{0,3,6}) addProduct(i);
        gap(content,14);TextView order=button("장바구니 확인  ·  "+count()+"개",RED,()->open("cart"));content.addView(order,lp(-1,52));
    }
    private void fulfillmentChooser(){
        LinearLayout selector=row(); selector.setPadding(d(4),d(4),d(4),d(4));
        selector.setBackground(bordered(WHITE,LINE,16));content.addView(selector,lp(-1,52));
        for(String choice:new String[]{"배달","포장"}) {
            TextView t=pill(choice.equals("배달")?"🛵 배달 보기":"▣ 포장 보기",fulfillment.equals(choice),()->chooseFulfillment(choice));
            selector.addView(t,new LinearLayout.LayoutParams(0,-1,1));
        }
        TextView note=text("* "+fulfillment+" 선택은 화면 시연이며, 실제 접수·배달료 안내가 아닙니다.",11,MUTED,false);
        content.addView(note,lp(-1,-2));
    }
    private void merchantCard(){
        LinearLayout card=row();card.setPadding(d(10),d(10),d(10),d(10));
        card.setBackground(bordered(WHITE,LINE,18));content.addView(card,lp(-1,116));
        card.addView(photo("seafood",96,96));
        LinearLayout body=column();body.setPadding(d(13),0,0,0);
        card.addView(body,new LinearLayout.LayoutParams(0,-2,1));
        body.addView(text("광양수산 · 메뉴 시연",18,INK,true));
        body.addView(text("47개 참고 메뉴 · 12개 세부 분류",12,MUTED,false));
        body.addView(text("입점 미검증 · 영업시간/배달료 미연동",11,RED,true));
        card.setOnClickListener(v->open("store"));
        card.setContentDescription("광양수산 시연 매장 메뉴 보기");
    }
    private void store(){
        section("광양수산 · 시연 매장","실제 계약된 입점 매장 또는 현재 영업 중인 매장임을 의미하지 않습니다.");
        ImageView cover=photo("seafood",-1,172);content.addView(cover,lp(-1,172));gap(content,12);
        content.addView(text("수산·회 메뉴 시연  ·  47종 카탈로그",18,INK,true));
        content.addView(text("배송 가능 지역, 영업시간, 최소주문, 배달비, 원산지·알레르기 정보는 운영 서버 검증 후 제공됩니다.",13,MUTED,false));
        gap(content,16);
        content.addView(button("메뉴 47종 보기",RED,()->{category="전체";open("products");}),lp(-1,52));
        gap(content,8);content.addView(button("장바구니 보기",GREEN,()->open("cart")),lp(-1,48));
    }
    private void categoryBar(){HorizontalScrollView hs=new HorizontalScrollView(this);hs.setHorizontalScrollBarEnabled(false);LinearLayout row=row();hs.addView(row);for(String kind:kinds){TextView b=pill(kind,category.equals(kind),()->{if(!category.equals(kind))query="";category=kind;render();});row.addView(b,lp(-2,48));sideMargins(b,0,0,8,0);}content.addView(hs,lp(-1,52));gap(content,15);}
    private void products(){section("상품 탐색","47개 메뉴 표시 · 가격은 제공된 목록 기준 · 실주문 불가");categoryBar();
        EditText search=new EditText(this);search.setSingleLine(true);search.setHint("상품명 검색");search.setTextSize(15);search.setPadding(d(14),d(8),d(14),d(8));search.setBackground(bordered(WHITE,LINE,14));search.setFilters(new InputFilter[]{new InputFilter.LengthFilter(80)});search.setText(query);content.addView(search,lp(-1,48));gap(content,13);
        LinearLayout results=column();content.addView(results,lp(-1,-2));renderResults(results);
        search.addTextChangedListener(new TextWatcher(){public void beforeTextChanged(CharSequence s,int st,int c,int a){}public void onTextChanged(CharSequence s,int st,int before,int count){query=s.toString();renderResults(results);}public void afterTextChanged(Editable e){}});
    }
    private void renderResults(LinearLayout l){l.removeAllViews();int found=0;for(int i=0;i<names.length;i++)if(CatalogFilters.matches(category,catalogCategories[i],names[i],descriptions[i],query)){addProductInto(i,l);found++;}if(found==0){
        l.addView(text("검색 결과가 없습니다. 검색어 또는 분류를 변경하세요.",15,MUTED,false),lp(-1,60));
        l.addView(button("전체 상품 다시 보기",GREEN,()->{category="전체";query="";render();}),lp(-1,48));
    }}
    private void addProduct(int i){addProductInto(i,content);}
    private void addProductInto(int i,LinearLayout root){
        LinearLayout card=row();card.setPadding(d(9),d(9),d(9),d(9));card.setBackground(bordered(WHITE,LINE,16));root.addView(card,lp(-1,180));sideMargins(card,0,0,0,10);
        card.addView(photo(String.format(java.util.Locale.ROOT,"menu_%02d.jpg",i+1),95,95));
        LinearLayout details=column();details.setPadding(d(12),0,0,0);card.addView(details,new LinearLayout.LayoutParams(0,-1,1));
        LinearLayout productTop=row();details.addView(productTop,lp(-1,-2));
        TextView productName=text(names[i],16,INK,true);productName.setMaxLines(2);
        productTop.addView(productName,new LinearLayout.LayoutParams(0,-2,1));
        TextView favorite=pill(favorites.contains(i)?"♥":"♡",favorites.contains(i),()->toggleFavorite(i));
        productTop.addView(favorite,lp(-2,48));
        favorite.setContentDescription(names[i]+(favorites.contains(i)?" 찜 해제":" 찜하기"));
        details.addView(text(units[i],11,MUTED,false));
        details.addView(text(won(prices[i])+"  ·  미승인 시연",14,RED,true));gap(details,2);
        TextView add=button("상세·구성 선택",RED,()->openProduct(i));
        details.addView(add,lp(-1,48));
        card.setOnClickListener(v->openProduct(i));
        card.setContentDescription(names[i]+" 상세 페이지 보기");
    }
    private void openProduct(int i){
        if(i<0 || i>=names.length)return;
        selectedProduct=i;
        detailQuantity=1;
        open("product_detail");
    }
    private void productDetail(){
        final int i=selectedProduct;
        if(i<0 || i>=names.length){
            section("상품을 찾을 수 없습니다.","상품 목록에서 다시 선택해주세요.");
            content.addView(button("상품 목록",RED,()->open("products")),lp(-1,52));
            return;
        }
        section("상품 상세","가락한상 오더 · 상품별 구성 및 수량 선택");
        ImageView cover=photo(String.format(java.util.Locale.ROOT,"menu_%02d.jpg",i+1),-1,250);
        content.addView(cover,lp(-1,250));
        gap(content,15);
        content.addView(text(names[i],22,INK,true));
        gap(content,7);
        content.addView(text(units[i],13,MUTED,false));
        gap(content,9);
        content.addView(text(won(prices[i])+" · 시연 기준가",19,RED,true));
        gap(content,14);
        content.addView(text(descriptions[i],14,INK,false));
        gap(content,18);
        content.addView(text("구성 및 옵션",17,INK,true));
        gap(content,7);
        TextView configuration=text("기본 구성 · 추가 옵션/손질/맵기는 운영 상품 API 검증 후 제공",13,MUTED,false);
        configuration.setPadding(d(12),d(12),d(12),d(12));
        configuration.setBackground(bordered(WHITE,LINE,12));
        content.addView(configuration,lp(-1,-2));
        gap(content,15);
        content.addView(text("수량 선택",17,INK,true));
        LinearLayout selector=row();
        selector.setPadding(d(9),d(7),d(9),d(7));
        selector.setBackground(bordered(WHITE,LINE,14));
        content.addView(selector,lp(-1,66));
        TextView chosen=text(String.valueOf(detailQuantity),18,INK,true);
        chosen.setGravity(Gravity.CENTER);
        TextView amount=text(won((long)prices[i]*detailQuantity),17,RED,true);
        selector.addView(pill("−",false,()->{
            detailQuantity=Math.max(1,detailQuantity-1);
            chosen.setText(String.valueOf(detailQuantity));
            amount.setText(won((long)prices[i]*detailQuantity));
        }),lp(-2,48));
        selector.addView(chosen,new LinearLayout.LayoutParams(0,-1,1));
        selector.addView(pill("+",true,()->{
            detailQuantity=Math.min(99,detailQuantity+1);
            chosen.setText(String.valueOf(detailQuantity));
            amount.setText(won((long)prices[i]*detailQuantity));
        }),lp(-2,48));
        gap(content,11);
        content.addView(text("선택 상품 합계 (배달비·할인 전)",12,MUTED,false));
        content.addView(amount,lp(-1,42));
        gap(content,13);
        TextView restriction=text("AI 연출 이미지 및 시연 기준가입니다. 실제 판매 승인, 옵션 가격, 재고, 배달료를 운영 서버에서 확인하기 전에는 결제되지 않습니다.",12,RED,true);
        content.addView(restriction,lp(-1,-2));
        gap(content,15);
        content.addView(button("장바구니 담기 · "+won(prices[i])+"부터",RED,()->{
            cart[i]=Math.min(99,cart[i]+detailQuantity);
            save();
            Toast.makeText(this,"시연 장바구니에 "+detailQuantity+"개 담았습니다.",Toast.LENGTH_SHORT).show();
            open("cart");
        }),lp(-1,54));
        gap(content,9);
        content.addView(button("주문서 보기 (결제 연결 준비 중)",GREEN,()->{
            cart[i]=Math.min(99,cart[i]+detailQuantity);
            save();
            open("checkout");
        }),lp(-1,52));
        gap(content,8);
        content.addView(button("상품 목록으로",0xFF77645F,()->open("products")),lp(-1,48));
    }

    private void cart(){section("장바구니", "선택한 상품을 확인하세요. 실제 주문 요청은 전송되지 않습니다.");
        fulfillmentChooser();gap(content,14);
        int total=count();if(total==0){TextView msg=text("장바구니가 비었습니다.\n상품 목록에서 재료를 담아보세요.",16,MUTED,false);msg.setGravity(Gravity.CENTER);content.addView(msg,lp(-1,120));content.addView(button("상품 둘러보기",RED,()->open("products")),lp(-1,52));return;}
        for(int i=0;i<names.length;i++)if(cart[i]>0){final int id=i;LinearLayout cell=row();cell.setPadding(d(12),d(12),d(12),d(12));cell.setBackground(bordered(WHITE,LINE,14));content.addView(cell,lp(-1,74));sideMargins(cell,0,0,0,9);
           TextView t=text(names[i]+"\n"+won(prices[i])+" × "+cart[i]+" = "+won((long)prices[i]*cart[i]),13,INK,true);cell.addView(t,new LinearLayout.LayoutParams(0,-1,1));TextView minus=pill("−",false,()->{cart[id]=Math.max(0,cart[id]-1);save();render();});cell.addView(minus,lp(-2,48));TextView num=text("  "+cart[i]+"  ",17,INK,true);cell.addView(num);TextView plus=pill("+",true,()->{cart[id]=Math.min(99,cart[id]+1);save();render();});cell.addView(plus,lp(-2,48));}
        gap(content,15);TextView note=text("선택 수량 "+total+"개\n상품 합계 "+won(cartTotal())+"\n\n배송비·할인 전 금액입니다. 실제 주문·결제·배송 접수는 제공되지 않습니다.",15,INK,true);content.addView(note);
        gap(content,14);content.addView(button("주문서 미리보기 · 실제 결제 불가",RED,()->open("checkout")),lp(-1,52));
        gap(content,8);content.addView(button("선택 초기화",GREEN,()->new AlertDialog.Builder(this).setTitle("장바구니 비우기").setMessage("저장한 상품 수량을 지울까요?").setPositiveButton("초기화",(dialog,w)->{Arrays.fill(cart,0);save();render();}).setNegativeButton("취소",null).show()),lp(-1,48));
    }
    private void checkoutPreview(){
        section("주문서 미리보기","개발 중 화면 · 주문/결제는 진행되지 않습니다.");
        if(count()==0){
            content.addView(text("장바구니가 비어 있습니다.",15,MUTED,false));gap(content,12);
            content.addView(button("상품 보기",RED,()->open("products")),lp(-1,48));return;
        }
        infoCell("주문 방식",fulfillment+" (화면 시연만)");
        infoCell("선택 지역",demoArea+" · 서비스 권역 미확인");
        infoCell("매장", "광양수산 · 시연 카탈로그 (입점 미검증)");
        gap(content,13);
        section("담은 상품", count()+"개 · 데이터는 이 기기에만 저장됩니다");
        for(int i=0;i<cart.length;i++)if(cart[i]>0){
            TextView t=text(names[i]+" × "+cart[i]+"  ·  "+won((long)prices[i]*cart[i]),14,INK,false);
            content.addView(t,lp(-1,-2));gap(content,7);
        }
        gap(content,13);infoCell("상품 시연 합계",won(cartTotal()));
        infoCell("배송비 · 쿠폰 · 수수료", "운영 정책 미확정 / 계산 불가");
        infoCell("최종 결제금액", "제공 불가 · 서버 검증 전");
        gap(content,12);
        TextView warning=text("이 화면은 주문이 아닙니다. 실가격·품절·원산지·알레르기·배송료 확인 및 PG 연동 전까지 주문 생성과 결제를 차단합니다.",13,RED,true);
        content.addView(warning);
        gap(content,15);
        content.addView(button("주문·결제 기능 준비 중",0xFF8B817D,()->new AlertDialog.Builder(this)
            .setTitle("주문 접수 불가")
            .setMessage("현재 화면은 개발용 시연입니다. 결제 요청, 실주문, 재고 차감, 배송 배차는 발생하지 않습니다.")
            .setPositiveButton("확인",null).show()),lp(-1,52));
        gap(content,10);content.addView(button("장바구니 돌아가기",GREEN,()->open("cart")),lp(-1,48));
    }
    private void addressPage(){
        section("배송권역 확인 · 개발 P1","현재 정확한 배송지·GPS·주소는 수집하지 않습니다.");
        content.addView(text("우편번호 5자리로 API 확인을 요청할 수 있습니다. 서버에서 공식 배송권역이 검증되지 않으면 배송 불가/미설정으로 표시됩니다. 우편번호는 저장하지 않습니다.",14,MUTED,false));
        gap(content,14);
        EditText postal=new EditText(this);
        postal.setHint("우편번호 5자리 입력");postal.setSingleLine(true);
        postal.setInputType(InputType.TYPE_CLASS_NUMBER);
        postal.setFilters(new InputFilter[]{new InputFilter.LengthFilter(5)});
        postal.setBackground(bordered(WHITE,LINE,12));postal.setPadding(d(16),0,d(16),0);
        content.addView(postal,lp(-1,52));gap(content,12);
        TextView output=text("서버 상태: "+mobileApi.status(),13,MUTED,false);
        content.addView(output,lp(-1,-2));gap(content,12);
        content.addView(button("배송 가능 지역 조회 (읽기 전용)",RED,()->{
            final int requestId=++addressRequestSerial;
            output.setText("조회 중…");
            mobileApi.serviceability(postal.getText().toString(),(data,error)->{
                if(requestId!=addressRequestSerial || !page.equals("address") || isFinishing() || isDestroyed())return;
                if(error!=null){output.setText("확인 불가: "+error);return;}
                boolean verified=data.optBoolean("verified",false);
                boolean serviceable=data.optBoolean("serviceable",false);
                // Even a misconfigured server cannot turn this P1 preview into a checkout.
                output.setText(verified && serviceable ? "검증 응답 수신 · 실제 주문은 별도 승인 전 불가"
                    : "배송권역 미확인 · 실제 주문 불가\n"+data.optString("message","권역 정보 없음"));
            });
        }),lp(-1,52));
        gap(content,12);content.addView(text("실제 상세 주소와 전화번호는 운영 인증 및 개인정보 동의 기능 승인 전까지 입력받지 않습니다.",12,RED,true));
    }
    private void authPreviewPage(){
        section("계정 로그인 · P1C","Google 로그인 검증 준비 · 현재 실제 로그인 불가");
        infoCell("인증 방식", "Neon Managed Better Auth / Google 소셜 로그인");
        infoCell("모바일 로그인", "OAuth public client 및 검증된 HTTPS App Link 미설정");
        infoCell("OAuth 코드 교환", "PKCE·일회용 콜백·HTTPS 토큰 보호 구현 / 개발 인증서버 미준비");
        infoCell("안드로이드 앱 링크", "실제 앱 서명 SHA-256·assetlinks.json 확인 전까지 비활성");
        TextView result=text("개발 API 설정: "+mobileApi.status(),14,MUTED,false);
        content.addView(result,lp(-1,-2));gap(content,14);
        content.addView(button("서버 로그인 준비 상태 확인",RED,()->{
            final int requestId=++authRequestSerial;
            result.setText("로그인 준비 상태 조회 중…");
            mobileApi.authStatus((data,error)->{
                if(requestId!=authRequestSerial || !page.equals("auth_preview") || isFinishing() || isDestroyed())return;
                if(error!=null){result.setText("상태 조회 실패 · "+error);return;}
                result.setText("실제 로그인: "+(data.optBoolean("login_enabled",false)?"서버 설정 검토 필요":"비활성화")
                    +"\n"+data.optString("reason","추가 검증 필요"));
            });
        }),lp(-1,50));
        gap(content,14);
        content.addView(text("안전 조치: 앱에 Google 비밀번호·클라이언트 비밀키·JWT를 입력하거나 저장하지 않습니다. 외부 브라우저 PKCE·공식 App Link·운영과 분리된 Neon 개발 브랜치 검증 후에만 활성화됩니다.",13,RED,true));
    }
    private void apiPage(){
        section("모바일 API 연결 · P1","서버에서 조회 가능한 개발 데이터만 표시합니다. 실제 판매/배달이 아닙니다.");
        infoCell("연결 상태",mobileApi.status());
        TextView result=text("조회할 항목을 선택하세요. 데이터 조회 결과로 주문이 활성화되지는 않습니다.",13,MUTED,false);
        content.addView(result,lp(-1,-2));gap(content,12);
        content.addView(button("개발 서버 상태",RED,()->apiRequest("bootstrap",result)),lp(-1,48));gap(content,9);
        content.addView(button("Neon 로그인 연결 상태",GREEN,()->apiRequest("auth",result)),lp(-1,48));gap(content,9);
        content.addView(button("시장 목록 (읽기 전용)",RED,()->apiRequest("markets",result)),lp(-1,48));gap(content,9);
        content.addView(button("시연 매장 목록 (읽기 전용)",GREEN,()->apiRequest("merchants",result)),lp(-1,48));gap(content,9);
        content.addView(button("시연 상품 목록 (읽기 전용)",RED,()->apiRequest("products",result)),lp(-1,48));
        gap(content,14);
        content.addView(text("고객 로그인·실제 주소·실결제·실주문 API는 아직 활성화되지 않았습니다.",13,RED,true));
    }
    private void apiRequest(String what, TextView output){
        final int requestId=++apiRequestSerial;
        output.setText("조회 중…");
        MobileApiClient.Callback callback=(data,error)->{
            if(requestId!=apiRequestSerial || !page.equals("api") || isFinishing() || isDestroyed())return;
            if(error!=null){output.setText("API 조회 실패: "+error);return;}
            if(what.equals("bootstrap")){
                output.setText("서버 모드: "+data.optString("mode","정보 없음")
                    +"\n주문 허용: "+(data.optBoolean("checkout_enabled",false)?"서버 설정 검토 필요":"아니오")
                    +"\n"+data.optString("message",""));return;
            }
            if(what.equals("auth")){
                output.setText("로그인 연결: "+(data.optBoolean("login_enabled",false)?"서버 응답됨 (앱 인증 미연결)":"미연결")
                    +"\n"+data.optString("reason",""));return;
            }
            JSONArray arr=data.optJSONArray("items");
            if(arr==null){output.setText("API 응답 목록 형식이 다릅니다.");return;}
            StringBuilder summary=new StringBuilder("개발용 "+what+" 조회: "+arr.length()+"건\n");
            for(int i=0;i<Math.min(8,arr.length());i++){
                JSONObject item=arr.optJSONObject(i); if(item==null)continue;
                summary.append("• ").append(safeRemoteText(item.optString("name","이름 없음"),80))
                    .append(" · 시연/주문 불가\n");
            }
            if(arr.length()>8)summary.append("외 ").append(arr.length()-8).append("건");
            if(arr.length()==0)summary.append("검증된 운영 데이터 없음");
            output.setText(summary.toString());
        };
        switch(what){
            case "bootstrap":mobileApi.bootstrap(callback);break;
            case "auth":mobileApi.authStatus(callback);break;
            case "markets":mobileApi.markets(callback);break;
            case "merchants":mobileApi.merchants(callback);break;
            case "products":mobileApi.products(callback);break;
            default:output.setText("지원하지 않는 API 요청입니다.");
        }
    }
    @Override protected void onDestroy(){
        if(mobileApi!=null)mobileApi.close();
        super.onDestroy();
    }
    /** A deliberately separate, read-only server catalog. It cannot write into the demo cart. */
    private void remoteCatalogPage(){
        section("시장·매장·상품 탐색 · P1", "개발 서버 시연 목록 · 실제 입점/영업/배달이 아닙니다.");
        infoCell("서버 연결",mobileApi.status());
        TextView status=text("시장 목록을 불러오려면 아래 버튼을 누르세요. 상품을 담거나 주문할 수 없습니다.",13,MUTED,false);
        content.addView(status,lp(-1,-2));gap(content,12);
        LinearLayout list=column();
        content.addView(button("전체 시장 목록 조회",RED,()->loadRemoteMarkets(list,status)),lp(-1,50));
        gap(content,12);
        content.addView(list,lp(-1,-2));
        if(!selectedRemoteMarketId.isEmpty()) {
            String chosen=selectedRemoteMarketId, caption=selectedRemoteMarketName;
            content.addView(button("선택한 시장의 매장 재조회 · "+caption,GREEN,
                ()->loadRemoteMerchants(chosen,caption,list,status)),lp(-1,50));
        }
        gap(content,18);
        content.addView(text("원본 47종 로컬 카탈로그와 서버의 개발 상품은 서로 다른 데이터입니다. 서버 상품은 장바구니·결제 화면으로 이동할 수 없습니다.",12,RED,true));
    }
    private static String safeRemoteText(String raw,int limit){
        if(raw==null || limit<1)return "";
        StringBuilder clean=new StringBuilder(Math.min(limit,raw.length()));
        for(int i=0;i<raw.length() && clean.length()<limit;i++){
            char c=raw.charAt(i);
            clean.append(Character.isISOControl(c)?' ':c);
        }
        return clean.toString().trim();
    }
    private void remoteMessage(TextView status, String message){status.setText(safeRemoteText(message,220));}
    private void remoteError(LinearLayout list,TextView status,String error){
        list.removeAllViews();
        remoteMessage(status,"조회 실패 · "+error+"\n주문·배달 가능 여부는 확인되지 않았습니다.");
    }
    private boolean remoteAlive(){return "remote_catalog".equals(page)&&!isFinishing()&&!isDestroyed();}
    private void remoteItem(LinearLayout list,String headline,String detail,Runnable click){
        LinearLayout item=column();item.setPadding(d(14),d(12),d(14),d(12));
        item.setBackground(bordered(WHITE,LINE,13));list.addView(item,lp(-1,-2));sideMargins(item,0,0,0,10);
        item.addView(text(headline,16,INK,true));gap(item,3);
        item.addView(text(detail,12,MUTED,false));
        if(click!=null){
            item.setOnClickListener(v->click.run());
            item.setContentDescription(headline+" · 시연 상세 열기");
        }
    }
    private void loadRemoteMarkets(LinearLayout list,TextView status){
        final int requestId=++remoteRequestSerial;
        list.removeAllViews();remoteMessage(status,"시장 목록을 조회 중입니다…");
        mobileApi.markets((data,error)->{
            if(!remoteAlive() || requestId!=remoteRequestSerial)return;
            if(error!=null){remoteError(list,status,error);return;}
            JSONArray items=data.optJSONArray("items");
            if(items==null){remoteError(list,status,"시장 목록 형식 오류");return;}
            list.removeAllViews();remoteMessage(status,"시연 시장 "+items.length()+"개 · 배송 가능 판정 아님");
            if(items.length()==0)remoteItem(list,"시연 시장 없음","서버의 시장 등록/승인 정보를 확인하세요.",null);
            for(int i=0;i<Math.min(100,items.length());i++){
                JSONObject item=items.optJSONObject(i);if(item==null)continue;
                String id=item.optString("id","");
                if(!id.matches("[A-Za-z0-9_-]{1,60}"))continue;
                String title=safeRemoteText(item.optString("name","시장 이름 없음"),80);
                remoteItem(list,title,"배송 미검증 · 판매 불가 · 매장 둘러보기",
                    ()->loadRemoteMerchants(id,title,list,status));
            }
        });
    }
    private void loadRemoteMerchants(String marketId,String marketName,LinearLayout list,TextView status){
        final int requestId=++remoteRequestSerial;
        remoteMessage(status,marketName+" · 매장을 조회 중입니다…");list.removeAllViews();
        mobileApi.merchants(marketId,(data,error)->{
            if(!remoteAlive() || requestId!=remoteRequestSerial)return;
            if(error!=null){remoteError(list,status,error);return;}
            JSONArray items=data.optJSONArray("items");
            if(items==null){remoteError(list,status,"매장 목록 형식 오류");return;}
            selectedRemoteMarketId=marketId;selectedRemoteMarketName=marketName;
            selectedRemoteMerchantName="";
            list.removeAllViews();remoteMessage(status,marketName+" · 개발용 매장 "+items.length()+"개");
            if(items.length()==0)remoteItem(list,"시연 매장 없음","판매 승인과 영업 현황이 아닙니다.",null);
            for(int i=0;i<Math.min(200,items.length());i++){
                JSONObject item=items.optJSONObject(i);if(item==null)continue;
                String name=safeRemoteText(item.optString("name",""),90);if(name.isEmpty())continue;
                remoteItem(list,name,"시연 매장 · 배달/주문 불가 · 상품 보기",
                    ()->loadRemoteProducts(marketId,marketName,name,list,status));
            }
        });
    }
    private void loadRemoteProducts(String marketId,String marketName,String merchantName,
                                    LinearLayout list,TextView status){
        final int requestId=++remoteRequestSerial;
        remoteMessage(status,merchantName+" · 시연 상품 조회 중…");list.removeAllViews();
        mobileApi.products(marketId,merchantName,(data,error)->{
            if(!remoteAlive() || requestId!=remoteRequestSerial)return;
            if(error!=null){remoteError(list,status,error);return;}
            JSONArray items=data.optJSONArray("items");
            if(items==null){remoteError(list,status,"상품 목록 형식 오류");return;}
            selectedRemoteMerchantName=merchantName;
            list.removeAllViews();remoteMessage(status,marketName+" › "+merchantName+" · 시연 상품 "+items.length()+"개");
            remoteItem(list,"‹ 매장 목록으로 돌아가기","기존 시연 장바구니와 별도로 표시됩니다.",
                ()->loadRemoteMerchants(marketId,marketName,list,status));
            if(items.length()==0)remoteItem(list,"시연 상품 없음","아직 조회 가능한 상품이 없습니다.",null);
            for(int i=0;i<Math.min(200,items.length());i++){
                JSONObject item=items.optJSONObject(i);if(item==null)continue;
                String name=safeRemoteText(item.optString("name","상품 이름 없음"),100);
                // Never trust remote 'orderable' or 'price' flags to enable checkout.
                long krw=item.optLong("price_krw",-1);
                remoteItem(list,name,(krw>=0?won(krw)+" · ":"")+"서버 카탈로그 · 상세 보기",
                    ()->{selectedRemoteProduct=item;open("remote_product_detail");});
            }
        });
    }
    private void remoteProductDetail(){
        // This screen contains server-supplied, approved merchant catalog data.
        // It never trusts price/availability flags to enable ordering or payments.
        JSONObject product=selectedRemoteProduct;
        if(product==null){
            section("상품 조회 정보 없음","서버 상품 목록에서 다시 선택해 주세요.");
            content.addView(button("서버 상품 다시 보기",RED,()->open("remote_catalog")),lp(-1,52));
            return;
        }
        String name=safeRemoteText(product.optString("name","상품"),100);
        String slug=safeRemoteText(product.optString("slug",product.optString("id","")),80);
        String merchant=safeRemoteText(product.optString("merchant",""),90);
        String origin=safeRemoteText(product.optString("origin",""),100);
        long price=product.optLong("price_krw",-1);
        long stock=product.optLong("stock",-1);
        section("서버 상품 상세","웹서버에서 조회한 상품 정보 · 실결제 연결 전");
        LinearLayout hero=column();
        hero.setPadding(d(16),d(18),d(16),d(18));
        hero.setBackground(shape(WHITE,20));
        content.addView(hero,lp(-1,-2));
        hero.addView(text(name,23,INK,true));
        gap(hero,12);
        hero.addView(text(price>0?won(price):"서버 가격 확인 불가",19,RED,true));
        gap(hero,11);
        hero.addView(text("판매처 · "+(merchant.isEmpty()?"정보 확인 중":merchant),14,INK,false));
        hero.addView(text("상품 식별자 · "+(slug.isEmpty()?"정보 없음":slug),12,MUTED,false));
        gap(content,16);
        infoCell("원산지",origin.isEmpty()?"검수 후 표기":origin);
        infoCell("재고 표시",stock>=0?stock+"개 (시연 DB 기준)":"재고 확인 불가");
        infoCell("상품 사진","서버 원본 이미지 승인 및 모바일 미디어 매핑 후 제공");
        infoCell("상품 옵션","판매자별 실제 옵션·추가메뉴·선택가격 등록 및 검수 후 활성화");
        gap(content,8);
        content.addView(text("이 상품은 서버에서 가져온 참고 정보입니다. 로컬 시연 카트와 SKU가 일치한다고 보장할 수 없어 주문·결제·장바구니에 추가하지 않습니다.",13,RED,true));
        gap(content,16);
        content.addView(button("서버 목록으로 돌아가기",GREEN,()->open("remote_catalog")),lp(-1,52));
    }
    private void infoCell(String label,String value){
        LinearLayout wrap=column();wrap.setPadding(d(15),d(11),d(15),d(11));
        wrap.setBackground(bordered(WHITE,LINE,13));content.addView(wrap,lp(-1,-2));
        wrap.addView(text(label,12,MUTED,false));wrap.addView(text(value,15,INK,true));gap(content,9);
    }
    private void orders(){
        section("주문 내역","실제 주문 서버 미연동 · 주문 정보 없음");
        TextView empty=text("아직 주문한 내역이 없습니다.\n현재 장바구니는 시연 기능이며 실제 주문으로 처리되지 않습니다.",15,MUTED,false);
        empty.setGravity(Gravity.CENTER);content.addView(empty,lp(-1,155));
        content.addView(button("상품 둘러보기",RED,()->open("products")),lp(-1,52));
    }
    private void favoritesPage(){
        section("찜한 상품",favorites.size()+"개 · 이 기기에서만 보관됩니다");
        if(favorites.isEmpty()){
            content.addView(text("찜한 상품이 없습니다. 상품의 ♡ 버튼을 눌러보세요.",15,MUTED,false));
            gap(content,12);content.addView(button("상품 보기",RED,()->open("products")),lp(-1,48));return;
        }
        for(int i=0;i<names.length;i++)if(favorites.contains(i))addProduct(i);
    }
    private void myPage(){
        section("마이 가락한상","회원 로그인·주소 저장·실주문 조회는 아직 제공되지 않습니다.");
        infoCell("현재 시연 지역",demoArea);
        infoCell("시연 주문 방식",fulfillment);
        content.addView(button("시연 지역 바꾸기",GREEN,this::chooseDemoArea),lp(-1,46));gap(content,10);
        content.addView(button("우편번호 · 배송권역 확인 (P1)",RED,()->open("address")),lp(-1,48));gap(content,10);
        content.addView(button("Google 로그인 검증 준비 (P1E)",RED,()->open("auth_preview")),lp(-1,48));gap(content,10);
        content.addView(button("시장·매장·상품 API 상태 (P1)",0xFF6B514B,()->open("api")),lp(-1,48));gap(content,10);
        content.addView(button("개발 서버 시장·매장·상품 탐색 (P1)",GREEN,()->open("remote_catalog")),lp(-1,48));gap(content,10);
        content.addView(button("찜한 상품 · "+favorites.size()+"개",RED,()->open("favorites")),lp(-1,48));
        gap(content,10);content.addView(button("서비스 및 개인정보 안내",0xFF6B514B,()->open("info")),lp(-1,48));
        gap(content,13);content.addView(text("테스트용 데이터는 기기 내에만 보관됩니다. 카드 번호, 휴대폰 번호, 상세 주소 등은 수집하지 않습니다.",12,MUTED,false));
    }
    private void info(){section("가락한상 오더","공식 캐릭터를 활용한 Android 네이티브 47개 메뉴 시연 앱");ImageView image=photo("garakhansang_official_logo",-1,230);content.addView(image,lp(-1,230));gap(content,18);
        content.addView(text("47개 시연 메뉴 · 12개 카테고리 탐색\n시연용 지역 선택 · 배달/포장 화면 전환 · 찜 목록\n장바구니 · 주문서 미리보기 (실접수 차단)\n\n모든 메뉴는 원본상 '숨김'이며 AI 콘셉트 이미지를 사용합니다. 실제 입점·판매가·결제·배달은 연결되지 않았습니다.\n\n테스트 버전 1.10.0-p1g-accessibility-demo · 47종 메뉴",14,INK,false));gap(content,12);
        content.addView(button("상품 보러가기",RED,()->open("products")),lp(-1,52));
    }
    @Override public void onBackPressed(){
        if(page.equals("checkout"))open("cart");
        else if(page.equals("product_detail"))open("products");
        else if(page.equals("remote_product_detail"))open("remote_catalog");
        else if(page.equals("api")||page.equals("address")||page.equals("remote_catalog")||page.equals("auth_preview"))open("my");
        else if(page.equals("favorites")||page.equals("info"))open("my");
        else if(!page.equals("home"))open("home");
        else super.onBackPressed();
    }
}
