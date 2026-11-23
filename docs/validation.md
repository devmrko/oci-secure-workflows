# 검증 결과

최종 문서·예제 검증: 2026-11-23. 기존 인프라 검증: 2026-11-22. 실행 환경: macOS arm64, Python 3.15.0, OCI CLI 3.88.0, Terraform 1.14.0, OCI provider 9.14.0.

2026-11-23에는 Worksheet·Dashboard 관리 Cloudflare 도우미를 포함해 전체 40개 테스트를 통과했습니다. 실제 ADB Worksheet와 Cloudflare Tunnel·Access 웹 접속도 확인했습니다. Terraform 코드는 변경하지 않았습니다.

## 수행한 검증

| 범위 | 결과 |
|---|---|
| Python unittest | 40개 통과, skip 없음. 기존 35개, Worksheet 3개, Cloudflare 원격 관리 모드의 토큰 비출력·입력 및 권한 제한 2개 |
| 셸 진입점 | 미리보기 시 외부 프로그램 미실행, --execute 시 전달 인자·오류 코드, 다른 작업 디렉터리와 공백 경로를 실제 하위 프로세스로 검증. 외부 네트워크 클라이언트 실행은 기록용 대체 프로그램 사용 |
| sshuttle 2.0.0 | 실제 패키지의 옵션 파서로 remote·CIDR·DNS 옵션 확인. 실제 방화벽·트래픽 시험과 별개 |
| OpenSSH | 생성된 SSH 옵션을 실제 `ssh -G`로 해석, localhost 포트·host key alias 확인. 네트워크 접속 없음 |
| cloudflared 로컬 설정 검사 | 공식 배포물 2026.11.1 SHA256 확인 후 예제 ingress validate, URL별 사설 backend 매칭과 알 수 없는 호스트 404 매칭 검사. 이 설정 검사에서는 외부 터널 연결 없음 |
| Cloudflare 실제 접속 | 별도 Quick Tunnel 외부 응답 일치와 HTTP/2 확인. Dashboard 관리 named tunnel을 셸 도우미로 실행하고 Access 로그인 후 가상 원본 응답·HTTP 200 지표 확인. curl의 익명·위조 쿠키 요청은 HTTP 302로 Access 로그인 이동 |
| Cloudflare OCI NAT 실제 접속 | Public IPv4·IPv6 없는 단일 NIC VM, 사설 서브넷의 기본 경로가 NAT만 사용. 외부 관측 IP와 NAT IP 일치. HTTP/2·QUIC Quick Tunnel 각각 외부 HTTPS 200·무작위 표식 일치. QUIC 커넥터 HTTP 200 지표도 확인 |
| Bastion Terraform validate | 통과 |
| HTTPS LB Terraform validate | 통과 |
| API Gateway Terraform validate | 통과 |
| NAT Terraform validate | 통과 |
| Terraform mock plan test | 8개 통과. Bastion 3, LB 1, API Gateway 2, NAT 2 |
| Terraform fmt | 적용 후 check 통과 |
| Bash 구문 | `bash -n scripts/infra.sh` 통과 |
| CLI 예제 | example 설정의 list, validate, plan 실행 확인 |
| 문서 실행 경로 | README의 도움말·목록·고정 포워딩 계획·sshuttle 계획·Tailscale 미리보기·Cloudflare 미리보기 6개 명령 실행. 로컬 링크·제목 anchor와 전체 문서의 셸 블록 구문 검사 통과 |
| 문서 구조·다이어그램 | 로컬 링크·제목 anchor·셸 블록 구문과 Mermaid 11 파서로 그림 24개 문법 검사 통과. 다이어그램의 브라우저 시각 렌더링 검사와 별개 |
| ADB SQL 예제 | 관리형 서비스 설정의 offline validate, mTLS 11522→1522·TLS 11521→1521·SOCKS 1080 계획 확인. SQL·wallet 시험 없음 |
| 실제 ADB Worksheet | 기존 점프 VM → ADB 사설 IP:443 경로에서 HTTP 200·TLS 검증. 고정 포워딩+브라우저 매핑, SOCKS5+원격 DNS 두 경우 모두 실제 Chrome 로그인 화면과 리소스 15건 정상. HTTP 오류·요청 실패·JS 오류 없음. 로그인·SQL·SSO는 시험하지 않음 |
| 다중 목적지 | sshuttle·Tailscale의 두 CIDR 명령 미리보기 확인. 실제 cloudflared로 다중 웹 설정 검사, 두 도메인의 backend 분기와 미등록 호스트 404 확인 |
| OCI CLI 명령 계약 | 설치된 CLI의 help·JSON 샘플과 고정/동적 세션 입력 대조 |

