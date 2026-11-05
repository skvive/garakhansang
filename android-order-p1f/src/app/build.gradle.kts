plugins { id("com.android.application") }

android {
    namespace = "site.lexid.garakhansang.order"
    compileSdk = 36
    defaultConfig {
        applicationId = "site.lexid.garakhansang.order"
        minSdk = 26
        targetSdk = 36
        versionCode = 19
        versionName = "1.9.0-p1e-ci-gate"
    }
    buildTypes {
        getByName("release") { isMinifyEnabled = false }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
