# SSAFY Wi-Fi에서 Meta Quest 2 Air Link가 검색되지 않은 원인 분석

## 요약

SSAFY Wi-Fi에서 Meta Quest 2와 노트북을 같은 네트워크에 연결했지만, Quest 2의 Air Link 화면에서 노트북이 검색되지 않았다.

반면 **같은 Quest 2와 같은 노트북을 사용한 채 네트워크만 노트북 모바일 핫스팟으로 변경하자 Air Link에서 노트북이 정상적으로 검색되고 연결까지 가능했다.**


> **결론: SSAFY Wi-Fi에서 무선 클라이언트 간 mDNS/multicast 또는 유사한 로컬 discovery 트래픽이 제한되어 Quest 2가 Meta Horizon Link PC를 찾지 못했을 가능성이 가장 높다.**

다만 AP 설정이나 네트워크 관리자 로그를 직접 확인한 것은 아니므로, 네트워크 정책을 100% 확정한 것은 아니다.

---

## 1. 문제 상황

목표는 Quest 2를 Air Link로 노트북에 연결한 뒤 Unreal Engine의 `VR Preview`를 사용하는 것이었다.

```text
Quest 2
  ↓ Air Link
Meta Horizon Link
  ↓ OpenXR
Unreal Engine
  ↓
VR Preview
```

하지만 SSAFY Wi-Fi에서는 Quest 2의 Air Link PC 목록에 노트북이 나타나지 않았다.

---

## 2. 같은 네트워크인지 확인

노트북:

```text
IPv4 주소       : 192.168.100.60
서브넷 마스크   : 255.255.255.0
기본 게이트웨이 : 192.168.100.1
```

Quest 2:

```text
192.168.100.249
```

두 기기 모두 `192.168.100.0/24` 대역에 있으므로 서로 다른 서브넷에 연결된 문제는 아니었다.

### 확인 화면

![노트북 ipconfig](./images/2026-09-02/2026-09-02-ipconfig.png)

---

## 3. 노트북 설정 확인

Air Link 검색을 막을 수 있는 기본 설정을 확인했다.

- Windows Defender 방화벽을 일시적으로 꺼도 증상은 동일했다.
- Wi-Fi 네트워크 프로필은 이미 `Private`이었다.
- Meta Horizon Link의 `OVRService`는 `RUNNING` 상태였고, 재시작 후에도 증상은 동일했다.
- Meta Horizon Link 클라이언트도 재시작했지만 변화가 없었다.

따라서 Windows 방화벽, 네트워크 프로필, Meta 런타임 서비스가 직접적인 원인일 가능성은 낮았다.

---

## 4. Quest 2와 일반 통신이 가능한지 확인

노트북에서 Quest 2로 `ping`을 실행했다.

```cmd
ping 192.168.100.249
```

결과:

```text
보냄 = 89
받음 = 88
손실 = 1%

최소 = 4ms
최대 = 190ms
평균 = 66ms
```

Quest 2가 정상적으로 응답했으므로 **두 기기 사이의 일반적인 IP unicast 통신은 가능했다.**

### 확인 화면

![Quest 2 ping 결과](./images/2026-09-02/2026-09-02-pingtest.png)

---

## 5. Wi-Fi 대역과 신호 확인

노트북의 SSAFY Wi-Fi 연결 상태는 다음과 같았다.

```text
Band          : 5GHz
Channel       : 36
Radio type    : 802.11ac
Receive rate  : 780 Mbps
Transmit rate : 866.7 Mbps
Signal        : 85%
RSSI          : -55 dBm
```

따라서 `2.4GHz 사용`이나 `약한 Wi-Fi 신호` 때문에 PC 검색이 실패했다고 보기는 어려웠다.

다만 ping 지연이 `4~190ms`로 크게 출렁였기 때문에, Air Link 검색 문제와 별개로 실시간 VR 스트리밍 품질은 안정적이지 않을 가능성이 있다.

---

## 6. 노트북 모바일 핫스팟과 비교

SSAFY Wi-Fi 자체의 영향을 확인하기 위해 Quest 2를 노트북 모바일 핫스팟에 연결했다.

```text
SSAFY Wi-Fi
→ Air Link PC 검색 실패

노트북 모바일 핫스팟
→ Air Link PC 검색 성공
→ Air Link 연결 성공
```

같은 Quest 2, 같은 노트북, 같은 Meta Horizon Link에서 **네트워크만 변경했는데 결과가 달라졌다.**

이 결과로 Quest 2 하드웨어, Meta Horizon Link 설치, `OVRService`, Windows 방화벽 등보다 **SSAFY Wi-Fi의 네트워크 정책 또는 discovery 처리 방식**이 더 유력한 원인이 됐다.

> 모바일 핫스팟에서는 Air Link 연결은 됐지만 스트리밍이 심하게 끊겼다. 이는 SSAFY Wi-Fi에서 PC가 검색되지 않는 문제와 별개의 문제이므로 여기서는 다루지 않는다.

---

## 7. Wireshark로 Meta mDNS 송신 확인

SSAFY Wi-Fi에서 Wireshark로 Wi-Fi 인터페이스를 캡처했다.

사용한 필터:

```text
ip.dst == 224.0.0.0/4
```

또는:

```text
udp.port == 5353
```

노트북 `192.168.100.60`에서 `224.0.0.251:5353`으로 mDNS 패킷이 반복적으로 송신되고 있었다.

