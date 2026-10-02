# SSAFY Wi-Fi에서 Air Link는 실패하고 ALVR은 연결된 이유 — 추가 분석

> 작성일: 2026-09-10  
> 대상: Meta Quest 2 · SSAFY Wi-Fi · SteamVR · ALVR  
> 선행 문서: [SSAFY Wi-Fi에서 Meta Quest 2 Air Link가 검색되지 않은 원인 분석](ssafy-wifi-airlink-분석.md)

<div style="color:#14804A">

### 🟢 최종 판단

SSAFY Wi-Fi는 모든 단말 간 통신을 차단한 것이 아니다. **일반 유니캐스트와 ALVR의 UDP broadcast는 통과시키지만, Air Link의 PC 검색에 사용된 mDNS multicast는 전달하지 않는 것으로 판단된다.** 그래서 같은 SSAFY Wi-Fi에서도 Air Link는 PC를 찾지 못하고 ALVR은 연결될 수 있다.

팀의 무선 PC VR 작업 경로는 **`Unreal → OpenXR → SteamVR → ALVR → SSAFY Wi-Fi → Quest 2`**다. SteamVR은 활성 OpenXR 런타임이고, ALVR은 SteamVR과 Quest 사이의 무선 전송 드라이버·스트리머다. Meta Horizon Link는 이 경로에서 사용하지 않는다.

</div>

## 1. 추가 확인된 사실

선행 문서에서는 SSAFY Wi-Fi에서 Air Link가 PC를 찾지 못한 반면, 모바일 핫스팟에서는 검색·연결에 성공했다. Wireshark에서는 Meta Horizon Link가 다음 mDNS 패킷을 송신하는 것도 확인됐다.

```text
224.0.0.251:5353
_oculusal_sp._tcp.local
_oculusal_sp_v2._tcp.local
```

이번 추가 사실은 **ALVR + SteamVR이 SSAFY Wi-Fi에서 실제로 무선 연결됐다는 것**이다. 따라서 SSAFY Wi-Fi에서 모든 로컬 통신이나 모든 discovery가 차단됐다고 볼 수는 없다.

## 2. Air Link와 ALVR의 discovery 차이

| 구분 | Meta Air Link | ALVR |
| --- | --- | --- |
| 자동 탐색 | mDNS multicast | UDP broadcast |
| 확인 주소·포트 | `224.0.0.251:5353` | UDP `9943` |
| 연결 후 통신 | Meta 전용 스트리밍 경로 | TCP 제어 + UDP/TCP 스트림 |
| PC 측 런타임 | Meta Horizon Link | SteamVR |

ALVR 공식 기술 문서에 따르면 Quest의 ALVR 클라이언트가 UDP `9943` discovery broadcast를 보내고, PC의 ALVR 드라이버가 응답한다. 사용자가 Dashboard에서 기기를 `Trust`하면 이후 스트리밍 연결이 형성된다.

따라서 ALVR은 Air Link에서 관찰된 mDNS multicast를 사용하지 않는다. 네트워크 장비는 multicast와 broadcast를 별도로 처리할 수 있으므로 **mDNS multicast만 제한되고 ALVR broadcast와 유니캐스트는 통과하는 상황**이 가능하다.

- [ALVR 공식 — How ALVR works](https://github.com/alvr-org/ALVR/wiki/How-ALVR-works)
- [ALVR 공식 저장소 — 요구사항과 네트워크 구성](https://github.com/alvr-org/ALVR)

## 3. 팀 작업 구성

```text
Unreal Engine VR Preview
        ↓ OpenXR
SteamVR
        ↓ ALVR 외부 드라이버
ALVR Streamer
        ↓ SSAFY Wi-Fi
Quest 2 ALVR 앱
```

PC에서 필요한 핵심 구성은 **SteamVR + ALVR**이다.

| 구성 요소 | 역할 |
| --- | --- |
| SteamVR | 활성 OpenXR 런타임. Unreal의 PC VR 프레임 처리 |
| ALVR | 프레임을 Quest로 전송하고 Quest의 추적·컨트롤러 입력을 SteamVR에 전달 |
| Meta Horizon Link | 이 경로에서는 사용하지 않음 |

ALVR 자체는 OpenXR 런타임이 아니다. Unreal을 ALVR로 테스트할 때는 **SteamVR을 활성 OpenXR 런타임으로 지정**한다.
