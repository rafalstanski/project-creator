plugins {
    kotlin("jvm") version "2.0.0"
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
    jvmToolchain(21)
}
