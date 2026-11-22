# OCI Secure Workflows

OCI 서버의 Public IP를 제거한 뒤에도 개발·관리와 웹/API 제공을 계속할 수 있도록 접속 방법, 셸 도구, 인프라 예제를 함께 제공합니다. 내 PC에서 서버를 관리하는 경로와 다른 사용자가 서비스를 이용하는 경로를 구분해 선택합니다.

예를 들어 본인은 Bastion으로 SSH 개발을 하고, 동료에게는 Load Balancer의 HTTPS 데모 URL을 제공할 수 있습니다. 여러 사설 서비스를 오가거나 장시간 개발하는 경우에는 sshuttle·Tailscale·기존 회사 VPN도 검토할 수 있습니다. SOCKS5는 제공하는 방법 중 하나이며 필수는 아닙니다.

## 그림으로 먼저 선택하기

**서버에 들어가서 작업하는 일**, **다른 사람에게 서비스를 제공하는 일**, **서버가 외부에 요청하는 일**을 먼저 구분합니다. 예를 들어 웹 화면 하나를 본인이 확인하는 상황과, 고객이 그 웹을 계속 이용하는 상황은 다른 경로를 사용합니다.

```mermaid
flowchart TD
    START{"지금 하려는 일은 무엇인가요?"}
    START -->|내가 서버를 관리하거나 개발| MANAGE{"어떻게 사용할 건가요?"}
    MANAGE -->|한두 서버나 화면에 접속| FIXED["Bastion 고정 포워딩<br/>PC의 로컬 포트를 사설 서비스에 연결"]
    MANAGE -->|여러 사설 서비스를 오가며 사용| MULTI["SOCKS5 또는 sshuttle<br/>앱별 프록시 설정 여부로 비교"]
    MANAGE -->|여러 도구로 장시간 작업| VPN["기존 회사 VPN 또는 Tailscale 검토<br/>사설망 접속 경로를 준비"]
    START -->|다른 사람이 웹사이트를 이용| WEB["HTTPS Load Balancer<br/>웹서비스의 접속 입구"]
    START -->|프로그램이 인증된 API를 호출| API["API Gateway 또는 앱 인증을 갖춘 LB<br/>API 요청을 검사하고 전달"]
    START -->|서버가 외부 API나 패키지 저장소에 요청| NAT["NAT Gateway<br/>사설 서버의 외부 통신 경로"]
    classDef manage fill:#e8f1ff,stroke:#3469a3,color:#142d4e
    classDef service fill:#e9f6ee,stroke:#3e8052,color:#173823
    classDef outbound fill:#fff2df,stroke:#b46b13,color:#4d2a07
    class FIXED,MULTI,VPN manage
    class WEB,API service
    class NAT outbound
```

파란 상자는 본인의 관리 접속, 녹색 상자는 서비스 이용자의 접속, 주황 상자는 서버의 외부 통신을 뜻합니다. Cloudflare Tunnel와 Access는 **외부 중계 서비스 사용이 허용된 환경에서**, 로그인한 사용자에게 웹을 제공하는 또 다른 선택지입니다. 위 그림은 처음 검토할 방법을 고르는 안내이며 구성 전체를 자동 결정하지 않습니다. 이미 회사 VPN으로 대상 서버에 접근할 수 있다면 그 경로부터 확인합니다.

처음 배우는 분은 [상황별 그림으로 이해하는 입문 가이드](docs/explanation/beginner-guide.md)를 먼저 읽으십시오. 각 방법을 **어떤 경우에 쓰는지 → 왜 필요한지 → 누가 무슨 역할을 하는지 → 사용자는 무엇을 입력하는지** 순서로 설명합니다. 용어를 알고 있다면 아래 비교표와 실행 절차로 바로 진행할 수 있습니다.

## 어떤 방법을 선택하나요

