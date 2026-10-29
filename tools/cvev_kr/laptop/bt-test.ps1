# 국내 EV6 무선 CarPlay: 블루투스 경로 시험 (노트북용, 읽기 전용 + DiPO 한 번 다시 시작)
# 하는 일: ADB 연결 -> 새 DiPO 설치 확인 -> 로그 받기 시작 -> DiPO 다시 시작 ->
#          아이폰 블루투스 다시 연결 (사람이 함) -> 로그 멈춤 -> 브릿지 줄만 골라 저장
# 결과: 이 파일 옆 logs\bt-result.txt (블루투스 주소는 가려짐). 전체 로그 bt-live.txt 는 공유하지 마세요.
param([string]$Ip = '192.168.0.1')

$ErrorActionPreference = 'Continue'
$adb = 'C:\platform-tools\adb.exe'
$want = '22473c7334da398b4b64eba83c4784c2'
$dir = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$live = Join-Path $dir 'bt-live.txt'
$result = Join-Path $dir 'bt-result.txt'
$mask = '([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}'

function Step($t) { Write-Host ''; Write-Host "== $t" -ForegroundColor Cyan }
function Adb { & $adb -s $script:dev @args }

if (-not (Test-Path $adb)) { Write-Host "adb 가 없습니다: $adb" -ForegroundColor Red; Read-Host '끝내려면 Enter'; exit 1 }

Step "1. ADB 연결 ($Ip`:5555)"
& $adb disconnect | Out-Null
& $adb connect "$Ip`:5555"
$script:dev = "$Ip`:5555"
$state = (& $adb devices) | Select-String ([regex]::Escape($dev))
if (-not (($state | % Line) -match '\sdevice\s*$')) {
    Write-Host '연결되지 않았습니다. 노트북이 차 핫스팟(Kia_x5UE)에 붙어 있는지, 주소가 맞는지 확인하세요.' -ForegroundColor Red
    Write-Host '주소가 다르면: 이 파일을 다시 실행할 때 -Ip <주소> 를 붙이세요.'
    Read-Host '끝내려면 Enter'; exit 1
}

Step '2. 설치된 DiPO 확인'
$md5 = (Adb shell "nemesis root -c 'md5 /system/app/HKMC_DiPO.apk'") -join ' '
Write-Host $md5
if ($md5 -notmatch $want) { Write-Host "새 패키지의 DiPO 가 아닙니다 (기대값 $want). 패키지를 다시 설치한 뒤 시험하세요." -ForegroundColor Yellow }

Step '3. 로그 받기 시작'
Adb logcat -c
$p = Start-Process -FilePath $adb -ArgumentList "-s $dev logcat -v time" -RedirectStandardOutput $live -NoNewWindow -PassThru
Start-Sleep -Seconds 2

Step '4. DiPO 다시 시작 (시스템 앱이라 바로 다시 켜집니다)'
function DipoPid { foreach ($l in (Adb shell ps)) { if ($l -match 'com\.daudio\.app\.dipo\s*$') { return ($l -split '\s+')[1] } }; return $null }
$old = DipoPid
Write-Host "지금 DiPO PID: $old"
if ($old) {
    Adb shell "nemesis root -c 'kill $old'" | Out-Null
    $new = $null
    for ($i = 0; $i -lt 30; $i++) { Start-Sleep -Seconds 1; $new = DipoPid; if ($new -and $new -ne $old) { break } }
    if ($new -and $new -ne $old) { Write-Host "DiPO 다시 시작됨: PID $new" -ForegroundColor Green }
    else { Write-Host 'DiPO 가 30초 안에 다시 뜨지 않았습니다. 시험 뒤 헤드유닛을 재시작하세요.' -ForegroundColor Yellow }
} else { Write-Host 'DiPO 프로세스를 찾지 못했습니다.' -ForegroundColor Yellow; $new = $null }
Start-Sleep -Seconds 10

Step '5. 이제 아이폰 차례입니다'
Write-Host '케이블은 꽂지 마세요. 아이폰의 블루투스를 껐다 켜서 차와 다시 연결하세요.'
Write-Host '연결되면 30~40초 기다린 뒤 (화면에 무엇이 뜨는지 봐 두세요) Enter 를 누르세요.'
Read-Host '준비되면 Enter'

Step '6. 로그 멈추고 고르기'
Stop-Process -Id $p.Id -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
$lines = @()
$lines += '### 브릿지·충돌 줄 (EV6CPWL / FATAL / VerifyError)'
$lines += Select-String -Path $live -Pattern 'EV6CPWL|FATAL|VerifyError|VFY' | % { $_.Line -replace $mask, 'XX:XX:XX:XX:XX:XX' } | Select-Object -First 80
$lines += ''
$lines += '### DiPO 블루투스 관리자 쪽 줄'
$pidPat = if ($new) { "\(\s*$new\)" } else { 'DIPO_NO_PID' }
$lines += Select-String -Path $live -Pattern "DipoBluetooth|BTCMService|onServiceConnected|HfDeviceBTCM|$pidPat" | % { $_.Line -replace $mask, 'XX:XX:XX:XX:XX:XX' } | Select-Object -First 60
$lines | Out-File -Encoding utf8 $result
$lines | Select-Object -First 70 | % { Write-Host $_ }

Step '끝'
Write-Host "결과 파일: $result"
Write-Host '이 파일을 열어 아이폰 이름·일련번호·전화번호가 보이면 XXXX 로 바꾼 뒤 보내 주세요.'
Write-Host "전체 로그 ($live) 는 공유하지 마세요."
Read-Host '끝내려면 Enter'
