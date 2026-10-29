# 국내 EV6 포팅 도구 준비 (작업용 문서)

> `CVEV-KOR-PORT-PLAN.md` 의 진행 순서 2번(`tools/port.py` 실행) 앞 단계입니다.
> 포크의 작업 브랜치에서만 관리하고, upstream 에 공유하기 전에는 삭제하거나 upstream 규칙에 맞게 다듬습니다.
> 순정 파일·수정 빌드·프레임워크는 이 문서에도, 저장소에도 넣지 않습니다. 해시와 명령만 적습니다.

## 1. 확인한 것 (2026-10-29, 기준 커밋 08f4436)

| 항목 | 결과 |
|---|---|
| 헤드유닛용 lpatch | `tools/lpatch/build.sh` 로 새로 빌드한 `lpatch` md5 `be4a186a1c92d0d82e50040a496b753f`, 저장소에 커밋된 바이너리와 같음 |
| 호스트 lpatch | `lpatch-host` 빌드되고 `delta`·`zipadd` 동작 |
| Python 패키지 | `pip install --require-hashes -r tools/requirements.txt` 통과 (bsdiff4 1.3.1) |
| `diff`, `patch` | port.py 의 3-way 병합에 필요. Linux 에는 기본으로 있음 |
| port.py 흐름 | 가짜 자료로 시험 (아래). 정상 경우 `patches/cvev_kr/` 7개 델타·`stock`·`manifest` 를 쓰고 `patches/cars` 에 `CVEV.KOR. cvev_kr Kia EV6 (Korea)` 추가 |
| baksmali / smali | **확인 못 함.** 클라우드 작업 환경에서는 내려받은 jar 를 실행할 수 없었음. 사용자 PC 에서 4절로 확인 |

가짜 자료 시험 (실제 앱이 아닌 몇 줄짜리 smali 와 가짜 파일, deodex·smali 조립 단계는 건너뜀):

| 경우 | port.py 결과 |
|---|---|
| 새 차 클래스가 기준과 같음 | `OK: patches/cvev_kr written ...` |
| 새 차 libautoreceiver 가 기준과 다름 | `STOP: libautoreceiver_infobank.so differs from the reference car; it needs its own patch (--lib-build)` |
| 우리가 바꾼 클래스를 새 차도 다르게 바꿈 | `STOP: these classes differ on this car AND carry our changes; merge them by hand:` + 목록 |

국내 EV6 는 libautoreceiver 가 기준과 달라서(`c4fb…` ≠ `48ee…`) 기준 자료만 받으면 두 번째 경우로 바로 멈춥니다. `--lib-build` 가 꼭 필요합니다.

## 2. port.py 를 돌리기 전에 알아 둘 것

- **`--new-fw` 는 `framework` 폴더 자체**를 가리킵니다: `.../new-fw/framework` (`new-fw` 가 아님).
- **`--work`, `--out-builds` 는 저장소 밖의 비공개 폴더**로 줍니다. work 에는 두 차의 순정 앱을 deodex 한 smali 가 그대로 남고, out-builds 에는 전체 수정 APK 가 생깁니다. `--work` 를 빼면 임시 폴더(`/tmp/port-…`)에 남으니 꼭 지정합니다.
- **`--patches` 는 빼서 저장소 `patches/` 에 쓰게 합니다.** 여기에는 델타·해시만 생깁니다. 커밋 전에 `git status` 로 `patches/cvev_kr/`·`patches/cars` 말고는 바뀐 것이 없는지 봅니다.
- **work 폴더는 다시 쓰입니다.** port.py 는 work 안에 이미 있는 deodex 결과를 다시 만들지 않습니다. 입력을 바꿨으면(기준 자료를 다시 받음 등) 새 work 폴더로 돌립니다.
- **libautoreceiver (`--lib-build`)**: port.py 는 받은 파일을 그대로 복사만 합니다. 만드는 방법은 CLAUDE.md 의 AA 라이브러리 항목입니다: 0x1c4160 의 5칸 상대 주소표와 훅 3곳을 새 라이브러리에 맞게 다시 가리키고, 인라인된 도우미가 있으면 새 세그먼트에 복사본을 둡니다. 먼저 미국 순정에서 미국 수정본을 바이트 단위로 똑같이 만들어 방법을 확인합니다. 캐나다 아이오닉 5(`neev_ca/libautoreceiver_infobank.tbt.lpd`)가 같은 경우를 손으로 포팅한 선례입니다. mkpatches 는 공통 델타가 맞지 않으면 `patches/cvev_kr/libautoreceiver_infobank.tbt.lpd` 를 따로 만듭니다.
- **smali 조립 옵션이 문서와 다릅니다.** port.py 는 `smali a -a 19` (스레드 기본값)로 조립하고, CLAUDE.md 와 `tools/mkmenu.py` 는 `--api 18 -j 1` 을 씁니다. 스레드가 여럿이면 smali 가 돌릴 때마다 다른(동작은 같은) dex 를 쓸 수 있어서, port.py 를 다시 돌리면 `.lpd`·`manifest` 가 바뀔 수 있습니다. 한 번 돌린 결과는 그 안에서 맞으니 설치에는 문제없습니다. 바꿀지는 실제 자료로 두 번 돌려 비교해 본 뒤 정합니다.
- **port.py 가 하지 않는 것**: `docs/data/compat.json` 등록(`tools/compat-built.py`), 패키지 빌드(`tools/build-package.sh`), 모의 시험. 계획 문서 5~7번에서 따로 합니다.

