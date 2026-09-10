# project-creator

## What is it?

This is a project scaffold creator. It simply creates a project starting structure based on Gradle + Kotlin (JVM). When executed, it fetches the latest versions of Gradle and Kotlin, along with a list of supported Java SDK versions.

## Why?

Often, I want to create a simple project — for example, to build a prototype of a solution or try out a small concept. Usually in Kotlin. Of course, I need to start with a minimal project structure. There are many ways to start like: new project in `Intellij`, `gradle init`, ready-made `GitHub` template projects. But I'm a developer and why be efficient when you can spend hours building your own solution? 😄 Second, I dislike how existing scaffold generators add extra boilerplate to files like `build.gradle.kts` that I immediately end up removing. 

**Hidden Agenda:**  
I wanted a practical project to experiment with local LLMs. This project is created using `opencode` driven by `Qwen 3.8 27B`. Developed using techniques like Prompt Engineering and Incremental Prompting; small, iterative steps.

## Prerequisites

- `gradle` CLI (>= 8.2) on your `PATH` — `create_project.py` uses `gradle` to init Gradle related files.
- `uv` — scripts are run with `uv run`.
- Python 3.14 — pinned via `.python-version`.

## How to use?
To create a project, run:
```shell
uv run create_project.py
```

It will prompt you for the project name and package name. You can also pass them directly as arguments:
```shell
uv run create_project.py myapp com.sample.package
```

This will create the project inside the `projects/` directory. 
Example output:
```
Creating project myapp (package com.sample.package) ...
Fetching newest Gradle version...
Gradle version: 9.7.1
Fetching newest Kotlin version...
Kotlin version: 2.4.20
Looking up Java versions for Kotlin 2.4.20...
Java version: 21 (supported: 1.8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26)
Project directory created: projects/myapp
Running 'gradle init' ...
Running 'gradle wrapper' ...
gradle init and wrapper completed.
Populating project files from templates ...
Project files populated.
Project created: projects/myapp
```