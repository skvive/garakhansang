package site.lexid.garakhansang.order;

/**
 * Pure Java HTTP response contract shared by catalog and OAuth token transports.
 * Reject ambiguous JSON MIME types and non-UTF-8 content before decoding data.
 * No Android classes, network access, or logging of credentials.
 */
public final class HttpResponseGuards {
    private HttpResponseGuards() {}

    public static boolean isStrictJson(String contentType) {
        if (contentType == null || contentType.length() > 256) return false;
        String[] segments = contentType.split(";", -1);
        if (segments.length < 1 || segments.length > 2
            || !"application/json".equalsIgnoreCase(segments[0].trim())) return false;
        if (segments.length == 1) return true;
        String parameter = segments[1].trim();
        int equals = parameter.indexOf('=');
        if (equals <= 0 || equals != parameter.lastIndexOf('=')) return false;
        if (!"charset".equalsIgnoreCase(parameter.substring(0, equals).trim())) return false;
        String charset = parameter.substring(equals + 1).trim();
        if (charset.length() >= 2 && charset.charAt(0) == '"'
            && charset.charAt(charset.length() - 1) == '"') {
            charset = charset.substring(1, charset.length() - 1);
        }
        return "utf-8".equalsIgnoreCase(charset);
    }
}
