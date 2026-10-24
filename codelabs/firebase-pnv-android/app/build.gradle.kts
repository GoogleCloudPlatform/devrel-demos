import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.google.services)
    alias(libs.plugins.kotlin.serialization)
}

// Firebase PNV test token for debug builds. Generate one in the Firebase console
// (Security > Phone Verification > Settings > Testing) and add it to your
// local.properties file, which isn't checked into version control:
//   fpnv.testToken=COPIED_TOKEN_STRING
// On CI, you can set the FPNV_TEST_TOKEN environment variable instead.
val localProperties = Properties().apply {
    rootProject.file("local.properties").takeIf { it.exists() }
        ?.inputStream()?.use { load(it) }
}
val fpnvTestToken = System.getenv("FPNV_TEST_TOKEN")?.takeIf { it.isNotEmpty() }
    ?: localProperties.getProperty("fpnv.testToken", "")

android {
    namespace = "com.google.firebase.example.fpnv"
    compileSdk {
        version = release(37)
    }

    defaultConfig {
        applicationId = "com.google.firebase.example.fpnv"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug {
            buildConfigField("String", "FPNV_TEST_TOKEN", "\"$fpnvTestToken\"")
        }
        release {
            // Release builds never enable a test session.
            buildConfigField("String", "FPNV_TEST_TOKEN", "\"\"")
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons.core)

    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.ai.logic)
    implementation(libs.firebase.pnv)

    implementation(libs.androidx.navigation3.runtime)
    implementation(libs.androidx.navigation3.ui)
    implementation(libs.androidx.lifecycle.viewmodel.navigation3)
    implementation(libs.kotlinx.serialization.core)
    implementation(libs.kotlinx.serialization.json)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
}