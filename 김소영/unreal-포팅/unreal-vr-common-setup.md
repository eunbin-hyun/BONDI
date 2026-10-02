# UE 5.8.1 공통 개발환경 — Quest 2 · PICO 4

> Windows PC · Epic Games Launcher의 Unreal Engine 5.8.1 · Blueprint VR 템플릿 기준  
> 확인일: 2026-08-28 · 공식 자료 기준 작성 · 실제 PC·헤드셋 실행 검증 전

## 1. 범위와 읽는 순서

| 문서 | 담당하는 내용 |
| --- | --- |
| **현재 문서 — 공통 개발환경** | 엔진·기본 프로젝트, Android·C++ 도구 설치와 경로 확인까지만 |
| [Quest 2 연결·포팅](unreal-quest2-porting.md) | 1절 개발 준비 → 2절 PC 테스트 → 3절 포팅 |
| [PICO 4 연결·포팅](unreal-pico4-porting.md) | 1절 개발 준비 → 2절 PC 테스트 → 3절 포팅 |
| [기기 전환·빌드 관리](unreal-vr-build-management.md) | 두 기기를 번갈아 테스트할 때의 설정·플러그인·빌드 분리 |

**이 문서는 개발환경 세팅까지만 다룬다.** Android 도구를 설치해도 아직 프로젝트를 헤드셋용으로 포팅한 것은 아니다.

| 단계 | 작업 | 끝났다고 보는 기준 |
| --- | --- | --- |
| **개발 세팅** | 공통 문서 + 기기 문서 1절의 도구·기기 준비 | 기본 프로젝트가 열리고 필요한 도구·경로·권한 준비 완료 |
| **PC 테스트** | 기기 문서 2절의 USB·무선 VR Preview | PC에서 실행한 프로젝트의 화면·입력을 헤드셋으로 확인 |
| **포팅** | 기기 문서 3절의 Android 프로젝트 설정 → APK 빌드 → 설치 | PC 스트리밍을 끊고 헤드셋 자체에서 실행 |

파일명 앞에는 순서 숫자를 붙이지 않았다. **기기 문서는 둘 다 2절까지 PC 테스트, 3절부터 포팅**이다.

| 목표 | 현재 문서에서 할 일 | 다음 작업 |
| --- | --- | --- |
| **PC VR Preview만 확인** | 2절에서 PC VR 항목 확인 → 3절 | 기기 문서 1절의 PC VR 준비 → **2절**. 여기서 종료 가능 |
| **헤드셋에 APK를 넣어 단독 실행** | 2절에서 APK 항목 준비 → 3절 → 4절 | 기기 문서 1절의 APK 준비 → **3절**. PC 테스트 2절은 생략 가능 |
| **C++ 코드·코드 플러그인 빌드** | 위 경로에 5절 추가 | VS Code는 그대로 사용 |

## 2. 다운로드 목록 — 필요한 구역만 준비

### PC VR Preview용

