package site.lexid.garakhansang.order;

import java.util.Locale;

/** Pure-Java menu matching; never enables hidden products or server checkout. */
public final class CatalogFilters {
    private CatalogFilters() {}
    public static boolean matches(String selectedCategory,String itemCategory,
                                  String name,String description,String query) {
        if (selectedCategory!=null && !selectedCategory.equals("전체")
                && !selectedCategory.equals(itemCategory)) return false;
        String term=query==null?"":query.trim().toLowerCase(Locale.ROOT);
        if (term.isEmpty()) return true;
        return (name!=null && name.toLowerCase(Locale.ROOT).contains(term))
            || (description!=null && description.toLowerCase(Locale.ROOT).contains(term));
    }
}
