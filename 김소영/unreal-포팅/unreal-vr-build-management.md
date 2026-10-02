# UE 5.8.1 — Quest 2·PICO 4 전환과 빌드 관리

> Windows PC · Meta Quest 2 · PICO 4 · 로컬 테스트용  
> 확인일: 2026-08-28 · 문서·보고 사례를 구분해 정리 · 실제 두 기기 교차 실행 검증 전

[공통 개발환경](unreal-vr-common-setup.md) · [Quest 2 연결·포팅](unreal-quest2-porting.md) · [PICO 4 연결·포팅](unreal-pico4-porting.md)

## 1. 이 문서의 기본 운영 방식

**콘텐츠와 공통 코드는 공유하고, 기기별 설정·APK·검증 결과를 구분한다. 처음에는 한 번에 한 기기만 빌드한다.**

개발환경 설치는 [공통 문서](unreal-vr-common-setup.md)와 각 기기 문서의 **1절**에서 끝낸다. 이 문서는 그다음 **PC 테스트 전환**과 **포팅 대상 전환**을 관리한다.

| 작업 | 기기 문서의 위치 | 이 문서에서 볼 곳 |
| --- | --- | --- |
| PC 연결·VR Preview | 각 기기 문서 **2절** | 아래 **2절 PC 기기 전환** |
| Android 설정·APK 빌드·설치 | 각 기기 문서 **3절부터 포팅** | 아래 **3절 APK 대상 전환** |

아래 표의 PC 런타임은 PC 테스트에서, APK 플러그인·패키징 옵션·패키지명은 포팅에서 적용한다.

| 구분 | Quest 2 | PICO 4 |
| --- | --- | --- |
| 공통 콘텐츠·입력 | `VRShared`의 맵·공통 Blueprint·OpenXR 입력 | 동일 |
| PC 연결 | Meta Horizon Link | PICO Connect + SteamVR |
| PC 활성 OpenXR 런타임 | Meta Horizon Link | SteamVR |
| 기본 PC VR 플러그인 | 엔진 OpenXR | 엔진 OpenXR |
| 이 문서들의 APK 플러그인 | 엔진 OpenXR, 외부 Meta XR 미사용 | 엔진 OpenXR + 외부 **PICO For OpenXR** |
| Package for Meta Quest devices | ON | OFF |
| 테스트 패키지명 | `com.example.vrshared.quest2` | `com.example.vrshared.pico4` |
| APK 출력 | `C:\UEBuilds\VRShared\Quest2` | `C:\UEBuilds\VRShared\PICO4` |
| 설치 도구 | MQDH | SDK의 ADB |

**PC 런타임을 바꾸는 것과 Android APK 구성을 바꾸는 것은 별개다.** SteamVR를 활성화한다고 APK가 PICO용으로 바뀌지 않는다. 두 기기가 모두 Android이므로 “Android 선택”만으로 제조사가 구분되지도 않는다.