| 하고 싶은 일 | 먼저 검토할 방법 | 접속할 때 달라지는 점 |
|---|---|---|
| 본인이 SSH·DB·RDP 또는 개발 웹 화면 몇 개 사용 | Bastion 고정 포트 포워딩 | 터널을 열고 `127.0.0.1:로컬포트`에 접속 |
| 여러 사설 웹을 오가며 브라우저 프록시 설정 가능 | Bastion SOCKS5 | 브라우저에 중계 주소를 지정한 뒤 사설 URL 사용 |
| 여러 사설 TCP 서비스에 앱별 프록시 설정 없이 접근 | sshuttle | Bastion 뒤 Linux VM을 경유하도록 선택한 사설 대역 연결을 중계 |
| 여러 앱으로 장시간 개발·관리 | 기존 회사 VPN 또는 Tailscale | 연결된 사설망 주소 또는 Tailscale 주소 사용 |
| 동료·고객에게 웹서비스 URL 제공 | HTTPS Load Balancer | 사용자는 터널 없이 서비스 URL로 접속, 앱 인증 필요 |
| HTTP API에 토큰 검증·호출량 제한 적용 | API Gateway | API 입구에서 요청을 검사한 뒤 사설 백엔드로 전달 |
| 허용한 사용자에게 외부 중계를 통한 웹 접근 제공 | Cloudflare Tunnel와 Access | 서버의 외부 연결과 사용자 로그인 정책으로 웹 URL 제공 |

서버가 외부 API를 호출하거나 패키지를 내려받는 문제는 **NAT Gateway 같은 아웃바운드 경로**로 해결합니다. 위 표의 PC→서버 접속 방법과 통신 방향이 다릅니다. Public IP 제거만으로 모든 보안 정책이 충족되는 것은 아니므로 실제 정책과 finding을 확인해야 합니다.

처음에는 **고정 포워딩으로 본인의 접속 하나를 성공시키는 것**부터 권합니다. 서비스가 늘거나 연결 시간이 불편해지면 다른 방식을 선택합니다. [방법별 비교와 제약](docs/guides/alternatives.md) · [주소와 접속 원리 설명](docs/explanation/access-model.md)

## 각 방식에서 무엇이 연결되나요

아래 경로에서 화살표는 접속·요청의 흐름을 단순화한 것입니다. `사설 VM`은 인터넷에서 바로 접속할 수 있는 주소 없이 운영하는 클라우드 서버입니다. `127.0.0.1`은 그 주소를 입력한 PC 자신을 뜻합니다.

```text
고정 포워딩  PC의 localhost:8080 → Bastion → 사설 VM:8080
SOCKS5      프록시를 설정한 앱 → PC의 중계기 → Bastion → 앱이 요청한 사설 목적지
sshuttle    선택한 사설 대역으로 향하는 앱 연결 → SSH → Bastion 뒤 Linux VM → 목적지
Tailscale   PC 클라이언트 → 등록한 서버 또는 승인된 subnet router → 사설 서비스
웹서비스    사용자 브라우저 → HTTPS LB 또는 API Gateway → 사설 웹/API
Cloudflare  사용자 브라우저 → Cloudflare Access/Tunnel → cloudflared → 웹앱
외부 통신   사설 VM → NAT → 외부 API·패키지 저장소
```

Bastion은 별도 점프 VM을 운영하지 않고 제한된 시간 동안 접속하게 해 주는 OCI 서비스입니다. 고정 포워딩은 연결할 목적지를 미리 정하고, SOCKS5는 앱이 요청마다 목적지를 알려 줍니다. SOCKS5 중계 주소 `127.0.0.1:1080`은 **브라우저 프록시 설정에 넣는 주소**이며 주소창에는 실제 사설 서비스 URL을 입력합니다.

sshuttle도 이 저장소의 구성에서는 Bastion을 통과하므로 세션 최대 3시간 제약이 남습니다. Tailscale은 별도 클라이언트와 계정·접근 정책이 필요하고, Cloudflare Tunnel은 터널 외에 Access 로그인 정책과 DNS 설정이 필요합니다. 어느 방식도 기존 서비스의 로그인이나 네트워크 허용 규칙을 자동으로 대신하지 않습니다.

## 설치 없이 명령 미리보기

Git, Python 3.10 이상, POSIX 셸이 있으면 아래 예제를 실행할 수 있습니다. 외부 접속 클라이언트는 선택한 방법을 실제 실행할 때 준비합니다. 셸 예제는 macOS·Linux 계열 환경을 대상으로 하며 실제 검증 환경은 [검증 결과](docs/validation.md)에 있습니다.

```sh
git clone https://github.com/devmrko/oci-secure-workflows.git
cd oci-secure-workflows
sh scripts/workflow.sh
OCI_ACCESS_CONFIG=config/access.example.json sh scripts/workflow.sh list
OCI_ACCESS_CONFIG=config/access.example.json sh scripts/workflow.sh plan dev-web
```

