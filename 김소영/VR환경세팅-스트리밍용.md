# 공통

1. Epic Games Launcher에서 Unreal Engine 설치
    - 버전 UE 5.8.2. (5.8.0 설치하면 자동으로 업데이트 됨)
    - 옵션 → 타겟 플랫폼 → 안드로이드 추가 설치
    - Launcher에서 5.8.2 실행함.
2. Unreal Engine에서 새 VR 프로젝트 생성
    - 게임(Games) → Virtual Reality 템플릿 선택. (게임>VR이나 시뮬>VR이나 동일한 템플릿임. Game에서 할 것을 권장.)
    - 프로젝트 생성 후 에디터 진입.
3. UE 5.8.2 기본 XR 맵 확인
    - 프로젝트를 열었을 때 기본으로 L_XRTemplate 맵이 열려 있음.

------

## Oculus Quest2 세팅 (무선 스트리밍 방식)

> USB Quest Link를 사용하려면 Meta Horizon Link가 정상 동작해야 한다. 현재 개발 PC에서는 Horizon Link 호환성 오류가 발생하므로 일단 Steam Link를 이용해 우회한다.

1. Steam 및 SteamVR 설치 
    - [스팀 다운로드](https://store.steampowered.com/about/)

2. SteamVR 실행
    - ≡ → Settings → OpenXR → Set SteamVR as OpenXR Runtime
    - Current OpenXR Runtime: SteamVR로 나오면 성공

3. Quest2 기기에서 Steam Link 앱 설치
    - PC와 Quest 2 같은 네트워크에 연결 (5GHz Wi-Fi 권장)
    - Steam Link 실행 → 검색된 본인 PC 선택 → 화면 안내에 따라 페어링

4. 연결이 성공하면 Quest 내에서 SteamVR 공간이 보여야 함
    - 이 상태에서 양손 컨트롤러가 SteamVR에 잡히는지 확인

5. Unreal 실행 → 사용하는 L_XRTemplate 맵 열기

6. Edit → Plugins에서 OpenXR가 ON인지 확인

7. 상단 ▶ 재생 옆 화살표 → VR Preview를 실행


-----

## PICO4 세팅 
1. PC에 다음 설치
    - PICO Connect [다운로드 링크](https://www.picoxr.com/kr/software/pico-link?utm_source=chatgpt.com) 
        - PICO 4는 PICO OS 5.11.2 이상 권장 (아닐 시 소프트웨어 업데이트 필요)
        - Windows용 PICO Connect 다운로드
        - 스트리밍 어시스턴트는 예전 소프트웨어이므로 설치 X 
    - Steam 
    - SteamVR

2. PICO4에 PICO Connect 확인
    - 없으면 PICO Store에서 설치

3. SteamVR를 OpenXR Runtime으로 설정
    - PC에서 SteamVR 실행 SteamVR ≡ → Settings → OpenXR → Set SteamVR as OpenXR Runtime
    - 현재 OpenXR Runtime이: SteamVR면 됨

4. PICO 4 PC에 연결
    - 무선 스트리밍
        >  PC에서 PICO Connect 실행 → PICO 4에서 PICO Connect 실행 → 같은 네트워크 연결 → PICO에서 PC 검색 → 내 PC 선택 → 연결
    - 유선 스트리밍
        > PC PICO Connect 실행 → PICO 4와 PC를 USB 3 데이터 케이블로 연결 → PICO 4 PICO Connect 실행 → USB/유선 연결 선택

5. PICO Connect 연결 후 SteamVR 실행
    - 연결된 상태에서 PC의 SteamVR 켜야 함
    - SteamVR 상태창에서 다음이 정상 인식되는지 확인
        - 헤드셋
        - 왼손/오른손 컨트롤러
    
6. Unreal 실행
    - 현재 프로젝트 열고 L_XRTemplate맵 열기
    - Edit → Plugins → OpenXR가 ON인지 확인
    - 그리고 상단: ▶ 옆 ▼ → VR Preview 실행

---

## ** 참고 — Meta Horizon Link 호환성 문제 ** 

현재 발생한 문제는 Quest 2 자체나 Unreal 프로젝트의 오류가 아니라 Meta Horizon Link PC 앱의 하드웨어 호환성 판정 단계에서 발생한 문제다.

현재 PC는 Core Ultra 9 185H + RTX 4070 Laptop GPU + 64GB RAM 구성으로 기본 성능 요구사항을 충분히 만족한다. Meta 공식 호환성 표에서도 RTX 40 시리즈는 Link 지원 대상이다. 다만 해당 노트북은 Intel Arc Graphics + RTX 4070 Laptop GPU의 하이브리드 그래픽 구성이며, Meta는 현재 Intel Arc GPU를 Horizon Link에서 지원하지 않는다고 명시하고 있다. 따라서 하이브리드 GPU 구성이 현재 호환성 오류에 영향을 주는 것이 유력하지만, Horizon Link가 Intel Arc를 직접 원인으로 판정했다는 것까지 확인된 것은 아니다.

Windows 그래픽 설정과 NVIDIA 제어판에서 OculusClient.exe, OVRServer_x64.exe 등을 RTX 4070 고성능 GPU로 지정한 후 재부팅했지만 동일한 호환성 오류가 유지됐다. Meta에서도 자동 감지 또는 호환성 문제가 있을 경우 드라이버 확인, 백그라운드 프로그램 종료, 재부팅 등을 권장하고 있다.

이 문제는 Meta Quest Link를 이용하는 PC VR Preview 경로의 문제이며 Quest 2용 APK 포팅과는 별개다. 추후 포팅은:
>  Unreal → Android APK 패키징 → USB/ADB 또는 MQDH로 Quest 2 설치 → Quest 2 단독 실행

으로 진행할 수 있으므로 Meta Horizon Link가 필수는 아니다. 현재는 Link 문제를 보류하고,

> Quest 2 Steam Link → SteamVR → OpenXR → Unreal VR Preview

경로로 PC VR 개발과 기능 테스트를 진행한다.