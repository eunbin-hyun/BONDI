# UE 5.8.1 + PICO 4 연결·포팅

> Windows PC · 일반 소비자용 PICO 4 · 공통 프로젝트 `VRShared` 기준  
> 확인일: 2026-08-28 · 공식 자료 기준 작성 · 실제 PC·헤드셋 실행 검증 전

[공통 개발환경](unreal-vr-common-setup.md) · [Quest 2 연결·포팅](unreal-quest2-porting.md) · [기기 전환·빌드 관리](unreal-vr-build-management.md)

**개발 준비는 1절, PC 테스트는 2절, 포팅은 3절이다.**

| 목표 | 먼저 할 일 | 이 문서에서 진행 |
| --- | --- | --- |
| **PC VR Preview만 확인** | [공통 프로젝트 준비](unreal-vr-common-setup.md#project) | 1-1의 PC VR 목록 → 1-2 → **2절**. 포팅 3절은 생략 |
| **APK를 넣어 단독 실행** | [공통 Android 도구 준비](unreal-vr-common-setup.md#android-tools)까지 | 1-1의 APK 목록 → 1-3 → **3절**. PC 테스트 2절은 생략 가능 |
| **둘 다 진행** | 위 공통 준비 | 1절의 두 경로 준비 → 2절 → 3절 |

포팅은 이 문서에서 **프로젝트를 헤드셋용 Android 설정으로 바꾸는 것부터 APK 빌드·설치·단독 실행까지**를 뜻한다. VR Preview 성공은 포팅 완료가 아니다.

<a id="setup"></a>

## 1. 기기 개발 준비

<a id="downloads"></a>

### 1-1. 다운로드 목록

#### PC VR용 — 유선 / 무선

| 받을 것 | 링크·준비 |
| --- | --- |
| **PICO Connect — Windows PC용** | [공식 다운로드](https://www.picoxr.com/global/software/pico-link). 같은 페이지에서 PC 요구사항 확인 |
| **Steam** | [공식 다운로드](https://store.steampowered.com/about/) |
| **SteamVR** | [SteamVR 공식 페이지](https://store.steampowered.com/app/250820/SteamVR/). Steam 설치 후 라이브러리에 추가·설치 |
| 헤드셋의 PICO Connect | PICO 4를 업데이트하고 헤드셋의 Connect 앱을 설치·업데이트 |
| 케이블 | USB 데이터 전송이 되는 USB 3 케이블 + PC USB 3 포트 |
| 무선 | 같은 공유기. PC는 랜선, PICO 4는 5GHz Wi-Fi 권장 |

현재 PICO Connect 안내의 기기 요구사항은 **PICO OS 5.11.2 이상**이다. 예전 Streaming Assistant 안내를 섞지 않는다. [PICO Connect 요구사항](https://www.picoxr.com/global/software/pico-link)

#### APK용 — 기기 준비·설치

| 받을 것 | 링크·준비 |
| --- | --- |
| **PICO OpenXR — 공식 플러그인** | [Fab 공식 배포](https://www.fab.com/listings/a7eb0f28-d7f1-4b30-8d2d-49d12eeb1d62). **UE 5.8용** 선택. 편집기 표시명은 **PICO For OpenXR** |
| Android 도구·ADB | [공통 문서 4절](unreal-vr-common-setup.md#android-tools). ADB는 SDK의 `platform-tools`에 포함되어 별도 설치 불필요 |
| USB 데이터 케이블 | APK 전송·USB 디버깅용 |
| PICO Developer Center — 선택 | [공식 도구 페이지](https://developer.picoxr.com/resources/). 이 문서는 ADB로 설치하므로 필수 아님 |

공식 PICO OpenXR 목록은 **UE 5.2–5.8, PICO 4, PICO OS 5.9 이상, 64비트·Vulkan**을 명시한다. **Meta XR나 구형 PICOXR/PXR Integration SDK는 추가하지 않는다.** [PICO OpenXR 요구사항](https://www.fab.com/listings/a7eb0f28-d7f1-4b30-8d2d-49d12eeb1d62)

### 1-2. PC VR용 앱 설치

1. PICO 4 초기 설정·소프트웨어 업데이트 완료. **PICO OS 5.11.2 이상** 확인.
2. PC에 **PICO Connect** 설치.
3. **Steam** 설치·로그인 후 **SteamVR** 설치.
4. 헤드셋의 PICO Connect 앱도 설치·업데이트.
5. 앱이 요청하는 연결 권한은 안내를 확인하고 허용. Windows 방화벽은 끄지 않고 필요한 앱 통신만 허용한다.
6. 설치가 끝나면 **2절**로 이동. 런타임 선택·실제 연결은 그곳에서 진행한다.

### 1-3. APK용 도구·기기 준비

#### PICO OpenXR 엔진 설치

1. 언리얼 에디터 종료.
2. **1-1의 Fab PICO OpenXR**를 Epic 계정의 라이브러리에 추가.
3. **Epic Games Launcher → Unreal Engine → Library → Fab Library**에서 PICO OpenXR 찾기.
4. **Install to Engine → UE 5.8** 선택 후 설치. 설치 대상에 UE 5.8이 없으면 다른 버전 파일을 억지로 넣지 않고 중단한다.
5. **설치까지만 완료한다.** 프로젝트의 PICO For OpenXR 활성화·Android 설정은 포팅 **3절**에서 진행한다.

설치는 엔진에서 플러그인을 사용할 준비이고, 활성화는 해당 프로젝트가 플러그인을 쓰도록 바꾸는 작업이다. [PICO 공식 Quick start](https://developer.picoxr.com/document/unreal-openxr/ue-openxr-quickstart/)

#### 개발자 모드·USB 디버깅 준비

1. 헤드셋 **Settings → General → About** 열기.
2. **Software Version**을 반복 선택해 **Developer** 메뉴가 나타나게 하기.
3. **Developer → USB Debug** ON.
4. PC·헤드셋에서 PICO Connect의 스트리밍 종료.
5. PICO 4를 USB 데이터 케이블로 PC 연결.
6. 헤드셋의 **USB 디버깅 허용** 선택. 항상 허용은 본인이 관리하는 PC에서만 선택.

헤드셋 UI가 바뀌었으면 설정에서 About·Developer 항목을 찾는다. 개발자 모드 활성화 절차는 Meta의 스마트폰 앱 방식과 다르다. [PICO 개발자 모드 안내](https://developer.picoxr.com/document/unreal/test-and-build/)

### 1-4. 개발 준비 완료 확인

- [ ] 공통 프로젝트 `VRShared`가 열린다.
- [ ] PC VR 경로라면 PICO Connect·Steam·SteamVR가 설치되어 있다.
- [ ] APK 경로라면 Android 도구·경로, USB Debug, UE 5.8용 PICO OpenXR 설치를 확인했다.

**여기까지는 개발 세팅이다.** PC VR은 2절, APK만 필요하면 2절을 건너뛰고 3절로 이동한다. APK만 설치할 때는 PICO Connect·SteamVR가 필요 없다.

<a id="pc-preview"></a>

## 2. PC 연결·VR Preview

> PC에서 프로젝트를 실행하고 화면·입력을 헤드셋으로 확인한다. Android APK를 만들거나 설치하는 단계가 아니다.

### 2-1. PC 테스트용 OpenXR 설정

1. 공통 프로젝트 `VRShared`를 연다.
2. **Edit → Plugins → OpenXR** ON 확인.
3. 기본 VR 템플릿의 입력·엔진 내장 **PICO Controller** 설정은 유지.
4. 외부 **Meta XR / OculusXR**, **PICOXR / PXR**, **PICO For OpenXR**는 이번 기본 PC VR 테스트에서 추가하지 않는다.
5. 다른 기기 테스트로 활성화했다면 [빌드 관리 문서](unreal-vr-build-management.md)를 확인해 기본 구성으로 복귀. 재시작 후 **VRTemplateMap** 저장·에디터 종료.

**SteamVR PC 앱을 쓴다고 구형 Unreal SteamVR 플러그인을 따로 설치하는 것은 아니다.** 이 문서의 언리얼 측 연결은 OpenXR이다. [Epic OpenXR 런타임 설정](https://dev.epicgames.com/documentation/unreal-engine/setting-up-virtual-scouting-in-unreal-engine)

활성 런타임은 **SteamVR**를 사용한다. 아래 연결 절차에서 SteamVR를 활성 OpenXR 런타임으로 선택한 뒤 에디터를 연다.

### 2-2. 케이블로 VR Preview

1. PC에서 **PICO Connect** 실행.
2. PICO 4와 PC USB 3 포트를 데이터 케이블로 연결.
3. 헤드셋에서 **PICO Connect** 실행 → 표시된 PC의 **USB/유선 연결** 선택. 앱의 연결 안내 완료.
4. PC에서 **SteamVR** 실행. 헤드셋과 양손 컨트롤러가 연결 상태인지 확인.
5. **SteamVR → Settings → OpenXR → Set SteamVR as OpenXR Runtime** 선택. 이미 SteamVR가 활성 런타임이면 유지.
6. 헤드셋에서 SteamVR 화면이 보이는지 확인.
7. 이제 언리얼에서 **VRShared → VRTemplateMap** 열기.
8. 재생 버튼 옆 메뉴 → **VR Preview** 선택.
9. 시점·양손 컨트롤러·잡기·텔레포트 확인.

**완료:** 헤드셋에 VR 템플릿이 표시되고 입력이 반영된다. Connect 버튼 이름은 앱 버전에 따라 달라질 수 있다. [PICO Connect](https://www.picoxr.com/global/software/pico-link), [SteamVR 활성 OpenXR 설정](https://dev.epicgames.com/documentation/unreal-engine/setting-up-virtual-scouting-in-unreal-engine)

### 2-3. 무선으로 VR Preview

1. VR Preview와 언리얼 에디터 종료.
2. USB 케이블 분리. PC와 PICO 4를 같은 공유기에 연결.
3. **PC는 랜선, PICO 4는 5GHz Wi-Fi** 사용을 권장. 게스트망·기기 간 통신 차단 설정은 피한다.
4. PC와 헤드셋에서 **PICO Connect** 실행.
5. 헤드셋의 PC 목록에서 **무선 연결할 PC** 선택 → 표시되는 페어링·연결 안내 완료.
6. PC에서 SteamVR 실행 → 헤드셋·컨트롤러 연결 확인.
7. **SteamVR → Settings → OpenXR**에서 활성 런타임이 SteamVR인지 확인.
8. 헤드셋에 SteamVR 화면이 보이면 언리얼을 연다.
9. **VRShared → VRTemplateMap → VR Preview** 실행 후 시점·입력 확인.

**완료:** USB 케이블 없이 프리뷰가 실행된다. PICO에서는 Meta의 Air Link가 아니라 **PICO Connect 무선 연결**을 사용한다. [PICO Connect 공식 안내](https://www.picoxr.com/global/software/pico-link)

### 2-4. PC 테스트 완료·문제 해결

| 증상 | 먼저 확인할 것 |
| --- | --- |
| VR Preview가 회색 | PICO Connect 연결 → SteamVR에서 기기 확인 → SteamVR를 OpenXR 런타임으로 선택 → 에디터 다시 열기 |
| Quest 사용 뒤 PICO 프리뷰가 안 됨 | Meta 런타임이 남아 있는지 확인. [PC 기기 전환 절차](unreal-vr-build-management.md#pc-switch) 적용 |
| PDC 미리보기와 Connect가 충돌 | PDC 스트리밍을 종료하고 이번 PC VR 경로의 PICO Connect만 사용 |

PICO는 Connect와 PDC 스트리밍 서비스의 충돌 가능성을 안내한다. [PICO PDC 문제 해결](https://developer.picoxr.com/document/unreal/pdc-faq/)

- [ ] 선택한 유선 또는 무선 프리뷰에서 시점·양손 입력·잡기·텔레포트가 동작한다.

**PC VR Preview만 필요하면 여기서 종료한다. 포팅이 필요한 경우에만 아래 3절로 넘어간다.**

---

<a id="porting"></a>

## 3. 포팅 — 프로젝트 설정·APK 빌드·설치

> **여기서부터 포팅이다.** Android 프로젝트 설정 → APK 빌드 → PICO 4 설치 → PC 없이 실행 순서로 진행한다.

먼저 **1-3의 APK 도구·기기 준비**와 [공통 Android 도구·SDK 경로 설정](unreal-vr-common-setup.md#android-tools)을 완료한다. PC VR 2절의 성공 여부와 관계없이 시작할 수 있다.

UE 5.8에는 PICO 기본 지원도 있지만, **이 문서의 APK 절차는 설정 검사 기능을 이용하는 공식 PICO OpenXR 플러그인 경로로 통일한다.** 기본 엔진 경로와 외부 SDK 경로를 섞지 않는다. [PICO UE 5.8 기본 지원](https://developer.picoxr.com/blog/unreal-engine-ships-with-built-in-pico-support/), [공식 PICO OpenXR 배포·지원 버전](https://www.fab.com/listings/a7eb0f28-d7f1-4b30-8d2d-49d12eeb1d62)

### 3-1. 대상 플러그인 설정

1. 현재 프로젝트를 저장·백업하고 `VRShared`를 연다.
2. **Edit → Plugins → PICO For OpenXR** ON. **OpenXR**도 ON 유지.
3. 외부 **Meta XR / OculusXR**, **구형 PICOXR / PXR**는 OFF. 기존 SDK 노드·클래스가 있다면 [빌드 관리 문서](unreal-vr-build-management.md)의 분리 절차부터 적용.
4. 에디터 재시작. UE 5.8.1에서 모듈 버전 오류가 나면 다른 버전 플러그인 파일을 억지로 넣지 않고 설치 대상·배포본부터 확인.
5. **VRTemplateMap**의 기본 입력을 유지. PICO OpenXR Portal의 입력 검사에서 누락을 지적하면 공식 Quick start의 **controller input mapping** 절차 적용.
6. 아래 **3-2**의 Android 설정을 적용한 뒤 Portal의 프로젝트 검사까지 완료한다.

공식 Quick start의 일부 엔진 예시는 5.6·5.7로 남아 있으므로 **엔진·도구 버전은 UE 5.8 기준과 Fab 설치 대상**을 확인한다. 예전 예시에 맞추려고 엔진을 내리거나 SDK 경로를 덮어쓰지 않는다. [PICO 공식 Quick start·Portal·입력 설정](https://developer.picoxr.com/document/unreal-openxr/ue-openxr-quickstart/)

<a id="android-project"></a>

### 3-2. Android 프로젝트 설정

**Edit → Project Settings → Platforms → Android**를 열고 **Configure Now / Accept SDK License**가 표시되면 먼저 실행한다.

| 항목 | 값 |
| --- | --- |
| Android Package Name | `com.example.vrshared.pico4` |
| Package for Meta Quest devices | **OFF** — 설정 검색창에서 `Meta Quest` 검색 |
| Support arm64 / Support x86_64 | **ON / OFF** |
| Support Vulkan / Support Vulkan Desktop·SM5 | **ON / OFF** |
| Support OpenGL ES3.2 | **OFF** |
| Minimum SDK Version | 새 프로젝트 기본값 유지. **Target SDK와 혼동하여 35로 올리지 않음** |
| Target SDK Version | **35** |
| Package game data inside .apk | **ON** — 작은 VR 템플릿을 APK 하나로 설치 |
| Generate Bundle (AAB) | **OFF** |

이어서 Project Settings 검색창에서 **헤드셋 단독 실행에 사용할 렌더링·시작 맵·빌드 설정**을 적용한다.

| 항목 | 값 |
| --- | --- |
| Start in VR | **ON** |
| Mobile HDR | **OFF** |
| Mobile Multi-View | **ON** |
| Maps & Modes → Game Default Map | **VRTemplateMap** |
| Packaging → Build Configuration | **Development** |
| Packaging → For Distribution | **OFF** |

PICO OpenXR Portal의 설정 안내·프로젝트 검사에서 필수 항목을 확인한다. SDK 경로·버전은 공통 문서의 UE 5.8 조합을 유지하고, 변경된 설정을 확인한 뒤 저장·재시작한다. 이 설정은 작은 VR 템플릿의 로컬 APK 테스트용이며 스토어 제출 설정이 아니다. [Epic Android 프로젝트 설정](https://dev.epicgames.com/documentation/unreal-engine/android-settings-in-the-unreal-engine-project-settings), [Epic XR 권장 설정](https://dev.epicgames.com/documentation/unreal-engine/xr-best-practices-in-unreal-engine)

**이 표는 외부 PICO For OpenXR를 활성화한 구성이다.** 플러그인을 끈 채 표만 적용하는 것은 이 문서의 APK 경로와 다르다. [PICO 설정·패키징 순서](https://developer.picoxr.com/document/unreal-openxr/ue-openxr-quickstart/)

### 3-3. APK 빌드

1. **VRTemplateMap** 저장.
2. **Platforms → Android → Android (ASTC)** 선택.
3. **Package Project** 실행.
4. 출력 위치를 **`C:\UEBuilds\VRShared\PICO4`**로 지정.
5. **Packaging Complete** 확인 후 출력 폴더의 `.apk` 찾기. `Android_ASTC` 하위 폴더에 생성될 수 있다.
6. 빌드 도구가 필요하다는 오류가 나면 [공통 문서 5절](unreal-vr-common-setup.md#cpp-tools)의 C++ 도구 설치 후 재시도.

[Epic Android 패키징](https://dev.epicgames.com/documentation/unreal-engine/packaging-android-projects-in-unreal-engine)

### 3-4. APK 설치·단독 실행

1. Quest·다른 Android 기기를 잠시 분리하고 **PICO 4 한 대만 USB로 연결**. Android 에뮬레이터도 종료.
2. 헤드셋에서 USB 디버깅 허용.
3. Windows **PowerShell**을 열고 아래 첫 줄을 실제 SDK 경로에 맞게 수정해 실행.

```powershell
$VrAdb = 'C:\VRTools\AndroidSDK\platform-tools\adb.exe'
& $VrAdb devices -l
```

4. PICO 한 대가 **`device`** 상태로 표시되는지 확인. `unauthorized`면 헤드셋에서 디버깅 승인. 목록이 비어 있으면 케이블·USB Debug부터 확인.
5. 아래 APK 경로를 **방금 생성된 실제 파일 경로·파일명**으로 바꾸고 실행. 파일명은 프로젝트·빌드 설정에 따라 다르다.

```powershell
$VrApk = 'C:\UEBuilds\VRShared\PICO4\Android_ASTC\VRShared-arm64.apk'
& $VrAdb install -r $VrApk
```

6. **`Success`** 확인. `-r`은 같은 패키지 앱을 재설치하므로 설치 대상을 확인한다.
7. 헤드셋에서 PICO Connect 종료 → USB 분리.
8. 헤드셋의 **라이브러리/앱 목록**에서 `VRShared` 실행. 앱이 안 보이면 알 수 없는 출처·개발자 앱 분류도 확인한다.
9. PC 연결 없이 시점·양손 입력·잡기·텔레포트 확인.

**완료:** PC 스트리밍 없이 PICO 4 자체에서 앱이 실행된다. [Android 공식 ADB 설치 명령](https://developer.android.com/tools/adb), [PICO APK 설치 안내](https://developer.picoxr.com/document/unreal/package-and-install/)

이 절차는 3-2에서 설정한 **작은 APK 하나** 기준이다. OBB가 별도로 생성됐다면 APK만 설치하고 끝내지 말고 동반 데이터 설치도 진행해야 한다. 출력 폴더의 `Install_...bat`를 대안으로 사용할 경우 기존 앱 데이터 초기화 여부를 먼저 확인한다. [Epic Android 설치 안내](https://dev.epicgames.com/documentation/unreal-engine/packaging-android-projects-in-unreal-engine)

### 3-5. 포팅 완료·문제 해결

| 증상 | 먼저 확인할 것 |
| --- | --- |
| ADB가 `unauthorized` | 헤드셋에서 USB 디버깅 승인 |
| `more than one device/emulator` | 다른 기기·에뮬레이터를 분리하거나 [빌드 관리 문서](unreal-vr-build-management.md)의 `-s` 사용 |
| Android 빌드 실패 | [공통 도구·경로](unreal-vr-common-setup.md#android-tools)와 로그의 첫 오류 확인. C++ 도구를 요구하면 [공통 C++ 준비](unreal-vr-common-setup.md#cpp-tools) 진행 |
| APK 설치 시 `OLDER_SDK` | 기기의 Android API와 앱 Minimum SDK 비교. Target SDK를 무작정 낮추지 않음 |
| 시점은 움직이지만 버튼 입력이 안 됨 | VRTemplate 입력·PICO 컨트롤러 매핑·플러그인 검사 확인 |

- [ ] APK 빌드가 성공했다.
- [ ] 설치 대상이 PICO 4인지 확인했고 ADB 설치 결과가 `Success`다.
- [ ] PICO Connect를 종료하고 USB를 분리해도 앱이 실행된다.
- [ ] 헤드셋에서 시점·양손 입력·잡기·텔레포트가 동작한다.

**위 단독 실행 확인까지 통과하면 첫 VR 템플릿 포팅 완료다.** 실제 프로젝트는 모델·머티리얼·코드 플러그인의 Android 호환성과 PICO 4 성능을 별도로 확인한다.