도움말과 대상 목록이 나오고 계획에 `127.0.0.1:8080`과 `10.0.1.10:8080`이 표시되면 미리보기 성공입니다. 예제 설정은 실제 자원을 가리키지 않으며 이 단계는 OCI 조회·세션 생성·방화벽 변경을 하지 않습니다.

## 실제 접속 전에 준비할 것

| 방법 | 실행 위치와 준비물 |
|---|---|
| Bastion 고정 포워딩·SOCKS5 | PC에 OCI CLI 인증·SSH 키, OCI에 Bastion·접속 허용 CIDR·대상 방화벽 |
| sshuttle | PC에 sshuttle·로컬 방화벽 권한, Bastion 뒤 Linux VM에 Python 3.10 이상, VM에서 목적지 접근 |
| Tailscale | PC와 서버 또는 subnet router에 클라이언트·조직 로그인, 경로 승인·접근 정책 |
| Cloudflare | 웹앱에 도달하는 서버에 cloudflared·로컬 named tunnel 설정·credentials, 계정·도메인·Access 정책 |
| LB·API Gateway·NAT | Terraform 1.7 이상, OCI 프로파일·권한·기존 네트워크, 방법별 인증서·인증·라우팅 설정 |

예제와 도우미가 모든 인프라·계정·서비스 설치를 끝내 주는 것은 아닙니다. 외부 서비스의 사용 가능 여부와 요금도 확인합니다. 준비 항목과 설치 안내는 [방법별 쉬운 실행](docs/guides/easy-workflows.md)에 있습니다.

## 첫 실제 접속은 고정 포워딩으로

먼저 [Bastion 준비](docs/guides/bastion.md)를 완료하고 대상 서버에서 웹앱이 실행 중인지 확인합니다. 예제는 서버의 사설 IP에서 접근 가능한 8080 포트를 사용합니다. 기존 `config/access.json`이 없다면 아래처럼 복사하고, Bastion OCID·리전·키 경로와 `dev-web`의 서버 IP·포트를 실제 값으로 수정합니다.

```sh
cp config/access.example.json config/access.json
sh scripts/workflow.sh validate
sh scripts/workflow.sh doctor
sh scripts/workflow.sh plan dev-web
sh scripts/workflow.sh connect dev-web --execute
```

터널 터미널을 열어 둔 채 브라우저에서 `http://127.0.0.1:8080`을 엽니다. 대상 웹앱의 예상 화면이나 응답이 나오면 실제 접속 성공입니다. 브라우저 프록시 설정은 필요 없습니다. `doctor`는 로컬 도구와 파일만 확인하므로 성공했다고 네트워크 연결까지 검증된 것은 아닙니다.

SSH 개발은 `dev-ssh`, DB는 `dev-db`, RDP는 `dev-rdp` target을 실제 환경에 맞춰 사용합니다. 종료는 터널의 `Ctrl+C`이며 OCI 세션은 출력된 정리 명령으로 삭제하거나 TTL 만료를 기다립니다. [도구별 접속 주소와 종료 방법](docs/guides/clients.md)

## 다른 방법도 같은 셸에서 선택

아래는 **명령 미리보기**입니다. 실제 실행에는 `--execute`를 추가합니다. 준비와 성공 확인·종료·복구 절차를 읽고 사용합니다.

```sh
# 브라우저에 SOCKS5 프록시를 설정할 경우
sh scripts/workflow.sh connect seoul-socks
# 먼저 다른 터미널에서 dev-ssh 터널을 열어 두어야 합니다.
sh scripts/workflow.sh sshuttle dev-ssh --cidr 10.0.1.0/24
# 설치된 Tailscale의 상태 조회 명령 미리보기
sh scripts/workflow.sh tailscale status
# 로컬 named tunnel의 ingress 검사 명령 미리보기
sh scripts/workflow.sh cloudflare validate --config config/cloudflared.example.yml
```

