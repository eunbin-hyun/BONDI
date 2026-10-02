# UE 5.8.1 + Meta Quest 2 연결·포팅

> Windows PC · Meta Quest 2 · 공통 프로젝트 `VRShared` 기준  
> 확인일: 2026-08-28 · 공식 자료 기준 작성 · 실제 PC·헤드셋 실행 검증 전

[공통 개발환경](unreal-vr-common-setup.md) · [PICO 4 연결·포팅](unreal-pico4-porting.md) · [기기 전환·빌드 관리](unreal-vr-build-management.md)

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

#### PC VR용 — USB Link / Air Link

| 받을 것 | 링크·준비 |
| --- | --- |
| **Meta Horizon Link — PC 앱** | [공식 다운로드](https://www.meta.com/help/quest/1517439565442928/) → Download app |
| PC 호환성 확인 | [Meta Link PC 요구사항](https://www.meta.com/help/quest/140991407990979/)에서 GPU·운영체제 확인 |
| 케이블 | **USB 데이터 전송이 되는 USB 3 케이블 + PC USB 3 포트** |
| 무선 | 같은 공유기. PC는 랜선, Quest 2는 5GHz Wi-Fi 권장 |

#### APK용 — 기기 준비·설치

| 받을 것 | 링크·준비 |
| --- | --- |
| **Meta Horizon — 스마트폰 앱** | [Android](https://play.google.com/store/apps/details?id=com.oculus.twilight) / [iPhone](https://apps.apple.com/us/app/meta-horizon/id1366478176). 기존 페어링이 되어 있으면 유지 |
| **Meta Quest Developer Hub — MQDH** | [Windows 공식 다운로드](https://developers.meta.com/horizon/downloads/package/oculus-developer-hub-win/) |
| ADB 드라이버 — 인식 오류 시 | [Meta 공식 다운로드](https://developers.meta.com/horizon/downloads/package/oculus-adb-drivers/) |
| Android 도구 | [공통 문서 4절](unreal-vr-common-setup.md#android-tools)에서 준비. 이미 준비했다면 재설치하지 않음 |
| 케이블 | USB 데이터 케이블. 충전 전용 케이블은 사용하지 않음 |

**별도 Meta XR 플러그인은 받지 않는다.** 이 문서는 엔진 기본 OpenXR로 시작한다.

**Meta Horizon Link는 언리얼과 별도로 설치하는 PC 연결 앱이다.** APK만 설치할 경우 Link는 필요 없다.

### 1-2. PC VR용 앱 설치

1. Quest 2 초기 설정을 마치고 헤드셋 소프트웨어 업데이트.
2. PC에 **Meta Horizon Link** 설치 후 Meta 계정 로그인.
3. 설치가 끝나면 **2절**로 이동. 런타임 선택·실제 연결은 그곳에서 진행한다.

### 1-3. APK용 도구·기기 준비

1. PC에 **MQDH** 설치.
2. [Meta 개발 설정 안내](https://developers.meta.com/horizon/documentation/unreal/unreal-quick-start-config-headset/)에 따라 개발자 등록·계정 인증.
3. 스마트폰 **Meta Horizon → Quest 2 → Headset Settings → Developer Mode** ON.
4. 헤드셋에서 Link를 종료하고 USB 데이터 케이블로 PC 연결.
5. 헤드셋의 **USB 디버깅 허용** 선택. “이 컴퓨터에서 항상 허용”은 본인이 관리하는 PC에서만 선택.
6. MQDH에 개발자 계정으로 로그인하고 **Device Manager**에서 Quest 2 확인.
7. 인식되지 않으면 다운로드한 ADB 드라이버의 **`android_winusb.inf` → 우클릭 → 설치** 후 재연결. Windows 11은 “더 많은 옵션 표시”에 메뉴가 있을 수 있다.

### 1-4. 개발 준비 완료 확인

- [ ] 공통 프로젝트 `VRShared`가 열린다.
- [ ] PC VR 경로라면 Meta Horizon Link가 설치되어 있다.
- [ ] APK 경로라면 Android 도구·경로, 개발자 모드, MQDH 기기 인식을 확인했다.

**여기까지는 개발 세팅이다.** PC VR은 2절, APK만 필요하면 2절을 건너뛰고 3절로 이동한다.

<a id="pc-preview"></a>

## 2. PC 연결·VR Preview

> PC에서 프로젝트를 실행하고 화면·입력을 헤드셋으로 확인한다. Android APK를 만들거나 설치하는 단계가 아니다.

### 2-1. PC 테스트용 OpenXR 설정

1. 공통 문서에서 만든 `VRShared`를 연다.
2. **Edit → Plugins → OpenXR** ON 확인. 템플릿 기본 입력·기본 OpenXR 확장은 유지.
3. 이번 기본 PC VR 구성에서는 외부 **Meta XR / OculusXR**, **PICO For OpenXR**, **PICOXR / PXR**를 추가하지 않는다. 이전 테스트로 켰다면 아래 주의사항을 확인하고 기본 구성으로 복귀.
4. 필요한 플러그인 변경 후 재시작하고 **VRTemplateMap** 저장·에디터 종료.
5. PC의 **Meta Horizon Link → Settings → General → Unknown Sources** ON. 개발 중인 신뢰하는 앱 실행에만 사용한다.
6. 같은 화면의 **OpenXR Runtime → Set Meta Horizon Link as active** 선택. 이미 활성 상태면 유지.
7. 아래 케이블 또는 무선 연결을 완료한 뒤 언리얼을 다시 연다.

기존 프로젝트가 외부 SDK의 Blueprint 노드·C++ 클래스를 사용하면 곧바로 플러그인을 끄지 말고 [빌드 관리 문서](unreal-vr-build-management.md)의 분리 절차를 따른다. 엔진 내장 **PICO Controller**는 외부 **PICO For OpenXR**와 다른 플러그인이므로 이름만 보고 끄지 않는다.

[Meta 개발 앱 실행 설정](https://developers.meta.com/horizon/documentation/unreal/unreal-quick-start-config-headset/), [Meta OpenXR 런타임 설정](https://developers.meta.com/horizon/documentation/unreal/unreal-link/)

### 2-2. 케이블로 VR Preview

1. PC에서 **Meta Horizon Link** 실행.
2. Quest 2와 PC USB 3 포트를 데이터 케이블로 연결.
3. PC 앱 **Devices**에서 Quest 2 확인. 처음이면 기기 추가 안내 완료.
4. 헤드셋에서 **Meta/Oculus 버튼 → Quick controls(빠른 설정) → Link** 열기.
5. **Use Air Link**가 켜져 있으면 OFF.
6. PC 선택 → **Launch**. Link 환경에 들어왔는지 확인.
7. 이제 언리얼에서 **VRShared → VRTemplateMap** 열기.
8. 재생 버튼 옆 메뉴 → **VR Preview** 선택.
9. 고개 회전·위치 이동, 양손 컨트롤러, 잡기·텔레포트 확인.

**완료:** 헤드셋에 VR 템플릿이 표시되고 시점·입력이 반영된다. [Meta USB Link 연결](https://www.meta.com/help/quest/509273027107091/), [언리얼 Link 프리뷰](https://developers.meta.com/horizon/documentation/unreal/unreal-link/)

### 2-3. 무선으로 VR Preview

1. VR Preview와 언리얼 에디터 종료.
2. PC에서 **Meta Horizon Link** 실행.
3. PC와 Quest 2를 같은 공유기에 연결. **PC는 랜선, Quest 2는 5GHz Wi-Fi** 권장.
4. 헤드셋 **Meta/Oculus 버튼 → Quick controls → Link** 열기.
5. **Use Air Link** ON → PC 선택 → **Pair**.
6. PC·헤드셋의 코드 일치 확인 → PC에서 **Confirm**.
7. 헤드셋에서 **Launch**. 이후 연결부터는 최초 페어링 단계를 생략할 수 있다.
8. 언리얼에서 **VRShared → VRTemplateMap → VR Preview** 실행.
9. 시점·컨트롤러·잡기·텔레포트 확인.

**완료:** USB 케이블 없이 프리뷰가 실행된다. [Meta Air Link 연결](https://www.meta.com/help/quest/509273027107091/), [무선 네트워크 점검](https://www.meta.com/help/quest/975178886590868/)

헤드셋 메뉴가 다르면 **Settings → System → Quest Link**에서 연결 화면을 찾는다. [Meta 메뉴 안내](https://developers.meta.com/horizon/documentation/unreal/unreal-link/)

### 2-4. PC 테스트 완료·문제 해결

| 증상 | 먼저 확인할 것 |
| --- | --- |
| VR Preview가 회색 | Link 연결 완료 → Meta가 활성 OpenXR 런타임인지 확인 → 에디터 다시 열기 |
| PICO 사용 뒤 Quest 프리뷰가 안 됨 | SteamVR 대신 Meta 런타임 선택. [PC 기기 전환 절차](unreal-vr-build-management.md#pc-switch) 확인 |

- [ ] 선택한 USB 또는 무선 프리뷰에서 시점·양손 입력·잡기·텔레포트가 동작한다.

**PC VR Preview만 필요하면 여기서 종료한다. 포팅이 필요한 경우에만 아래 3절로 넘어간다.**

**Link 대안은 선택 사항이다.** 기본 연결이 되면 별도 대안 문서를 볼 필요 없다. Steam Link·Virtual Desktop 비교는 기존 [PC VR 대안 문서](quest2-pcvr-alternatives.md)에 두고 필수 설치 순서에는 포함하지 않는다.

---

<a id="porting"></a>

## 3. 포팅 — 프로젝트 설정·APK 빌드·설치

> **여기서부터 포팅이다.** Android 프로젝트 설정 → APK 빌드 → Quest 2 설치 → PC 없이 실행 순서로 진행한다.

먼저 **1-3의 APK 도구·기기 준비**와 [공통 Android 도구·SDK 경로 설정](unreal-vr-common-setup.md#android-tools)을 완료한다. PC VR 2절의 성공 여부와 관계없이 시작할 수 있다.

### 3-1. 대상 플러그인 설정

1. 현재 프로젝트를 저장·백업하고 `VRShared`를 연다.
2. **Edit → Plugins → OpenXR** ON.
3. 이번 Quest APK 구성은 외부 **Meta XR / OculusXR**, **PICO For OpenXR**, **PICOXR / PXR**를 사용하지 않는다. 새로 설치하지 말고, 활성화된 항목은 SDK 참조 여부를 확인한 뒤 비활성화한다.
4. 플러그인 변경 후 에디터 재시작. 기존 SDK 노드·클래스가 있다면 [빌드 관리 문서](unreal-vr-build-management.md)의 분리 절차부터 적용.

Meta XR 다운로드 페이지에서 확인한 v205.0은 UE 5.7.4용이다. 이를 UE 5.8.1용으로 간주하여 설치하지 않는다. [Meta XR 배포 정보](https://developers.meta.com/horizon/downloads/package/unreal-engine-5-integration/)

<a id="android-project"></a>

### 3-2. Android 프로젝트 설정

**Edit → Project Settings → Platforms → Android**를 열고 **Configure Now / Accept SDK License**가 표시되면 먼저 실행한다.

| 항목 | 값 |
| --- | --- |
| Android Package Name | `com.example.vrshared.quest2` |
| Package for Meta Quest devices | **ON** — 설정 검색창에서 `Meta Quest` 검색 |
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

저장하고 에디터를 재시작한다. 이 설정은 작은 VR 템플릿의 로컬 APK 테스트용이며 스토어 제출 설정이 아니다. [Epic Android 프로젝트 설정](https://dev.epicgames.com/documentation/unreal-engine/android-settings-in-the-unreal-engine-project-settings), [Epic XR 권장 설정](https://dev.epicgames.com/documentation/unreal-engine/xr-best-practices-in-unreal-engine)

[Meta Quest 패키징 옵션](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-5.3-release-notes?application_version=5.3)

### 3-3. APK 빌드

1. **VRTemplateMap**을 열고 저장.
2. 상단 **Platforms → Android → Android (ASTC)** 선택.
3. **Package Project** 실행.
4. 출력 위치를 **`C:\UEBuilds\VRShared\Quest2`**로 지정.
5. **Packaging Complete** 확인 후 출력 폴더의 `.apk` 찾기. `Android_ASTC` 하위 폴더에 생성될 수 있다.

[Epic Android 패키징](https://dev.epicgames.com/documentation/unreal-engine/packaging-android-projects-in-unreal-engine)

### 3-4. APK 설치·단독 실행

1. Quest 2를 USB로 연결하고 디버깅 허용.
2. **MQDH → Device Manager → 설치할 Quest 2 → Apps → Add Build** 선택.
3. 방금 만든 APK를 선택하거나 Apps 영역에 드래그.
4. 설치 완료 확인. 같은 패키지명의 앱은 업데이트되므로 설치 대상 확인.
5. 헤드셋에서 Link 종료 → USB 분리.
6. **앱 목록 → Unknown Sources(알 수 없는 출처)**에서 `VRShared` 실행. OS에 따라 앱 필터·왼쪽 메뉴에 표시된다.
7. PC 연결 없이 시점·양손 입력·잡기·텔레포트 확인.

**완료:** PC 스트리밍 없이 Quest 2 자체에서 앱이 실행된다. [MQDH APK 설치 안내](https://developers.meta.com/horizon/documentation/unreal/ts-mqdh-deploy-build/)

MQDH 대신 출력 폴더의 `Install_...bat`를 사용할 수도 있다. 두 방법을 모두 실행할 필요는 없다. 배치 파일 재설치는 기존 테스트 앱 데이터를 초기화할 수 있으므로 내용을 확인하고 사용한다. [Epic 설치 배치 파일 안내](https://dev.epicgames.com/documentation/unreal-engine/packaging-android-projects-in-unreal-engine)

### 3-5. 포팅 완료·문제 해결

| 증상 | 먼저 확인할 것 |
| --- | --- |
| MQDH에서 기기가 안 보임 | 개발자 모드·헤드셋의 USB 디버깅 승인·데이터 케이블·ADB 드라이버 |
| Android 빌드 실패 | [공통 도구·경로](unreal-vr-common-setup.md#android-tools)와 로그의 첫 오류 확인. C++ 도구를 요구하면 [공통 C++ 준비](unreal-vr-common-setup.md#cpp-tools) 진행 |
| 설치는 되지만 실행 실패 | 3-2의 Quest 패키징 옵션·기본 맵·외부 SDK 참조·기기 로그 확인 |

- [ ] APK 빌드가 성공했다.
- [ ] 설치 대상이 Quest 2인지 확인했고 APK 설치가 완료됐다.
- [ ] Link를 종료하고 USB를 분리해도 앱이 실행된다.
- [ ] 헤드셋에서 시점·양손 입력·잡기·텔레포트가 동작한다.

**위 단독 실행 확인까지 통과하면 첫 VR 템플릿 포팅 완료다.** 실제 프로젝트는 모델·머티리얼·코드 플러그인의 Android 호환성과 Quest 2 성능을 별도로 확인한다.
