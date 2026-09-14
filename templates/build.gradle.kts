plugins {
    kotlin("jvm") version "{{KOTLIN_VERSION}}"
    application
}

group = "{{PACKAGE_NAME}}"
version = "1.0-SNAPSHOT"

repositories {
    mavenCentral()
}

dependencies {
    testImplementation(kotlin("test"))
}

application {
    mainClass.set("{{PACKAGE_NAME}}.AppKt")
}

kotlin {
    // Supported JVM versions for Kotlin {{KOTLIN_VERSION}}: {{JAVA_VERSIONS}}
    jvmToolchain({{JAVA_VERSION}})
}

// Creates uber-jar. No external libs. Alternative: use `shadow` plugin (https://gradleup.com/shadow/)
tasks.jar {
    manifest {
        attributes["Main-Class"] = application.mainClass.get()
    }
    // Fixes duplicates if multiple dependencies have the same file (like module-info.class)
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
    // Collects all dependencies from the runtime classpath and zips them into the Jar
    from(configurations.runtimeClasspath.get().map { if (it.isDirectory) it else zipTree(it) })
}