Terraform mock test는 `mock_provider "oci"`로 실제 OCI API 호출을 대체하고 `command = plan`만 실행합니다. 실제 프로파일·키·인프라를 사용하지 않습니다. Provider 바이너리는 첫 init에서 서명을 확인한 것을 나머지 스택의 로컬 검증에도 재사용했습니다. 환경별 인증·정책·서비스 내부 제약을 모의 테스트가 검증하지는 않습니다.

## 재현

저장소 루트 `oci-secure-workflows/`에서 실행합니다. init은 provider 다운로드를 위해 인터넷에 접속합니다.

```sh
sh scripts/test.sh
terraform fmt -check -recursive terraform
```

기본 실행에서 sshuttle 패키지나 `CLOUDFLARED_BIN`이 없으면 해당 실제 클라이언트 계약 검사는 skip으로 표시합니다. 40개 전체 검사를 재현하려면 테스트 전용 환경에 sshuttle 2.0.0을 설치하고 공식 cloudflared 실행 파일을 준비합니다. 클라이언트 설치 경로에 맞춰 아래 값을 바꿉니다.

```sh
python3 -m venv .venv-test
.venv-test/bin/python -m pip install sshuttle==2.0.0
PYTHON_BIN=.venv-test/bin/python CLOUDFLARED_BIN=/absolute/path/to/cloudflared sh scripts/test.sh --clients
```

이 unittest는 로그인·경로 광고·방화벽 변경·DNS 등록을 수행하지 않습니다. 별도의 Cloudflare 실제 시험과 구분합니다. Tailscale의 명령 호출 경로는 대체 실행 파일로 검사했으며 실제 클라이언트의 로그인·경로 적용은 수행하지 않았습니다. 설치된 macOS Tailscale launcher가 preferences 로딩 오류를 반환해 로컬 실제 CLI 검사도 성공으로 기록하지 않았습니다.

각 스택에서 다음 명령을 반복합니다. `bastion` 대신 `load-balancer`, `api-gateway`, `nat`도 실행합니다.

```sh
terraform -chdir=terraform/bastion init -backend=false -input=false
terraform -chdir=terraform/bastion validate
terraform -chdir=terraform/bastion test
```

## 실제 환경에서 남은 확인

- 실제 값으로 만든 Terraform plan과 대상 tenancy·region·compartment·기존 자원 중복 확인.
- Bastion 세션 생성·SSH/SOCKS5 연결, 공인 출구 allowlist, 회사 outbound TCP 22, 대상 OS 방화벽.
- LB 인증서 권한·health·로그인·업로드·WebSocket/SSE와 내부 TLS cipher 정책.
- API Gateway JWT issuer/audience/JWKS 접근·토큰 검증·권한·실제 API 제한.
- NAT 전환 시 공유 서브넷·SGW·DRG·피어링·출구 IP 의존성.
- Public IP/IPv6 노출 제거와 Security Central finding 재평가.
- sshuttle의 실제 로컬 방화벽 적용·원격 Python·DNS·네트워크 경로와 종료 복구.
- Tailscale 로그인·광고 경로 교체·승인·접근 정책·클라이언트 경로 수신과 복구.
- Cloudflare의 다른 실제 사용자의 권한 거부·다른 IdP·이메일 PIN·세션 회수·장애 복구·성능.
- ADB Private Endpoint 전환·공개 접속 차단·NSG·DNS·wallet·클라이언트별 TLS 이름 검증·SQL 조회·웹 443 접속. 다중 서버의 실제 동시 트래픽·용량·장애 영향.

Terraform의 실제 OCI plan/apply, 관리형 Bastion 세션 생성, OCI DNS 변경과 기존 자원의 Public IP 제거는 수행하지 않았습니다. NAT 시험에서는 CLI로 전용 VM·사설 서브넷·라우트·보안 목록을 만들고 기존 NAT Gateway를 재사용했습니다. 기존 서비스의 라우트·보안 목록은 변경하지 않았습니다. Worksheet 시험에 기존 사설 테스트 ADB를 임시 기동하고 종료 후 STOPPED로 복구했습니다. 점프 VM의 설정과 데이터는 변경하지 않았고 로컬 SSH 터널도 종료했습니다. Cloudflare에서는 별도 테스트 앱·정책·named tunnel·DNS를 생성해 시험했습니다.

## Cloudflare 실제 시험의 조건

