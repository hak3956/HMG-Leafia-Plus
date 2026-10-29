# 국내 EV6 무선 CarPlay: 이어서 하는 사람을 위한 인수인계 (2026-10-29)

> 포크 작업 문서입니다. 새 Claude 세션이나 다른 사람이 이 문서 하나로 이어 갈 수 있게 적었습니다.
> 같이 볼 문서: `CVEV-KOR-PORT-PLAN.md` (목표·안전 규칙), `CVEV-KOR-STOCK-HASHES.md` (순정 해시), `CVEV-KOR-PORT-SETUP.md` (도구 준비).
> 업스트림(VysseCodes)에는 PR·이슈를 만들지 않습니다. 순정 파일·전체 수정 앱·키 파일·로그는 저장소와 대화에 올리지 않습니다.

## 1. 목표와 차

- 국내 Kia EV6, 펌웨어 `CVEV.KOR.0000.V039.001.260902`, HUD 없음, NEMESIS 1.15 이상 설치됨.
- 목표: **무선 CarPlay** (+ 무선 Android Auto, 핫스팟). 클러스터 턴바이턴은 쓰지 않음.
- 업스트림 관리자에게 기준 자료를 받지 않고 자체적으로 해결하는 방향 (사용자 결정).

## 2. 지금까지 한 것 (브랜치 `claude/vibrant-keller-kkgsdp`)

1. **CarPlay 모드** (패키지): 패치 세트에 턴바이턴 빌드(2_tbt)가 없고 브릿지(3_bridge)만 있는 차는 1·3·4·5 부분만 설치. 브릿지는 순정 DiPO·Iap2Server 위에 얹힘. 모의 헤드유닛에서 국내 EV6 실제 순정 트리로 설치·제거 통과 (NEMESIS 1.15, Android 꺼짐 조건 포함).
2. **국내 EV6 패치 세트 `cvev_kr`** (사용자 PC 의 WSL 클론에서 만듦, **아직 커밋 안 함**: 아래 4절):
   - Iap2ServerApp 브릿지: 국내 아이오닉 5(`neev_kr`) 델타가 국내 EV6 파일에서 바이트 단위로 같은 결과를 냄 (APK md5 `75d7fea4d2009be6aa5c840118f58c94`, v1.0.2 때 국내 아이오닉 5 실차에서 무선 CarPlay 가 됐던 빌드).
   - HKMC_DiPO 브릿지: 국내 EV6 순정 DiPO 에 브릿지 변경만 옮김 (`tools/bridgeport.py --only-ours`): 훅 5개 클래스(e/g, e/h, i/e, service/aa, telechips/CarPlayService) + 새 클래스 `com/ev6/cpwl/*`. 나머지는 순정 그대로. DiPO APK md5 `a0b4f267a48730a923cc49967aa88a77`.
   - `com/ev6/cpwl/TxListener` 는 다시 만든 빌드에서 깨져 있어 **손으로 다시 씀** (`tools/cvev_kr/com/ev6/cpwl/TxListener.smali`). `disconnected`·`notify` 는 추론이라 실차 확인 필요.
3. 도구 (모두 `tools/`): `trydelta.py`, `cmpsmali.py`, `bridgeport.py`, `mkcarplay.py`, `mkpatches.py --carplay-only`. 사용법은 각 파일 첫 주석.

## 3. 실차 결과 (2026-10-29 저녁) — 여기서 멈춤

- CarPlay 모드로 설치됨 (`all parts installed (carplay mode: 1_projection 3_bridge 4_audio 5_menu)`), DiPO·Iap2 dexopt 성공.
- DiPO·iAP2 프로세스는 죽지 않음 (PID 그대로). 브릿지 코드도 돎: 케이블을 뺄 때 `EV6CPWL: iAP2 disconnected comp=1`, 꽂을 때 `iAP2 connected comp=1`.
- **그러나 유선 CarPlay 도, 무선 CarPlay 도 안 됨.** iAP2 연결(DipoService `onIap2Connected ... result = 1`)까지만 되고, CarPlay 화면 세션이 시작되지 않음 (브릿지 훅 `CarPlay session created` 가 찍히지 않음).
- 이것은 기본 모드에서 `carplay_wireless` 기능을 켰을 때 본 증상과 같음: 국내 V039 DiPO 는 무선 CarPlay 기능이 켜져 있으면 유선 연결에서도 iAP2 다음 단계(아이폰의 무선 전환 / Wi-Fi 정보)에서 멈춤. 브릿지가 이것을 풀지 못함.
- **일상용으로 되돌리기**: NEMESIS 에서 이 패키지를 제거 → 재부팅 (순정으로 돌아감, 유선 CarPlay 복원) → 평소 쓰던 버전(사용자가 고친, 기본 모드에서 `carplay_wireless` 를 켜지 않는 버전) 다시 설치.

## 4. 바로 다음 할 일