특히 다음 서비스가 확인됐다.

```text
_oculusal_sp._tcp.local
_oculusal_sp_v2._tcp.local
```

즉 **Meta Horizon Link가 Air Link discovery와 관련된 mDNS 트래픽을 노트북에서 정상적으로 송신하고 있었다.**

### 확인 화면

![Wireshark mDNS multicast](./images/2026-09-02/2026-09-02-wireshark224.png)

![Wireshark UDP 5353](./images/2026-09-02/2026-09-02-wireshark5353.png)

---

## 8. Quest 2 → 노트북 통신 확인

Quest 2에서 오는 패킷 자체가 막힌 것인지 확인하기 위해 다음 필터를 적용했다.

```text
ip.src == 192.168.100.249
```

동시에 노트북에서 `ping -t 192.168.100.249`를 실행했다.

Wireshark에서 다음 ICMP 응답이 정상적으로 확인됐다.

```text
Source      : 192.168.100.249
Destination : 192.168.100.60
Protocol    : ICMP
Info        : Echo (ping) reply
```

따라서 Quest 2 → 노트북 방향의 **일반 unicast 패킷은 정상적으로 전달되고 있었다.**

### 확인 화면

![Quest 2 ICMP Echo Reply](./images/2026-09-02/2026-09-02-wireshark-echo.png)

---

## 9. 다른 무선 클라이언트의 mDNS 확인

같은 SSAFY Wi-Fi에 연결된 다른 노트북의 IP `192.168.100.44`를 기준으로 다음 필터를 적용했다.

```text
udp.port == 5353 && ip.src == 192.168.100.44
```

캡처 결과 해당 노트북에서 오는 UDP 5353 패킷은 확인되지 않았다.

다만 해당 시점에 다른 노트북이 실제로 mDNS를 송신했는지는 보장할 수 없으므로, 이 결과만으로 multicast 차단을 확정하지는 않았다.

### 확인 화면

![다른 클라이언트의 UDP 5353 미수신](./images/2026-09-02/2026-09-02-wireshark5353192.png)

---

## 10. 임의 multicast 송수신 테스트

다른 노트북에서 PowerShell로 UDP multicast 패킷을 직접 송신했다.

```powershell
$udp = New-Object System.Net.Sockets.UdpClient
$bytes = [Text.Encoding]::UTF8.GetBytes("multicast-test")
$udp.Send($bytes, $bytes.Length, "239.255.100.100", 50000)
$udp.Close()
```

송신 측에서는 `14`가 반환됐다. 이는 14바이트를 UDP 스택에 전달했다는 의미이며, 수신 성공을 의미하는 ACK는 아니다.

내 노트북에서는 `239.255.100.100:50000` multicast 그룹에 가입한 뒤 수신을 기다렸다.

```powershell
$result = $udp.Receive([ref]$remote)
```

다른 노트북에서 패킷을 전송한 뒤에도 `Receive()`가 계속 대기 상태였기 때문에 multicast 패킷이 수신 소켓까지 도착하지 않은 것으로 보였다.

다만 송신 측 Wi-Fi 인터페이스를 명시적으로 강제한 재시험까지 진행하지 않았으므로, 이 결과 역시 **정황 증거**로만 사용한다.

### 확인 화면

![multicast-test 송신](./images/2026-09-02/2026-09-02-50000.png)

![multicast 수신 대기](./images/2026-09-02/2026-09-02-wait.png)

---

## 11. 최종 판단

| 확인 항목 | 결과 |
|---|---|
| 노트북과 Quest 2가 같은 서브넷 | O |
| PC ↔ Quest 2 unicast 통신 | O |
| Windows 방화벽 영향 | 가능성 낮음 |
| Windows 네트워크 프로필 | Private |
| Meta `OVRService` | 정상 실행 |
| SSAFY Wi-Fi | 5GHz |
| Meta Horizon Link의 mDNS 송신 | O |
| SSAFY Wi-Fi에서 Air Link PC 검색 | X |
| 모바일 핫스팟에서 Air Link PC 검색/연결 | O |
| 다른 클라이언트의 multicast 수신 | 확인되지 않음 |

핵심 근거는 세 가지다.

1. **PC와 Quest 2 사이의 unicast 통신은 정상이다.**
2. **PC의 Meta Horizon Link는 Oculus 관련 mDNS 패킷을 정상적으로 송신한다.**
3. **같은 PC와 Quest 2에서 네트워크만 모바일 핫스팟으로 바꾸면 Air Link가 검색된다.**

따라서 Unreal Engine, OpenXR, Quest 2 자체의 문제보다는 **SSAFY Wi-Fi에서 무선 클라이언트 간 mDNS/multicast 또는 유사한 local discovery 트래픽이 제한되는 것이 가장 유력한 원인**이다.

### 네트워크 관리자 확인이 필요한 항목

SSAFY Wi-Fi에서 Air Link를 사용해야 한다면 네트워크 관리자에게 다음 정책 적용 여부를 확인해야 한다.

```text
mDNS / Multicast Filtering
Multicast Suppression
Client / AP Isolation
Intra-client Communication 제한
Peer-to-Peer Discovery 제한
```

기관 네트워크의 실제 AP 설정과 로그를 확인하지 않았으므로 최종 확정에는 관리자 확인이 필요하다.
