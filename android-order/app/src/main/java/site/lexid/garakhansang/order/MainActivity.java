package site.lexid.garakhansang.order;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.os.Build;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.graphics.BitmapFactory;
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
import org.json.JSONObject;
import java.util.*;

/** Offline native ordering demo: no checkout, no payment, no external data collection. */
public class MainActivity extends Activity {
    private static final int RED = 0xFFCA1020, INK = 0xFF2D211F, CREAM = 0xFFFFF7EC,
            MUTED = 0xFF7A6660, GREEN = 0xFF49753D, WHITE = Color.WHITE, LINE = 0xFFF0E5DD;
    private final String[] kinds = {"전체", "수산", "축산", "농산"};
    private final String[] names = {"고등어", "새우", "제철 생선", "한우 불고기", "돼지 목살", "닭 안심", "제철 과일", "신선 채소", "제철 버섯"};
    private final String[] units = {"수산 · 시범 상품", "수산 · 시범 상품", "수산 · 시범 상품", "축산 · 시범 상품", "축산 · 시범 상품", "축산 · 시범 상품", "농산 · 시범 상품", "농산 · 시범 상품", "농산 · 시범 상품"};
    private final int[] images = {0,0,0,1,1,1,2,2,2};
    private String page="home", category="전체", query="";
    private int[] cart = new int[9];
    private LinearLayout app, content;
    private SharedPreferences prefs;
    private EditText searchEdit;

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        getWindow().setStatusBarColor(RED);
        getWindow().setNavigationBarColor(CREAM);
        // Android 15+ uses a transparent status bar. Dark status icons are readable on cream.
        if (Build.VERSION.SDK_INT >= 35) {
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller != null) controller.setSystemBarsAppearance(
                WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS,
                WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS);
        }
        prefs = getSharedPreferences("order_preview",MODE_PRIVATE);
        for (int i=0;i<cart.length;i++) cart[i]=Math.max(0,Math.min(99,prefs.getInt("q"+i,0)));
        render();
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
    private ImageView photo(String file,int width,int height){ImageView im=new ImageView(this);try{im.setImageBitmap(BitmapFactory.decodeStream(getAssets().open(file+".webp")));}catch(Exception ignored){}im.setScaleType(ImageView.ScaleType.CENTER_CROP);im.setBackground(shape(LINE,12));im.setClipToOutline(true);im.setLayoutParams(lp(width,height));im.setContentDescription(file+" 사진");return im;}
    private TextView pill(String label,boolean active,Runnable onClick){TextView b=text(label,13,active?WHITE:INK,true);b.setGravity(Gravity.CENTER);b.setPadding(d(14),0,d(14),0);b.setBackground(shape(active?RED:0xFFF6EDE5,28));b.setOnClickListener(v->onClick.run());return b;}
    private TextView button(String label,int color,Runnable click){TextView b=text(label,15,WHITE,true);b.setGravity(Gravity.CENTER);b.setPadding(d(12),0,d(12),0);b.setBackground(shape(color,14));b.setOnClickListener(v->click.run());return b;}
    private int count(){int c=0;for(int n:cart)c+=n;return c;}
    private void save(){SharedPreferences.Editor e=prefs.edit();for(int i=0;i<cart.length;i++)e.putInt("q"+i,cart[i]);e.apply();}
    private void open(String p){page=p;render();}
    private void render(){
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
        switch(page){case "products":products();break;case "cart":cart();break;case "orders":orders();break;case "info":info();break;default:home();}
        footer();
    }
    private void header(){
        LinearLayout bar=row();bar.setPadding(d(18),d(8),d(18),d(8));bar.setBackgroundColor(WHITE);app.addView(bar,lp(-1,64));
        ImageView icon=photo("order_brand_512",48,48);bar.addView(icon);icon.setOnClickListener(v->open("home"));
        LinearLayout labels=column();labels.setPadding(d(10),0,0,0);bar.addView(labels,new LinearLayout.LayoutParams(0,-2,1));
        labels.addView(text("가락한상 오더",20,INK,true));labels.addView(text("시장에서 식탁까지, 간편하게",11,MUTED,false));
        TextView bag=pill("장바구니 "+count(),true,()->open("cart"));bar.addView(bag,lp(-2,38));
    }
    private void footer(){
        LinearLayout bar=row();bar.setPadding(d(10),d(5),d(10),d(8));bar.setBackground(bordered(WHITE,LINE,0));app.addView(bar,lp(-1,66));
        String[][] nav={{"⌂","홈","home"},{"▦","상품","products"},{"▤","장바구니","cart"},{"☷","안내","info"}};
        for(String[] item:nav){LinearLayout segment=column();segment.setGravity(Gravity.CENTER);TextView ico=text(item[0],22,page.equals(item[2])?RED:MUTED,true);ico.setGravity(Gravity.CENTER);segment.addView(ico);TextView t=text(item[1],11,page.equals(item[2])?RED:MUTED,true);t.setGravity(Gravity.CENTER);segment.addView(t);bar.addView(segment,new LinearLayout.LayoutParams(0,-1,1));segment.setOnClickListener(v->open(item[2]));}
    }
    private void section(String title,String sub){TextView h=text(title,22,INK,true);content.addView(h,lp(-1,34));if(sub!=null){TextView s=text(sub,13,MUTED,false);s.setLineSpacing(d(2),1);content.addView(s,lp(-1,-2));}gap(content,14);}
    private void home(){
        LinearLayout hero=column();hero.setPadding(d(17),d(15),d(17),d(18));hero.setBackground(shape(RED,20));content.addView(hero,lp(-1,-2));
        TextView badge=text("가락시장 한상차림",12,0xFFFFD8B8,true);hero.addView(badge);
        TextView h=text("오늘도 신선하게,\n가락한상 오더",28,WHITE,true);hero.addView(h);gap(hero,8);
        hero.addView(text("수산 · 축산 · 농산을 한 곳에서",14,WHITE,false));gap(hero,14);
        LinearLayout bar=row();hero.addView(bar,lp(-1,118));ImageView food=photo("food",-1,118);bar.addView(food,new LinearLayout.LayoutParams(-1,-1));
        gap(content,22);section("어떤 재료를 찾으세요?","가락한상에서 엄선한 식재료 카테고리");
        LinearLayout cats=row();content.addView(cats,lp(-1,150));String[] tags={"수산","축산","농산"};String[] files={"seafood","meat","produce"};
        for(int i=0;i<3;i++){final String kind=tags[i];LinearLayout card=column();card.setPadding(d(4),d(4),d(4),d(4));cats.addView(card,new LinearLayout.LayoutParams(0,-1,1));ImageView ph=photo(files[i],-1,100);card.addView(ph,new LinearLayout.LayoutParams(-1,d(100)));TextView title=text(tags[i],15,INK,true);title.setGravity(Gravity.CENTER);card.addView(title,lp(-1,30));card.setOnClickListener(v->{category=kind;open("products");});}
        gap(content,24);section("가락한상 추천", "시장 상품 목록 미연동 · 시범 콘텐츠입니다");
        for(int i:new int[]{0,3,6}) addProduct(i);
        gap(content,14);TextView order=button("장바구니 확인  ·  "+count()+"개",RED,()->open("cart"));content.addView(order,lp(-1,52));
    }
    private void categoryBar(){HorizontalScrollView hs=new HorizontalScrollView(this);hs.setHorizontalScrollBarEnabled(false);LinearLayout row=row();hs.addView(row);for(String kind:kinds){TextView b=pill(kind,category.equals(kind),()->{category=kind;render();});row.addView(b,lp(-2,38));sideMargins(b,0,0,8,0);}content.addView(hs,lp(-1,40));gap(content,15);}
    private void products(){section("상품 탐색","실제 가격과 재고는 입점 확정 후 연결됩니다.");categoryBar();
        EditText search=new EditText(this);search.setSingleLine(true);search.setHint("상품명 검색");search.setTextSize(15);search.setPadding(d(14),d(8),d(14),d(8));search.setBackground(bordered(WHITE,LINE,14));search.setText(query);content.addView(search,lp(-1,48));gap(content,13);
        LinearLayout results=column();content.addView(results,lp(-1,-2));renderResults(results);
        search.addTextChangedListener(new TextWatcher(){public void beforeTextChanged(CharSequence s,int st,int c,int a){}public void onTextChanged(CharSequence s,int st,int before,int count){query=s.toString();renderResults(results);}public void afterTextChanged(Editable e){}});
    }
    private void renderResults(LinearLayout l){l.removeAllViews();int found=0;for(int i=0;i<names.length;i++)if((category.equals("전체")||units[i].startsWith(category))&&names[i].contains(query.trim())){addProductInto(i,l);found++;}if(found==0)l.addView(text("검색 결과가 없습니다.",15,MUTED,false),lp(-1,60));}
    private void addProduct(int i){addProductInto(i,content);}
    private void addProductInto(int i,LinearLayout root){
        LinearLayout card=row();card.setPadding(d(9),d(9),d(9),d(9));card.setBackground(bordered(WHITE,LINE,16));root.addView(card,lp(-1,116));sideMargins(card,0,0,0,10);
        card.addView(photo(images[i]==0?"seafood":images[i]==1?"meat":"produce",95,95));
        LinearLayout details=column();details.setPadding(d(12),0,0,0);card.addView(details,new LinearLayout.LayoutParams(0,-1,1));
        details.addView(text(names[i],17,INK,true));details.addView(text(units[i],12,MUTED,false));gap(details,8);
        TextView add=button(cart[i]>0?"담김 "+cart[i]+"  +":"담기 +",RED,()->{cart[i]=Math.min(99,cart[i]+1);save();Toast.makeText(this,names[i]+" 장바구니에 담음",Toast.LENGTH_SHORT).show();render();});details.addView(add,lp(-1,36));
        card.setOnClickListener(v->new AlertDialog.Builder(this).setTitle(names[i]).setMessage("시범 상품입니다. 실제 판매가·재고·배송비는 연결 전입니다. 장바구니는 이 기기에만 저장됩니다.").setPositiveButton("담기",(dg,w)->{cart[i]++;save();render();}).setNegativeButton("닫기",null).show());
    }
    private void cart(){section("장바구니", "선택한 재료를 확인하세요. 현재는 주문 요청이 전송되지 않습니다.");
        int total=count();if(total==0){TextView msg=text("장바구니가 비었습니다.\n상품 목록에서 재료를 담아보세요.",16,MUTED,false);msg.setGravity(Gravity.CENTER);content.addView(msg,lp(-1,120));content.addView(button("상품 둘러보기",RED,()->open("products")),lp(-1,52));return;}
        for(int i=0;i<names.length;i++)if(cart[i]>0){final int id=i;LinearLayout cell=row();cell.setPadding(d(12),d(12),d(12),d(12));cell.setBackground(bordered(WHITE,LINE,14));content.addView(cell,lp(-1,74));sideMargins(cell,0,0,0,9);
           TextView t=text(names[i]+"\n"+units[i],14,INK,true);cell.addView(t,new LinearLayout.LayoutParams(0,-1,1));TextView minus=pill("−",false,()->{cart[id]=Math.max(0,cart[id]-1);save();render();});cell.addView(minus,lp(-2,42));TextView num=text("  "+cart[i]+"  ",17,INK,true);cell.addView(num);TextView plus=pill("+",true,()->{cart[id]++;save();render();});cell.addView(plus,lp(-2,42));}
        gap(content,15);TextView note=text("선택 수량 "+total+"개\n\n이 화면은 시범 주문서입니다. 결제·배송·주문 접수는 아직 제공되지 않습니다.",14,MUTED,false);content.addView(note);
        gap(content,14);content.addView(button("주문 준비 중 · 실제 결제 불가",0xFF8B817D,()->new AlertDialog.Builder(this).setTitle("서비스 준비 중").setMessage("입점 매장, 상품 가격, 결제, 배송 연동이 완료된 뒤 주문 기능이 열립니다.").setPositiveButton("확인",null).show()),lp(-1,52));
        gap(content,8);content.addView(button("선택 초기화",GREEN,()->new AlertDialog.Builder(this).setTitle("장바구니 비우기").setMessage("저장한 상품 수량을 지울까요?").setPositiveButton("초기화",(dialog,w)->{Arrays.fill(cart,0);save();render();}).setNegativeButton("취소",null).show()),lp(-1,48));
    }
    private void orders(){section("주문 내역","운영 서버가 연결되지 않아 주문 기록은 없습니다.");content.addView(text("실제 주문 기능은 아직 준비 중입니다.",16,MUTED,false));}
    private void info(){section("가락한상 오더","가락한상의 공식 캐릭터를 활용한 Android 네이티브 주문 체험판");ImageView image=photo("garakhansang_official_logo",-1,230);content.addView(image,lp(-1,230));gap(content,18);
        content.addView(text("수산 · 축산 · 농산 카테고리 탐색\n장바구니 수량 기기 저장\n오프라인 상품 화면 지원\n\n실제 주문 접수·결제·판매가·매장 입점은 연결되지 않았습니다.\n\n테스트 버전 1.0.0-beta",14,INK,false));gap(content,12);
        content.addView(button("상품 보러가기",RED,()->open("products")),lp(-1,52));
    }
    @Override public void onBackPressed(){if(!page.equals("home"))open("home");else super.onBackPressed();}
}
