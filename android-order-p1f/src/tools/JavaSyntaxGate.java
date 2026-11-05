import java.util.Arrays;
import java.io.File;
import javax.tools.*;
import com.sun.source.util.JavacTask;

/** JDK 17+ syntax-only parse; Android SDK type checking still requires Gradle. */
public final class JavaSyntaxGate {
    public static void main(String[] args) throws Exception {
        JavaCompiler compiler=ToolProvider.getSystemJavaCompiler();
        if(compiler==null)throw new IllegalStateException("JDK compiler unavailable");
        DiagnosticCollector<JavaFileObject> diagnostics=new DiagnosticCollector<>();
        try(StandardJavaFileManager manager=compiler.getStandardFileManager(diagnostics,null,null)){
            Iterable<? extends JavaFileObject> source=manager.getJavaFileObjectsFromFiles(
                Arrays.stream(args).map(File::new).toList());
            JavacTask task=(JavacTask)compiler.getTask(null,manager,diagnostics,
                Arrays.asList("-source","17","-proc:none"),null,source);
            task.parse();
            int errors=0;
            for(Diagnostic<? extends JavaFileObject> d: diagnostics.getDiagnostics()){
                if(d.getKind()==Diagnostic.Kind.ERROR){System.err.println(d);errors++;}
            }
            if(errors!=0)throw new IllegalStateException("Java syntax errors: "+errors);
            System.out.println("Java 17 syntax parsing passed: "+args.length+" source files");
        }
    }
}
