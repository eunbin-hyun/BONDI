# Quest 2 무선 PC VR — ALVR + SteamVR 연결

> Windows 노트북(Intel Arc + RTX 4070 Laptop 하이브리드) · Meta Quest 2 · UE 5.8 기준
> 확인일: 2026-09-02 · **ALVR 연결과 SteamVR 홈 표시까지 실제 확인.** 언리얼 VR Preview는 미검증
> 갱신: 2026-09-09 — 기기 3·기기 4 기준 Streamer 버전, SSAFY Wi-Fi 동작, 09-09 연결 재확인 반영

[Quest 2 실행 경로 비교](2026-09-02.md) · [김소영 — Quest 2 연결·포팅](../김소영/unreal-포팅/unreal-quest2-porting.md) · [김소영 — 스트리밍용 VR 환경세팅](../김소영/VR환경세팅-스트리밍용.md) · [김소영 — SSAFY Wi-Fi Air Link 분석](../김소영/ssafy-wifi-airlink-분석.md)

## 0. 왜 이 경로인가

PC VR 프리뷰의 표준 경로가 팀 개발 PC에서 순서대로 막혔다.

| 경로 | 결과 | 원인 |
| --- | --- | --- |
| Meta Horizon Link (USB / Air Link) | ✗ 이 PC에서 사용 불가 | 호환성 오류 — Intel Arc 하이브리드 GPU 구성으로 추정 ([김소영 문서](../김소영/VR환경세팅-스트리밍용.md)). **PC마다 다르다.** 김소영 님은 09-02에 핫스팟으로 Air Link 연결에 성공했다 ([분석](../김소영/ssafy-wifi-airlink-분석.md)) |
| Steam Link | ✗ **Quest 스토어에서 검색되지 않음** | 계정 지역 또는 카탈로그 문제로 추정. 미확인 |
| **ALVR** | ✓ 스토어에 있음 → **연결 성공** | — |

ALVR은 Steam Link와 같은 방식이다. PC의 SteamVR이 렌더링하고 Wi-Fi로 헤드셋에 스트리밍한다.
오픈소스 무료이고 설정 항목이 더 많다.

**OpenXR 런타임은 SteamVR이다.** 언리얼은 SteamVR을 통해 헤드셋을 본다. ALVR은 SteamVR의 드라이버로 붙는다.

```text
언리얼 VR Preview
   ↓ OpenXR
SteamVR (활성 런타임)
   ↓ ALVR 드라이버
ALVR Streamer (PC)  ──Wi-Fi──▶  ALVR 앱 (Quest 2)
```

## 1. 준비물

| 구분 | 항목 |
| --- | --- |
| PC | Steam + SteamVR 설치, Steam 로그인 |
| PC | ALVR Streamer — https://github.com/alvr-org/ALVR/releases 의 **v20.14.0** `alvr_streamer_windows.zip` (기기 4 기준, 다른 기기 사용 시 4절 「Quest 2 — ALVR 앱」에서 버전 확인 후 다운받을 것) |
| Quest 2 | ALVR 앱 — **기기 3·기기 4는 설치 완료.** 그 외 기기만 Meta 스토어에서 설치 |
| 네트워크 | PC와 Quest 2가 같은 망. **PC는 랜선, Quest는 5GHz** 권장 |

ALVR Streamer는 설치 프로그램이 아니다. zip을 풀어서 `ALVR Dashboard.exe`를 실행한다.

## 2. PC — SteamVR 런타임 설정

1. SteamVR 실행 → ≡ → **Settings → OpenXR**
2. **Set SteamVR as OpenXR Runtime**
3. `Current OpenXR Runtime: SteamVR` 확인

이 시점에 상단에 **"Additional settings available upon headset detection."** 이 뜨고 메뉴가
Startup/Shutdown·OpenXR 두 개만 보인다. **오류가 아니다.** 헤드셋이 아직 연결되지 않아서 그렇고,
ALVR로 연결되면 나머지 메뉴가 나타난다.

## 3. PC — ALVR Streamer

1. `ALVR Dashboard.exe` 실행
2. 처음 뜨는 **Setup Wizard** 진행
   - **Add firewall rules** — 반드시 누른다. 안 하면 헤드셋이 PC를 찾지 못한다
   - SteamVR 드라이버 등록이 자동으로 된다
3. Dashboard가 열린 채로 둔다

## 4. Quest 2 — ALVR 앱

> **기기 3·기기 4는 설치가 끝나 있다.** 설치 단계를 건너뛰고 앱만 실행한 뒤 5절로 간다.

1. (미설치 기기만) 스토어에서 ALVR 설치
2. ALVR 실행 → 화면에 대기 중 표시가 뜬다. **보이는 버전을 확인한다** — PC Streamer와 같은 버전이어야 한다 (6-1)
3. 이 상태로 두고 PC로 돌아간다

## 5. 연결