엔진 내장 **PICO Controller**는 입력 확장이고, 별도 설치하는 **PICO For OpenXR**는 PICO SDK 플러그인이다. 이름이 비슷해도 같은 항목이 아니다. [UE 5.8 PICO 기본 지원](https://developer.picoxr.com/blog/unreal-engine-ships-with-built-in-pico-support/), [PICO OpenXR SDK](https://www.fab.com/listings/a7eb0f28-d7f1-4b30-8d2d-49d12eeb1d62)

<a id="pc-switch"></a>

## 2. PC VR Preview 기기 바꾸기

### Quest 2 → PICO 4

1. VR Preview와 언리얼 에디터 종료.
2. Quest Link 세션 종료. 이번 테스트에 쓰지 않는 연결 앱은 종료.
3. PICO Connect로 PICO 4 연결 → SteamVR에서 헤드셋·컨트롤러 확인.
4. **SteamVR → Settings → OpenXR → Set SteamVR as OpenXR Runtime** 선택.
5. 기본 PC VR 구성으로 외부 SDK 활성화 상태 확인.
6. 언리얼을 다시 열고 **VRTemplateMap → VR Preview** 실행.

### PICO 4 → Quest 2

1. VR Preview와 언리얼 에디터 종료.
2. PICO Connect 스트리밍·SteamVR 종료.
3. **Meta Horizon Link → Settings → General → OpenXR Runtime → Set Meta Horizon Link as active** 선택.
4. Quest 2에서 USB Link 또는 Air Link 연결.
5. 기본 PC VR 구성으로 외부 SDK 활성화 상태 확인.
6. 언리얼을 다시 열고 **VRTemplateMap → VR Preview** 실행.

런타임 변경 뒤 에디터를 다시 열어야 기존 연결 상태를 이어 쓰는 혼동을 줄일 수 있다. [Epic 런타임 선택](https://dev.epicgames.com/documentation/unreal-engine/setting-up-virtual-scouting-in-unreal-engine), [Meta Link 개발 안내](https://developers.meta.com/horizon/documentation/unreal/unreal-link/)

<a id="apk-switch"></a>

## 3. 같은 프로젝트에서 APK 대상을 바꾸기

처음 만든 VR 템플릿처럼 **제조사 전용 SDK 노드·클래스를 아직 사용하지 않는 경우**의 수동 절차다.

1. 현재 작업을 저장하고 Git 커밋 또는 프로젝트 백업.
2. 이전 빌드가 끝났는지 확인하고 VR Preview 종료.
3. **Edit → Plugins**에서 아래 대상 구성 적용.
4. 에디터 재시작.
5. [Quest 2 포팅](unreal-quest2-porting.md#porting) 또는 [PICO 4 포팅](unreal-pico4-porting.md#porting)의 **3-1 대상 플러그인 설정 → 3-2 Android 프로젝트 설정** 적용. PICO는 Portal 검사도 완료.
6. 공통 SDK·NDK·JDK 경로가 바뀌지 않았는지 확인하고, Android 프로젝트 설정은 선택한 기기의 **3-2**와 대조.
7. 출력 폴더를 기기별로 지정하고 **한 기기씩** 패키징.
8. APK 생성 시각·패키지명 확인 후 대상 기기에 설치.
9. PC 연결을 끊어 단독 실행하고 아래 7절에 결과 기록.

| 외부 플러그인 | Quest APK 구성 | PICO APK 구성 |
| --- | --- | --- |
| 엔진 OpenXR | ON | ON |
| Meta XR / OculusXR | OFF / 미설치 | OFF / 미설치 |
| PICO For OpenXR | OFF / 미설치 | ON — UE 5.8용 |
| 구형 PICOXR / PXR Integration SDK | OFF / 미설치 | OFF / 미설치 |

**이 표는 이번 가이드가 선택한 테스트 구성이다. 모든 Meta·PICO OpenXR 확장 조합이 원천적으로 충돌한다는 뜻은 아니다.**

출력 폴더만 분리해도 **프로젝트 플러그인·설정·Intermediate가 분리되는 것은 아니다.** Project Launcher 프로필도 만들기만 하면 제조사별 `.uproject`·설정을 자동 교체해 주는 것으로 간주하지 않는다.

## 4. 전용 SDK를 쓰기 시작하거나 병렬 빌드가 필요할 때

Meta 전용 노드, PICO 전용 클래스가 콘텐츠·코드에 들어가면 단순 ON/OFF만으로 전환하지 않는다. 비활성화한 플러그인의 클래스가 참조되어 프로젝트 로딩·컴파일·Cook이 실패할 수 있다.

1. 공통 로직·콘텐츠와 제조사 전용 기능을 구분한다.
2. 제조사 기능은 별도 모듈·플러그인·대상별 콘텐츠에 두고, 공통 코드가 특정 SDK 클래스를 항상 요구하지 않도록 설계한다.
3. Git을 쓰면 같은 저장소의 **별도 worktree**, 쓰지 않으면 별도 작업 복사본을 만든다. 복사본은 빌드용으로 관리하고 공통 콘텐츠 변경은 원본에 반영한다.
4. 각 작업 폴더에서 기기별 플러그인·설정·패키지명을 명시적으로 적용한다. worktree 생성만으로 대상 설정이 바뀌지는 않는다.
5. **각각의 Intermediate·Binaries·Saved·출력 경로**를 사용한다. 공통 원본 폴더에 두 빌드를 동시에 실행하지 않는다.
6. 기기별 실기 테스트가 모두 통과한 뒤 필요한 범위만 자동화한다.

| 작업 폴더 예시 | 용도 | 출력 폴더 |
| --- | --- | --- |
| `C:\UEWork\VRShared-Quest2` | Quest 대상 구성·중간 파일 | `C:\UEBuilds\VRShared\Quest2` |
| `C:\UEWork\VRShared-PICO4` | PICO 대상 구성·중간 파일 | `C:\UEBuilds\VRShared\PICO4` |

엔진 `Engine\Plugins`에 설치한 플러그인은 여러 작업 폴더가 같은 설치본을 사용할 수 있다. **병렬 작업 중 엔진·공유 플러그인을 업데이트하지 않는다.** 프로젝트와 엔진 양쪽에 동일 플러그인을 중복 배치하지 않는다.

## 5. 확인한 충돌 조건과 보고 사례

| 구분 | 확인 내용 | 이 문서의 대응 |
| --- | --- | --- |
| **공식 안내** | PICO 구형 **PXR**와 **OpenXR** 경로는 함께 사용하지 않도록 안내됨 | PICO APK는 PICO For OpenXR 경로 하나로 통일 |
| **공식 안내** | Meta의 **Epic Native OpenXR** 확장 경로와 기존 OVR 기반 경로는 다름 | “Meta XR”라는 이름만 보고 모든 OpenXR 확장이 충돌한다고 단정하지 않음 |
| **개발자 보고 — UE 5.6** | PICO OpenXR 빌드에서 `xmlns:android` 중복 속성으로 Manifest 생성 실패 사례 | 5.8.1에서도 동일하다고 단정하지 않음. 같은 오류가 실제로 나올 때 로그·버전·Manifest 생성 경로 확인 |
| **공식 도구 문제 안내** | PICO Connect와 PDC 스트리밍 서비스가 충돌할 수 있음 | PC VR와 기기 디버깅에서 필요한 스트리밍 도구만 실행 |
| **작업 방식상 위험** | 같은 작업 폴더에서 설정 변경·패키징을 동시에 수행 | 처음에는 순차 빌드. 병렬화 시 별도 작업 폴더 |

[PICO PXR·OpenXR 비교](https://developer.picoxr.com/blog/unreal-openxr-plugin15/), [Meta Native OpenXR 안내](https://developers.meta.com/horizon/documentation/unreal/unreal-openxr/), [UE 5.6 Manifest 오류의 개발자 보고](https://forums.unrealengine.com/t/ue-5-6-pico-openxr-xmlns-android-is-a-duplicate-attribute-name-full-breakdown-and-working-fix/2729313), [PICO PDC 문제 해결](https://developer.picoxr.com/document/unreal/pdc-faq/)

**기억하고 있던 “둘 다 빌드할 때 나는 버그”의 정확한 오류는 아직 특정되지 않았다.** 위 항목을 그 버그의 확정 원인으로 보지 않는다. UE 5.6 사례를 따라 UE 5.8.1 엔진 소스나 Manifest를 먼저 수정하지 않는다.

### 한 APK로 두 기기에서 실행하면 안 되나?

가능한 구성이 있다. PICO는 OpenXR 기반으로 여러 제조사 기기에서 실행하는 단일 APK 경로도 설명한다. 다만 제조사 확장·입력·권한·서비스가 모두 자동으로 호환되는 것은 아니다. **지금은 기기별 APK를 각각 확인하고, 이후 동일 APK를 두 기기에서 별도로 검증하는 순서**로 진행한다. [PICO OpenXR 교차 기기 설명](https://developer.picoxr.com/blog/unreal-openxr-plugin15/)

## 6. 실패했을 때 확인 순서

1. **어느 단계인지 구분:** PC 연결 / VR Preview / 패키징 / APK 설치 / 기기 실행.
2. 언리얼 **Output Log**에서 마지막 `Unknown Error`만 보지 말고 그 앞의 첫 오류를 기록한다.
3. SDK·NDK·JDK와 엔진·플러그인 버전을 확인한다.
4. 대상 기기·패키지명·플러그인 구성을 확인한다.
5. 변경하기 전에 `Saved\Logs`와 실패한 빌드 로그를 보관한다.
6. 설정을 고쳤는데 생성 파일이 남아 있는 정황이 있을 때만 에디터를 종료하고 **해당 작업 폴더의 `Intermediate\Android`**를 정리해 재빌드한다.
7. `Content`, `Config`, 서명 키, `Saved` 전체를 일괄 삭제하지 않는다. 외부 다운로드 DLL·엔진 패치를 첫 해결책으로 적용하지 않는다.

### ADB에서 두 기기가 동시에 연결된 경우

PowerShell에서 아래 경로·시리얼·APK 경로를 실제 값으로 바꾼다.

```powershell
$VrAdb = 'C:\VRTools\AndroidSDK\platform-tools\adb.exe'
& $VrAdb devices -l
& $VrAdb -s '설치할_기기의_시리얼' install -r 'C:\UEBuilds\대상기기\실제파일.apk'
```

`-s`로 설치 대상을 지정한다. `unauthorized`는 헤드셋에서 USB 디버깅 승인이 필요한 상태다. [Android ADB 기기 선택·설치](https://developer.android.com/tools/adb)

| 설치 오류 예 | 대응 |
| --- | --- |
| `INSTALL_FAILED_UPDATE_INCOMPATIBLE` | 기존 앱과 서명이 다른지 확인. 기존 서명으로 빌드하거나 테스트 앱 삭제를 선택. **삭제 시 앱 데이터가 사라질 수 있음** |
| `INSTALL_FAILED_VERSION_DOWNGRADE` | 설치된 앱보다 낮은 버전인지 확인. 테스트 버전 번호를 올려 빌드하는 방법부터 검토 |
| `INSTALL_FAILED_OLDER_SDK` | 헤드셋의 Android API와 앱 Minimum SDK 비교. 엔진·플러그인의 지원 하한 아래로 무작정 낮추지 않음 |

## 7. 기기별 완료 기록

| 기록 항목 | Quest 2 | PICO 4 |
| --- | --- | --- |
| 엔진 버전 | 5.8.1 | 5.8.1 |
| 헤드셋 OS 버전 | 기록 | 기록 |
| 외부 SDK 이름·버전 | 기본 구성은 없음 | 설치한 PICO For OpenXR 버전 기록 |
| SDK / NDK / JDK | 공통 문서 조합 확인 | 공통 문서 조합 확인 |
| 패키지명·빌드 시각·APK 경로 | 기록 | 기록 |
| USB VR Preview | 미검증 / 통과 / 실패 | 미검증 / 통과 / 실패 |
| 무선 VR Preview | 미검증 / 통과 / 실패 | 미검증 / 통과 / 실패 |
| APK 설치·PC 없이 실행 | 미검증 / 통과 / 실패 | 미검증 / 통과 / 실패 |
| 시점·양손 입력·잡기·텔레포트 | 미검증 / 통과 / 실패 | 미검증 / 통과 / 실패 |

**빌드 성공, 설치 성공, 실제 실행 성공은 각각 확인한다.** PC VR Preview 통과만으로 헤드셋 단독 실행의 성능·기능이 검증되지는 않는다.