- macOS 사설 LAN 호스트에서 127.0.0.1에만 가상 원본을 바인딩. 인바운드 포트나 라우터 포워딩을 추가하지 않았습니다. 이 macOS 시험과 아래 OCI NAT 시험은 별도로 수행했습니다.
- 공식 cloudflared 2026.11.1. Quick Tunnel의 외부 응답과 표식 일치, 별도 OCI VM의 외부 요청을 확인했습니다. HTTP/2도 명시적으로 연결했습니다.
- 사용자 계정의 Zero Trust 활성화 후 전용 앱·허용 정책·DNS·Dashboard 관리 터널 구성. 셸 도우미의 `--token-file` 실행과 실제 브라우저의 Cloudflare 로그인 후 원본 응답을 확인했습니다.
- curl에서 익명·위조 쿠키 각각 302와 실제 Cloudflare Access 로그인 목적지를 확인했습니다. Python urllib의 403은 별도 필터가 개입할 수 있어 Access 판정의 증거로 사용하지 않았습니다.
- 단일 허용 사용자 로그인과 익명 차단의 시험입니다. 다른 사용자의 로그인·권한 거부나 이메일 PIN 성공을 검증한 것으로 기록하지 않습니다. [실행 절차](guides/cloudflare.md)
- 시험 후 앱·전용 정책·터널·DNS 삭제를 Dashboard에서 확인했습니다. 로컬 커넥터·가상 원본을 종료하고 임시 토큰 파일을 폐기했습니다. 사용자가 활성화한 Free 플랜은 유지했습니다.

## OCI NAT 경유 Cloudflare 시험의 조건

- 2026-11-23, 서울 리전의 새 VM.Standard.E5.Flex(1 OCPU·2 GB), Oracle Linux 8.10, 공식 Linux amd64 cloudflared 2026.11.1 사용. GitHub 공식 배포물의 SHA256과 전송 후 해시가 일치했습니다.
- 단일 VNIC의 Public IP가 null이고 공인 IPv6도 없음을 OCI API와 OS에서 확인했습니다. 전용 사설 서브넷은 Public IP 할당 금지, 기본 경로는 기존 NAT Gateway 하나입니다. 외부에서 관측한 출구 IP가 NAT의 공인 IP와 일치했습니다.
- 테스트 보안 목록은 기존 점프 VM의 사설 IP에서 오는 SSH 22만 인바운드 허용했습니다. 외부 터널은 TCP/UDP 7844, API는 TCP 443, DNS는 VCN resolver로 허용했습니다. 웹 원본은 127.0.0.1:19090에만 바인딩했습니다.
- SSH 관리는 기존 점프 VM을 사용했지만, 웹 요청은 점프 VM이나 SSH 포워딩을 경유하지 않았습니다. VCN에 다른 용도의 IGW는 존재하며 **테스트 서브넷의 경로에는 IGW가 없었습니다.**
- HTTP/2와 QUIC를 각각 명시한 Quick Tunnel을 만들고 PC의 curl에서 기본 인증서 검증으로 HTTPS 200·가상 원본의 무작위 표식 일치를 확인했습니다. QUIC 커넥터에서도 HTTP 200 지표 1건을 확인했습니다.
- 종료 후 VM·부트 볼륨의 TERMINATED 상태와 전용 서브넷·라우트·보안 목록 삭제를 확인했습니다. 임시 SSH 키도 폐기했으며 재사용 NAT와 기존 점프 VM은 유지했습니다.
- 이 시험은 NAT를 통한 Tunnel 전송 경로 검증입니다. 위 macOS의 named tunnel·Access 시험과 결합한 하나의 시험으로 기록하지 않습니다. [NAT 시험 재현](guides/cloudflare.md#oci-nat-출구-시험)

## Worksheet 실제 시험의 조건

- macOS arm64, curl, OpenSSH, Playwright 1.65.1과 설치된 Chrome 157.0.8103.80의 headless 세션. TLS 오류 무시 옵션은 사용하지 않았습니다.
- PC → 기존 점프 VM의 SSH → 기존 ADB Private Endpoint. **관리형 OCI Bastion을 시험한 것이 아닙니다.**
- PC·다른 VCN을 주 NIC로 쓰는 VM의 DNS는 공용 IP, ADB와 같은 VCN의 점프 VM은 사설 IP 반환. 다중 NIC 추가만으로 기본 DNS·경로가 바뀌지 않는 점 확인.
- 실제 호스트·IP·계정·키·화면 원본은 공개 저장소에 포함하지 않았습니다. [재현 절차와 도우미](guides/worksheet.md)
