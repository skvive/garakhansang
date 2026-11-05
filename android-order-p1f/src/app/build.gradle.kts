plugins { id("com.android.application") }

android {
    namespace = "site.lexid.garakhansang.order"
    compileSdk = 36
    defaultConfig {
        applicationId = "site.lexid.garakhansang.order"
        minSdk = 26
        targetSdk = 36
        versionCode = 21
        versionName = "1.11.0-p1h-http-safety-demo"
    }
    buildTypes {
        getByName("release") { isMinifyEnabled = false }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
