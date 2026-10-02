# 인왕제색도 VR — 음향 소스 기록 (저작권 확인용)

담당: 김채원 (AI 트랙) · 갱신: 2026-09-12

## 규칙 (팀 공통으로 제안)

1. **CC0 (퍼블릭 도메인 헌정) 또는 Pixabay Content License 만 쓴다.**
   - CC0: 출처 표기 의무 없음, 상업·비상업 무관. 가장 안전
   - Pixabay Content License: 상업 이용 가능, 출처 표기 불요. 단 **소리 파일 자체를 단독 재배포 금지** (앱 안에 넣어 쓰는 건 허용)
2. **CC-BY 는 쓰지 않는다.** 앱 안에 크레딧 화면을 넣어야 하는데 VR 에서 잊기 쉽다. 꼭 쓸 거면 이 파일 + 앱 내 크레딧 둘 다
3. **BBC Sound Effects (RemArc 라이선스) 는 쓰지 않는다.** 개인·교육·연구 비상업 한정이라 부스·시연 등 대외 노출에 애매함
4. **유튜브에서 추출 금지.** 라이선스 확인 불가
5. 파일 하나 받을 때마다 아래 표에 **URL·라이선스·저자·받은 날짜**를 적는다. 표에 없는 파일은 저장소에 넣지 않는다

## 소스 후보 (2026-09-12 확인)

| 사이트 | 라이선스 | 검색 방법 | 비고 |
|---|---|---|---|
| Freesound (freesound.org) | 파일마다 다름 → **License 필터를 "Creative Commons 0" 으로** | `wind mountain loop`, `forest birds korea`, `footsteps gravel` | 가입 필요. WAV 원본 제공 |
| Pixabay Sound Effects (pixabay.com/sound-effects) | Pixabay Content License (전부 동일) | `wind`, `forest birds`, `footsteps dirt` | 가입 없이 MP3. 약관: 상업 OK, 표기 불요, 단독 재배포 금지 |
| 공유마당 (gongu.copyright.or.kr) | 공공누리 1유형 등 자료마다 표시 | 소리 → `바람`, `새소리` | 한국 산새 소리가 있을 수 있음. 자료별 유형 확인 |

## 필요한 소리 (1차)

| 용도 | 파일명 (assets/sounds/) | 길이 | 비고 |
|---|---|---|---|
| 산바람 (전역, 잔잔) | `wind_mountain_loop.wav` | 30 s+ 루프 | 폭풍 X. 나뭇잎 스치는 정도 |
| 산새 (근경 나무 쪽) | `birds_forest_loop.wav` | 30 s+ 루프 | 한국 산 새(박새·직박구리)면 이상적, 아니면 일반 숲 새 |
| 발소리 (흙·자갈) | `footstep_dirt_01~04.wav` | 0.3 s ×4 | 폰(BP_XRPawn, 김신정 담당)에 붙여야 함 → 요청 사양은 노트 참조 |

## 받은 파일 기록

| 파일 | 출처 URL | 라이선스 | 저자 | 받은 날짜 | 가공 |
|---|---|---|---|---|---|
| (아직 없음) | | | | | |

## MP3 → WAV

언리얼 5.8 이 MP3 를 바로 임포트하는지 확인 안 됨. 안 되면 무료 변환:
- Audacity (오픈소스) 로 열어서 파일 → 내보내기 → WAV
- 또는 ffmpeg: `ffmpeg -i in.mp3 -ar 48000 out.wav`