1. PC ALVR Dashboard → **Devices** 탭 → 헤드셋이 "New devices"에 나타남 → **Trust**
2. SteamVR이 자동으로 켜진다. 안 켜지면 Dashboard 상단 **Launch SteamVR**
3. Quest 안에 SteamVR 홈(회색 격자 공간)이 보이면 연결 성공
4. 양손 컨트롤러가 SteamVR에 잡히는지 확인
5. SteamVR Settings를 다시 열면 헤드셋·비디오 등 메뉴가 늘어나 있다

**여기까지 2026-09-02에 확인했고, 2026-09-09에 같은 절차로 다시 연결되는 것을 확인했다.**

## 6. 문제 해결

실제로 겪은 것과 미리 알아둘 것을 함께 적었다.

### 6-1. 버전 불일치

ALVR은 **헤드셋 앱과 PC Streamer의 버전이 맞아야** 한다. **기기 4 기준으로는 v20.14.0
`alvr_streamer_windows.zip`을 받는다.** 다른 기기는 4절에서 확인한 앱 버전에 맞춘다.
**최신 릴리스가 항상 맞는 것이 아니다.** 스토어 앱은 안정 버전이라 GitHub 최신보다 뒤에 있을 수 있다.

### 6-2. GPU 지정 — 이 노트북에서는 핵심

Horizon Link를 막은 Intel Arc + RTX 하이브리드 구성이 ALVR에서도 문제가 될 수 있다.
ALVR은 NVENC 인코딩을 쓰므로 **반드시 RTX에서 돌아야** 한다.

Windows 설정 → 시스템 → 디스플레이 → 그래픽 → 아래 항목 추가 후 **고성능** 지정:

| 실행 파일 | 위치 |
| --- | --- |
| `ALVR Dashboard.exe` | Streamer를 푼 폴더 |
| `vrserver.exe` | `Steam\steamapps\common\SteamVR\bin\win64\` |
| `vrcompositor.exe` | 같은 폴더 |

### 6-3. Devices에 헤드셋이 안 뜸

| 확인 | 조치 |
| --- | --- |
| 같은 네트워크인가 | **Quest 2와 PC가 둘 다 SSAFY Wi-Fi에 연결돼 있는지 확인한다.** 같은 네트워크여야 헤드셋이 잡힌다. SSAFY Wi-Fi에서 ALVR은 그대로 연결된다 |
| 방화벽 | Setup Wizard의 Add firewall rules를 눌렀는지. 안 눌렀으면 Dashboard → Installation에서 다시 |

### 6-4. 연결됐는데 SteamVR이 "headset not detected"

드라이버 등록 실패다. Dashboard → **Installation** 탭 → **Register ALVR driver** → SteamVR 재시작.

### 6-5. 화면이 끊기거나 흐림

처음에는 Dashboard → Settings → Video → **Bitrate**를 30~40 Mbps로 낮춰 안정화하고, 그 뒤에 올린다.
코덱은 H264 기본값으로 시작한다.

## 7. 다음 — 언리얼 VR Preview (미검증)

1. 5절 상태(SteamVR 홈이 헤드셋에 보임)를 유지
2. 언리얼 프로젝트 열기 → **Edit → Plugins → OpenXR** ON 확인
3. 맵 열기 → ▶ 옆 ▼ → **VR Preview**
4. 시점·양손 컨트롤러·잡기·텔레포트 확인

| 증상 | 확인 |
| --- | --- |
| VR Preview가 회색 | 활성 OpenXR 런타임이 SteamVR인지 (2절). Meta로 잡혀 있으면 안 된다 |
| VR Preview 항목이 없음 | OpenXR 플러그인 비활성. 켜고 에디터 재시작 |

**주의.** 이 프리뷰는 PC GPU가 렌더링한다. Quest 2 단독 성능이 아니다. 성능 판정은 APK로 한다.
([09-02 노트 1절](2026-09-02.md) 참조)

## 8. 체크리스트

- [x] SteamVR이 활성 OpenXR 런타임
- [x] ALVR Streamer 설치, 방화벽 규칙 추가
- [x] Quest 2에 ALVR 앱 설치
- [x] Dashboard Devices에서 Trust → SteamVR 자동 실행
- [x] Quest에 SteamVR 홈 표시
- [ ] 양손 컨트롤러 인식 확인
- [ ] 언리얼 VR Preview에서 시점·입력 확인
- [ ] 6-2 GPU 고성능 지정이 실제로 필요했는지 기록

## 9. 팀에 공유할 것

- **Steam Link가 스토어에 안 보이는 기기가 있다.** 원인(계정 지역 / 카탈로그) 미확인.
  다른 팀원 기기에서도 같은지 확인 필요
- ALVR이 되면 Steam Link를 굳이 뚫을 이유가 없다. **팀 PC VR 경로를 ALVR + SteamVR로 통일할지** 회의 안건
- 김소영 님 [스트리밍용 세팅 문서](../김소영/VR환경세팅-스트리밍용.md)의 Steam Link 절차 옆에 ALVR 대안을 붙이면 좋겠다
- OpenXR 런타임은 한 번에 하나다. PICO 4도 SteamVR 런타임을 쓰므로 **Quest 2·PICO 4 모두 SteamVR로 통일되면 런타임 전환이 없어진다**
