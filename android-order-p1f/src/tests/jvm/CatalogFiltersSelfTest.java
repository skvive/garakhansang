import site.lexid.garakhansang.order.CatalogFilters;

/** Pure Java search tests: Android emulator not required. */
public class CatalogFiltersSelfTest {
    private static int passed=0;
    private static void test(boolean actual,boolean expected,String label){
        if(actual!=expected)throw new AssertionError(label);
        passed++;
    }
    private static boolean m(String c,String cat,String name,String desc,String q){
        return CatalogFilters.matches(c,cat,name,desc,q);
    }
    public static void main(String[] a){
        test(m("전체","회·모둠","연어회", "노르웨이산",""),true,"all");
        test(m("회·모둠","회·모둠","연어회", "맛","연어"),true,"same category");
        test(m("오늘의 한상","회·모둠","연어회", "맛","연어"),false,"different category");
        test(m("전체","회·모둠","Salmon", "fish","salmon"),true,"latin case insensitive");
        test(m("전체","회·모둠","Salmon", "fish","  SALMON  "),true,"trim and lowercase");
        test(m("전체","회·모둠","연어", "고소한 참치","참치"),true,"description");
        test(m("전체","회·모둠","연어", "고소한 참치","광어"),false,"not found");
        test(m("전체","회·모둠","연어", "고소한 참치",null),true,"null search");
        test(m(null,"회·모둠","연어", "고소한 참치","연어"),true,"null category");
        test(m("전체","회·모둠",null, "고소한 참치","참치"),true,"null name");
        test(m("전체","회·모둠",null,null,"참치"),false,"null all");
        test(m("전체","회·모둠",null,null,"  "),true,"empty search");
        test(m("회·모둠",null,"회", "맛","회"),false,"null item category");
        test(m("전체","회·모둠","회·모둠", "맛","·"),true,"punctuation");
        test(m("광양수산 인기","광양수산 인기","활새우회", "맛","활새우"),true,"korean full");
        test(m("전체","사이드","매운탕", "국물","탕"),true,"partial korean");
        System.out.println("CatalogFilters JVM checks: "+passed+" passed");
    }
}
