import site.lexid.garakhansang.order.HttpResponseGuards;

/** Android-free MIME boundary tests for both catalog and OAuth responses. */
public final class HttpResponseGuardsSelfTest {
    private static int passed=0;
    private static void check(String input, boolean expected) {
        boolean actual=HttpResponseGuards.isStrictJson(input);
        if (actual!=expected) throw new AssertionError("Unexpected JSON MIME acceptance: "+input);
        passed++;
    }
    public static void main(String[] ignored) {
        check("application/json",true);
        check("APPLICATION/JSON",true);
        check(" application/json ",true);
        check("application/json; charset=utf-8",true);
        check("application/json;charset=UTF-8",true);
        check("application/json; charset=\"utf-8\"",true);
        check(null,false);
        check("",false);
        check("text/html",false);
        check("application/json-unsafe",false);
        check("application/jsonp",false);
        check("application/json; charset=iso-8859-1",false);
        check("application/json; charset=",false);
        check("application/json; something=else",false);
        check("application/json; charset=utf-8; extra=a",false);
        check("application/json; charset=utf-8,application/json",false);
        check("application/json; charset=utf-8;",false);
        check("application/json; charset=utf-8;charset=utf-8",false);
        System.out.println("HTTP JSON content-type JVM checks: "+passed+" passed");
    }
}