## 3. 모의 시험에 필요한 자료가 더 있음

계획 문서 6번의 모의 헤드유닛 시험(`tools/mock/install-test.sh`)은 앱 9개 + 프레임워크만으로는 돌릴 수 없습니다. 순정 `/system` 트리(`app/`, `lib/`, `framework/`, `etc/permissions/`, `build.prop`)가 있어야 하고, 지역 폴더 이름(`ro.mobis.targetdir`)도 필요합니다.

- 가장 쉬운 방법은 **`leafia-kit-port.zip`** (읽기만 하는 USB 키트)을 한 번 돌리는 것입니다. `LEAFIA/private/stock/` 이 그대로 모의 시험 입력이 됩니다: 프레임워크, CarPlay·iAP2·AA 라이브러리와 코덱, 투영 앱, `etc/permissions`, `etc/wifi`, `featurexml.cfg`, `build.prop`.
- 받은 폴더는 `C:\hmg-private\cvev-kor\kit-stock\` 처럼 비공개 폴더에만 둡니다. 키트의 `private/` 는 공개 이슈에 올리지 않습니다.
- 지금 받아 둔 9개 파일과 키트의 같은 파일의 md5 가 같은지 함께 확인합니다 (`CVEV-KOR-STOCK-HASHES.md`).

## 4. 사용자 PC 준비 (Windows → WSL)

port.py 는 `diff`·`patch`·`cc`·POSIX 셸을 쓰므로 Windows 에서는 WSL(Ubuntu) 안에서 돌립니다. `C:\hmg-private` 는 WSL 에서 `/mnt/c/hmg-private` 입니다.

PowerShell(관리자)에서 한 번:

```bash
wsl --install -d Ubuntu
```

Ubuntu 안에서:

```bash
sudo apt update && sudo apt install -y git python3 python3-venv clang lld diffutils patch unzip openjdk-17-jre-headless qemu-user-static mksh
```

```bash
git clone -b claude/vibrant-keller-kkgsdp https://github.com/hak3956/HMG-Leafia-Plus.git ~/HMG-Leafia-Plus
```

```bash
cd ~/HMG-Leafia-Plus && sh tools/lpatch/build.sh && git status --short
```

마지막 줄의 md5 가 `be4a186a1c92d0d82e50040a496b753f` 이고 `git status` 에 아무것도 나오지 않으면 됩니다.

```bash
python3 -m venv ~/leafia-venv && ~/leafia-venv/bin/pip install --require-hashes -r ~/HMG-Leafia-Plus/tools/requirements.txt
```

baksmali·smali 2.5.2 (`tools/mkmenu.py` 와 같은 버전과 위치):

```bash
mkdir -p ~/.local/share/smali ~/.local/bin && cd ~/.local/share/smali && for j in baksmali smali; do curl -fLO https://bitbucket.org/JesusFreke/smali/downloads/$j-2.5.2.jar; done && sha256sum *.jar
```

클라우드 작업 환경에서 같은 주소로 받은 파일의 sha256 입니다. 다르면 쓰지 말고 알려 주세요.

| 파일 | sha256 |
|---|---|
| baksmali-2.5.2.jar | `d3116248cce4f82ec5a31eb7f95ee75daff42ddf6eed0ab573973dc53fbad2e5` |
| smali-2.5.2.jar | `9544299578b16f771d8aa8eaefe0d3718ca03478c16f3c356f2fcf1366bfb116` |

port.py 는 `baksmali`, `smali` 를 명령으로 부르므로 감싸는 스크립트를 PATH 에 둡니다:

```bash
for j in baksmali smali; do printf '#!/bin/sh\nexec java -jar "$HOME/.local/share/smali/%s-2.5.2.jar" "$@"\n' $j > ~/.local/bin/$j; chmod +x ~/.local/bin/$j; done
```

```bash
export PATH=$HOME/.local/bin:$PATH && baksmali --version && smali --version
```

## 5. 기준 자료 없이 지금 해 둘 수 있는 새 차 쪽 점검

모두 PC 의 복사본만 읽습니다. 차에는 아무것도 하지 않습니다.

```bash
K=/mnt/c/hmg-private/cvev-kor && export PATH=$HOME/.local/bin:$PATH
```

**(1) 해시**: 9개가 `CVEV-KOR-STOCK-HASHES.md` 와 같은지

```bash
md5sum $K/new-stock/app/* $K/new-stock/lib/*
```

**(2) 프레임워크 개수**: 142개인지 (차에 다시 연결하면 `adb shell ls /system/framework` 와 대조)

```bash
ls $K/new-fw/framework | wc -l
```

**(3) 클러스터 API** (2026-10-29 확인: 11개 모두 있음, PowerShell 로 `automotive.odex` 에서 문자열 확인 = 설치 프로그램의 `check_cluster_api` 와 같은 방식): 턴바이턴 파트가 설치 때 확인하는 11개 호출이 다 있는지. 하나라도 `없음` 이면 전체 모드가 되지 않으므로 포팅 전에 알아야 합니다.

```bash
for m in updateTBTInfo updateTBTSubInfo updateTBTSubInfo2C updateTBTTrapInfo updateTPTurnList updateTPTurnListNew updateTPCrossroadName updateTPFlexibleDestinationName updateLaneInfo updateOperationStatus responseNaviAliveStatus; do grep -q "$m" $K/new-fw/framework/automotive.odex && echo "있음 $m" || echo "없음 $m"; done
```

**(4) deodex**: port.py 와 같은 옵션으로 4개 앱을 국내 EV6 프레임워크에 맞춰 풀었을 때 건너뛴 클래스가 0인지. 결과 smali 는 순정 코드이므로 비공개 폴더에만 둡니다.

```bash
cd $K/new-fw/framework && BCP=$(for b in core conscrypt okhttp core-junit bouncycastle ext framework framework2 telephony-common voip-common mms-common android.policy services apache-xml webviewchromium automotive; do [ -f $b.odex ] && printf '%s.odex:' $b; done) && EXTRA=$(LC_ALL=C ls *.odex | grep -vxF "$(echo "$BCP" | tr ':' '\n')" | tr '\n' ':') && echo "${BCP}${EXTRA%:}" > $K/bcp.txt && cat $K/bcp.txt
```

```bash
for n in HKMC_GPM HKMC_DiPO Iap2ServerApp HKMC_Navi_ExSL; do baksmali x -a 18 -d $K/new-fw/framework -b "$(cat $K/bcp.txt)" -o $K/preflight/$n $K/new-stock/app/$n.odex 2> $K/preflight-$n.err; echo "$n 끝 $? 건너뜀 $(grep -c 'skipping class' $K/preflight-$n.err)"; done
```

네 줄 모두 `끝 0 건너뜀 0` 이면 됩니다. 아니면 `preflight-<앱>.err` 앞부분을 알려 주세요 (순정 코드가 아니라 오류 문구만).

## 6. 기준 자료가 오면 돌릴 명령

받은 자료는 `$K/ref-stock/` (`app/`, `lib/`), `$K/ref-fw/framework/`, `$K/ref-builds/` (`2_tbt/files/`, `3_bridge/files/`) 로 둡니다. 먼저 ref-stock 의 해시가 `patches/ev6/stock` 과 같은지 확인합니다. libautoreceiver 를 손으로 만든 뒤:

```bash
cd ~/HMG-Leafia-Plus && export PATH=$HOME/.local/bin:$PATH && ~/leafia-venv/bin/python tools/port.py --variant cvev_kr --prefix CVEV.KOR. --name "Kia EV6 (Korea)" --new-stock $K/new-stock --new-fw $K/new-fw/framework --ref-variant ev6 --ref-stock $K/ref-stock --ref-fw $K/ref-fw/framework --ref-builds $K/ref-builds --out-builds $K/out-builds --work $K/work --lib-build $K/lib-build/libautoreceiver_infobank.so 2>&1 | tee $K/port.log
```

| 결과 | 다음 할 일 |
|---|---|
| `OK: patches/cvev_kr written ...` | `git status` 확인 → 계획 문서 5번(패키지 빌드)·6번(모의 시험) |
| `STOP: ... merge them by hand:` | 목록만 정리해서 알려 주세요. `.lpd` 를 손으로 고치지 않습니다 |
| `STOP: checks failed:` | `unresolved` / `missing in this framework` 줄을 알려 주세요 |
| `deodex of ... failed` | 5절 (4)의 오류 문구와 같이 알려 주세요 |

## 상태

- 클라우드 작업 환경: lpatch·Python 패키지·port.py 흐름 확인 끝. baksmali/smali 는 사용자 PC 에서 확인할 차례.
- 사용자 PC: 5절 (3) 클러스터 API 11개 모두 있음 (2026-10-29). 4절 준비 → 5절 나머지 점검 → 결과 공유.
- 남은 차단 요인: 기준 자료(ref-stock, ref-fw, ref-builds)와 국내 EV6 용 libautoreceiver 빌드. 모의 시험용 키트(port) 수집.