| 받을 것 | 위치·선택 |
| --- | --- |
| UE 5.8.1 | 이미 설치한 엔진 사용. 다시 설치하지 않음 |
| 기기 연결 앱 | [Quest 2 문서의 다운로드 목록](unreal-quest2-porting.md#downloads) 또는 [PICO 4 문서의 다운로드 목록](unreal-pico4-porting.md#downloads)에서 받기 |

**PC VR Preview만 할 때는 Android Studio·SDK·NDK를 설치하지 않는다.** 기본 Blueprint 템플릿부터 시작하고, 빌드 도구를 요구하는 프로젝트·플러그인이 있을 때만 C++ 준비를 추가한다.

### APK 단독 실행용

| 받을 것 | 다운로드 위치 | 선택할 항목 |
| --- | --- | --- |
| 언리얼 Android 지원 | **Epic Games Launcher 내부** | UE 5.8.1 → Options → Target Platforms → Android |
| Android Studio | [공식 버전별 다운로드](https://developer.android.com/studio/archive) | **Koala Feature Drop 2024.1.2 Patch 1**, Windows용 |
| SDK·NDK·Build Tools | 설치한 **Android Studio → SDK Manager 내부** | 아래 4절의 버전 |
| Java / JDK | Koala 설치 폴더에 포함 | **`jbr`** 사용. 별도 Java 다운로드 생략 |
| 기기 설치 도구·플러그인 | 해당 기기 문서의 **1-1 다운로드 목록** | Quest는 MQDH, PICO는 PICO OpenXR 및 이미 설치한 SDK의 ADB 사용 |

**언리얼 Android 지원과 Android Studio는 서로 다른 설치 항목이다.** Android Studio에서는 도구를 준비하고, 프로젝트 제작·APK 빌드는 언리얼에서 진행한다. [Epic Android 준비 안내](https://dev.epicgames.com/documentation/unreal-engine/manual-android-sdk-setup-with-android-studio-for-unreal-engine)

### C++용 — 필요할 때만

| 받을 것 | 다운로드 위치 | 선택할 항목 |
| --- | --- | --- |
| VS Code | [공식 다운로드](https://code.visualstudio.com/Download) | 기존 설치가 있으면 유지 |
| Visual Studio Build Tools | [Microsoft 다운로드](https://visualstudio.microsoft.com/downloads/) → All Downloads → Tools for Visual Studio | **Build Tools for Visual Studio 2026** |
| VS Code 확장 | [C/C++ Extension Pack](https://marketplace.visualstudio.com/items?itemName=ms-vscode.cpptools-extension-pack), [C#](https://marketplace.visualstudio.com/items?itemName=ms-dotnettools.csharp) | 두 확장 설치 |

VS Code는 편집기이고 Build Tools는 컴파일 도구다. **Visual Studio 전체 IDE를 반드시 설치할 필요는 없다.** 이미 호환 C++ 도구가 설치되어 있으면 중복 설치하지 않는다. [Epic VS Code 안내](https://dev.epicgames.com/documentation/unreal-engine/setting-up-visual-studio-code-for-unreal-engine)

<a id="project"></a>

## 3. 공통 VR 프로젝트 만들기

1. UE 5.8.1을 열고 **Games → Virtual Reality** 템플릿 선택.
2. **Blueprint** 프로젝트 생성. 이 문서들의 공통 예시는 `VRShared`이다.
3. **Edit → Plugins**에서 **OpenXR**가 활성화되어 있는지 확인.
4. 템플릿의 다른 기본 플러그인·입력 설정은 유지. 이 단계에서는 외부 **Meta XR, PICO OpenXR, PICOXR/PXR**를 추가하지 않는다.
5. 재시작 안내가 나오면 에디터 재시작.
6. **Content → VRTemplate → Maps → VRTemplateMap**을 열고 저장.

VR 템플릿이 없으면 Launcher의 해당 엔진 **Options → Templates and Feature Packs**를 설치한다. 기본 템플릿은 OpenXR를 사용한다. [Epic VR 템플릿](https://dev.epicgames.com/documentation/unreal-engine/vr-template-in-unreal-engine), [PICO의 UE 5.8 기본 지원 안내](https://developer.picoxr.com/blog/unreal-engine-ships-with-built-in-pico-support/)

**PC VR만 할 경우 기기 문서 1절의 PC VR 준비 → 2절로 이동한다. APK가 필요할 때만 아래 4절을 진행한다.**

<a id="android-tools"></a>

## 4. Android 빌드 도구 설치·경로 확인 — APK가 필요할 때만

### 4-1. 언리얼 Android 지원 설치

1. **Epic Games Launcher → Unreal Engine → Library** 열기.
2. UE 5.8.1 옆 메뉴에서 **Options → Target Platforms → Android** 체크.
3. **Apply**를 누르고 완료될 때까지 기다리기.
4. 언리얼 에디터와 Launcher 종료.

### 4-2. Android Studio와 SDK 설치

1. 받은 **Koala Feature Drop 2024.1.2 Patch 1** 설치 파일 실행.
2. 기존 Android Studio가 있으면 삭제하지 않는다. 별도 설치 위치를 선택하고 기록한다. 예: `C:\VRTools\AndroidStudio-Koala`.
3. 초기 설정 완료 후 **More Actions → SDK Manager** 열기. 프로젝트가 열려 있으면 **Tools → SDK Manager** 사용.
4. **Android SDK Location**을 확인·기록한다. 기존 Unity 도구와 분리할 경우 예: `C:\VRTools\AndroidSDK`.
5. **SDK Platforms → Android 15 / API 35** 설치. 에뮬레이터용 시스템 이미지는 생략 가능.
6. **SDK Tools → Show Package Details**를 켜고 아래 항목 선택.

| 항목 | UE 5.8 기준 |
| --- | --- |
| Android SDK Build-Tools | **35.0.1** |
| NDK (Side by side) | **27.2.12479018 — r27c** |
| Android SDK Platform-Tools | 설치. `adb.exe` 포함 |
| Android SDK Command-line Tools | 설치 |
| Java / JDK | Koala의 **`jbr`**, 요구 버전 **OpenJDK 21.0.3** |

7. **Apply → 라이선스 동의 → 설치 완료**까지 진행.
8. SDK·NDK·JDK 경로를 기록하고 Android Studio 종료.

기존 Unity용 SDK·NDK, `JAVA_HOME` 등 시스템 환경변수를 임의로 삭제·변경하지 않는다. 최신 Android Studio를 무조건 받지 말고 위 조합을 맞춘다. [Epic UE 5.8 Android 요구사항](https://dev.epicgames.com/documentation/unreal-engine/android-development-requirements-for-unreal-engine), [Epic 수동 SDK 설치](https://dev.epicgames.com/documentation/unreal-engine/manual-android-sdk-setup-with-android-studio-for-unreal-engine)

<a id="sdk-paths"></a>

### 4-3. 언리얼에 도구 경로 지정

프로젝트에서 **Edit → Project Settings → Platforms → Android SDK**를 열어 실제 설치 경로를 지정한다.

| 항목 | 위 예시대로 설치했을 때 |
| --- | --- |
| SDK | `C:\VRTools\AndroidSDK` |
| NDK | `C:\VRTools\AndroidSDK\ndk\27.2.12479018` |
| JAVA | `C:\VRTools\AndroidStudio-Koala\jbr` |
| SDK API Level | `android-35` |
| NDK API Level | 새 UE 5.8.1 프로젝트 기본값 유지 |

다른 곳에 설치했다면 예시 경로를 그대로 입력하지 않는다. 저장·재시작 후 **Platforms → SDK Management → Android**에서 SDK 상태를 확인한다. 오류가 남으면 패키징 전에 경로·설치 버전을 수정한다. [Epic Android SDK 설정](https://dev.epicgames.com/documentation/unreal-engine/android-sdk-settings-in-the-unreal-engine-project-settings)

**Android 도구 준비는 여기까지다.** 패키지명·Vulkan·arm64·Mobile HDR 등 APK 프로젝트 설정은 여기서 변경하지 않고, 해당 기기 문서 **3-2 Android 프로젝트 설정**에서 진행한다.

<a id="cpp-tools"></a>

## 5. C++ 빌드 도구 설치 — VS Code 유지

C++ 프로젝트를 만들거나 코드 플러그인 때문에 빌드 도구를 요구할 때 진행한다.

1. **Build Tools for Visual Studio 2026** 설치 파일 실행.
2. Installer의 **Workloads → Desktop development with C++** 선택.
3. **Individual components**에서 **MSVC x64/x86 빌드 도구**와 **Windows SDK** 확인. UE 5.8 권장값은 **MSVC 14.50**, **Windows SDK 10.0.26100 이상**.
4. 설치 완료 후 재부팅 안내가 있으면 재부팅.
5. VS Code에 **C/C++ Extension Pack**, **C#** 확장 설치.
6. 언리얼에서 **Edit → Editor Preferences → General → Source Code → Source Code Editor → Visual Studio Code** 선택 후 재시작.
7. **Tools → Refresh Visual Studio Code Project** 실행.
8. 프로젝트의 **`.code-workspace`** 파일을 VS Code로 열기.

이미 **Visual Studio 2022 17.14 이상** 또는 **Visual Studio 2026 18.0 이상**에 호환 C++ 도구가 있으면 중복 설치를 생략한다. APK용 C++ 컴파일에는 4절의 Android NDK도 필요하다. [Epic 컴파일러 요구사항](https://dev.epicgames.com/documentation/unreal-engine/setting-up-visual-studio-development-environment-for-cplusplus-projects-in-unreal-engine), [Epic VS Code 설정](https://dev.epicgames.com/documentation/unreal-engine/setting-up-visual-studio-code-for-unreal-engine)

## 6. 개발환경 세팅 완료

- [ ] UE 5.8.1에서 `VRShared`의 `VRTemplateMap`이 열린다.
- [ ] PC VR만 할 경우 Android·C++ 도구를 불필요하게 추가하지 않았다.
- [ ] APK가 필요하면 Android 도구 버전·경로와 SDK 상태를 확인했다.
- [ ] C++·코드 플러그인 빌드가 필요하면 빌드 도구를 준비했다.

**여기까지는 개발환경 준비이며, 포팅 완료가 아니다.** 다음으로 [Quest 2 개발 준비](unreal-quest2-porting.md#setup) 또는 [PICO 4 개발 준비](unreal-pico4-porting.md#setup)를 진행한다. PC 테스트만 할 사람은 기기 문서 2절까지, APK가 필요한 사람은 3절까지 진행한다.