- [SOCKS5 브라우저 따라하기](docs/guides/socks5-walkthrough.md): 중계 주소·DNS·원래 브라우저 설정으로 복구.
- [sshuttle 실행](docs/guides/easy-workflows.md#sshuttle): 두 터미널 순서, 사설 대역·DNS 범위와 방화벽 권한.
- [Tailscale 실행](docs/guides/easy-workflows.md#tailscale): 서버 직접 등록과 subnet router의 차이, 광고·승인·접근 정책.
- [Cloudflare 실행](docs/guides/easy-workflows.md#cloudflare-tunnel): named tunnel 준비, Access 인증과 DNS, 설정 검증·연결.
- [기존 회사망 연결](docs/guides/alternatives.md#회사망-연결-요청에-필요한-정보): 회사 VPN에서 대상 VCN까지 도달하는지 확인.

`--execute` 없는 `connect`, `sshuttle`, `tailscale`, `cloudflare`는 외부 클라이언트를 실행하지 않습니다. 반면 `infra`의 init·validate·plan·show는 즉시 해당 Terraform 명령을 실행하며, apply는 저장된 계획과 스택 이름 확인 후 적용합니다.

## 여러 사용자용 웹과 서버 외부 통신

웹서비스의 공개 입구는 LB, API 요청 정책은 API Gateway, 서버 아웃바운드는 NAT 예제를 사용합니다. 필요한 것만 각각 선택하며 모두 설치할 필요는 없습니다. 각 Terraform 스택은 별도 state를 사용하고 기존 Compute의 Public IP나 기존 서브넷 경로를 자동 변경하지 않습니다.

```sh
cp terraform/load-balancer/terraform.example.tfvars terraform/load-balancer/terraform.tfvars
# 실제 값을 입력한 뒤 실행
sh scripts/workflow.sh infra load-balancer init
sh scripts/workflow.sh infra load-balancer validate
sh scripts/workflow.sh infra load-balancer plan
sh scripts/workflow.sh infra load-balancer show
```

plan은 OCI를 조회하고 로컬 계획을 만들지만 자원을 생성하지 않습니다. 인증서·백엔드 방화벽 연결·DNS·사용자 인증 등 후속 설정은 [인프라 구성](docs/guides/infrastructure.md)에서 확인합니다. 실제 Public IP 제거는 [전환과 복구 절차](docs/guides/migration.md)를 따릅니다.

## 어디까지 검증했나요

| 범위 | 확인한 내용 | 추가 환경 검증 |
|---|---|---|
| 셸·Python 도우미 | 35개 테스트 통과, 미리보기·인자 전달·실패 처리·패키지 제외 규칙 | 실제 계정·키·네트워크 연결 |
| sshuttle·OpenSSH | 실제 sshuttle 옵션 파서와 `ssh -G` 구성 해석 | sudo 방화벽 변경·원격 Python·사설 트래픽 |
| Cloudflare | 공식 cloudflared로 예제 ingress·호스트 매칭·404 규칙 검사 | 실제 터널·DNS·Access 허용과 거부 |
| Tailscale | 대체 실행 파일로 셸 호출과 전달 인자 검사 | 실제 로그인·경로·접근 정책 |
| Terraform | 네 스택 validate와 8개 mock plan 테스트 통과 | 실제 plan/apply·서비스 동작·정책 finding 해소 |

```sh
sh scripts/test.sh
```

실제 클라이언트 도구가 없는 기본 테스트에서는 해당 옵션 검사가 skip될 수 있습니다. 35개 전체 검증을 재현하는 방법과 버전은 [검증 결과](docs/validation.md)에 있습니다. 현재는 실제 클라우드 트래픽 검증 전 단계의 도구이며 운영 검증 완료를 의미하지 않습니다.

## 상세 문서와 배포 파일

[그림으로 배우는 입문 가이드](docs/explanation/beginner-guide.md) · [주소와 접속 원리](docs/explanation/access-model.md) · [방법 비교](docs/guides/alternatives.md) · [셸 사용 절차](docs/guides/easy-workflows.md) · [명령과 설정 참조](docs/reference/commands.md) · [공식 출처](docs/reference/sources.md) · [설계](docs/design/secure-workflows.md) · [설계 결정](docs/adr/0001-access-paths.md)

`python3 scripts/package.py`를 실행하면 상위 디렉터리에 `oci-secure-workflows.zip`이 생성됩니다. 소스·문서·예제만 포함하며 실제 설정·키·Terraform state와 plan은 제외합니다. 외부 참고 코드는 복사하지 않았고, 이 저장소의 별도 재배포 라이선스는 아직 지정하지 않았습니다.