1. **로그 보기** (진행 중이던 일). 노트북(Windows, WSL 없음)의 PowerShell 에서, 아이폰을 케이블로 꽂은 직후:
   ```powershell
   cd C:\platform-tools; .\adb connect <헤드유닛 IP>; .\adb logcat -d -v time | Out-File -Encoding utf8 C:\hmg-private\cvev-kor\carplay-test1.txt
   ```
   그다음 꽂은 시각(`$t0`)부터 40초 동안 DiPO·iAP2 서버(ps 의 PID) 줄과 CarPlay·Wi-Fi 관련 줄만 잘라서 봅니다:
   ```powershell
   $t0=[datetime]'22:07:49'; Select-String -Path C:\hmg-private\cvev-kor\carplay-test1.txt -Pattern '\( 1010\)|\( 1037\)|CarPlay|AirPlay|iAP2|Iap2|iap2|WiFi|Wifi|wifi|hostapd|mDNS|Bonjour' | % Line | ? { $_ -match '^\d\d-\d\d (\d\d:\d\d:\d\d)' -and ([datetime]$matches[1] -ge $t0) -and ([datetime]$matches[1] -le $t0.AddSeconds(40)) } | % { $_ -replace '([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}','XX:XX:XX:XX:XX:XX' } | Out-File -Encoding utf8 C:\hmg-private\cvev-kor\carplay-test1-cut.txt
   ```
   (PID 1010/1037 과 시각은 그때의 `adb shell ps` 와 로그에 맞게 바꿈.) 아이폰 이름·일련번호·전화번호가 보이면 가린 뒤에만 공유.
2. 로그에서 볼 것: iAP2 identification 이 끝났는지, 아이폰이 WiFiInformation 을 요청했는지 (`persist.sys.iap2.wifi=t` 로 iAP2 서버가 Wi-Fi 정보를 알림), DiPO 가 유선 세션을 시작하지 않는 까닭 (DipoService 의 연결 방식/무선 판단 로그), `EV6CPWL` 의 `Iap2SvcInit(EV6_CPWL_BT, 0xc00) = true`.
3. 아이폰에 "무선 CarPlay 사용" 안내가 떴는지, 수락/거절 각각에서 무엇이 달라지는지 기록.
4. 가설: 무선 CarPlay 가 켜진 국내 DiPO 의 유선 경로가 멈추는 것은 미국 EV6 에는 없는 순정 동작일 수 있음. 그 경우 DiPO 의 해당 분기(유선일 때 무선 대기를 건너뛰기)를 찾아 훅을 하나 더 넣는 것이 다음 수정 후보.

## 5. 사용자 PC 의 상태

- `C:\hmg-private\cvev-kor\` (비공개, 저장소 아님): `new-stock` (앱·라이브러리), `new-fw\framework`, `kit\LEAFIA\private\stock` (port 키트로 받은 순정 /system: 모의 시험 입력), `trydelta`, `cmp` (deodex 결과), `port\dipo-bridge` (브릿지를 옮긴 DiPO smali), `builds` (전체 수정 APK), `install-log.txt`, `carplay-test1.txt`.
- WSL(Ubuntu 26.04) `~/HMG-Leafia-Plus` 클론: `patches/cvev_kr/` 와 `patches/cars` 줄이 **커밋되지 않은 채** 있음 (델타·해시만이라 커밋해도 되지만, WSL 에 GitHub 인증이 없음). 같은 결과는 아래 명령으로 언제든 다시 만들 수 있음.
- 다시 만들기 (WSL):
  ```bash
  cd ~/HMG-Leafia-Plus && git pull && K=/mnt/c/hmg-private/cvev-kor
  ~/leafia-venv/bin/python tools/bridgeport.py --work $K/cmp --app HKMC_DiPO --set neev_kr --base tbt --part bridge --out $K/port/dipo-bridge --fw $K/new-fw/framework --baksmali ~/.local/share/smali/baksmali-2.5.2.jar --only-ours --replace tools/cvev_kr
  ~/leafia-venv/bin/python tools/mkcarplay.py --variant cvev_kr --prefix CVEV.KOR. --name "Kia EV6 (Korea)" --stock $K/new-stock --dipo-smali $K/port/dipo-bridge --iap2-dex $K/trydelta/neev_kr/Iap2ServerApp.bridge.out --builds $K/builds
  sh tools/build-package.sh
  MOCK_SH=/usr/bin/mksh sh tools/mock/install-test.sh dist/HMG_Leafia_Plus_Wireless_CarPlay_AA.zip CVEV.KOR.0000.V039.001.260902 cvev_kr $K/kit/LEAFIA/private/stock
  ```
- WSL 준비물: `qemu-arm-static` 은 `/usr/local/bin` 에 `/usr/bin/qemu-arm` 연결, smali/baksmali 2.5.2 는 `~/.local/share/smali/`, Python 패키지는 `~/leafia-venv`. Ubuntu 26.04 의 clang 은 헤드유닛 lpatch 를 다른 바이트로 빌드하므로 `tools/lpatch/build.sh` 뒤 `git checkout tools/lpatch/lpatch` 로 되돌릴 것.

## 6. 지킬 것

- 실차 시험은 주차 상태에서만. 운전 중 실험 금지.
- 순정 파일·전체 수정 APK·키·로그 원본은 저장소·대화·공개 이슈에 올리지 않음. 로그는 블루투스 주소·기기 정보를 가린 일부만.
- 모의 시험(제거 후 순정과 바이트 단위로 같음)을 통과한 패키지만 차에 설치.
- 업스트림 PR·이슈는 만들지 않음 (사용자가 완벽하다고 판단할 때까지).
