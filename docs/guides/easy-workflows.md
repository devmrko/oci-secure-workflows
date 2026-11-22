# 방법별 셸 명령으로 쉽게 실행

`sh scripts/workflow.sh` 하나로 접속 방법을 선택합니다. 기본은 명령 미리보기이며, `--execute`에서 해당 도구를 실행합니다. 이 문서의 실제 실행 명령은 계정·키·네트워크 준비를 마친 뒤 사용합니다. 도구 설치와 계정 생성, 네트워크 설정 전체를 자동으로 처리하지는 않습니다.

## 먼저 방법 선택

| 필요한 일 | 실행 방법 | 추가 준비 |
|---|---|---|
| SSH·웹 화면 하나·DB·RDP | `connect TARGET` | OCI Bastion, CLI 인증, 키 |
| 여러 사설 웹을 브라우저 프록시로 사용 | SOCKS target으로 `connect` | 브라우저 SOCKS5 설정 |
| 프록시 없이 여러 사설 서비스 사용 | `sshuttle TARGET --cidr ...` | 먼저 연 Bastion SSH 터널, 원격 Linux/Python, 로컬 방화벽 권한 |
| 장시간 여러 앱·서버에 접근 | `tailscale ...` | 조직 계정·클라이언트, 필요 시 subnet router |
| 로그인한 사용자에게 웹 URL 제공 | `cloudflare ...` | Cloudflare 계정·도메인·Access 정책·named tunnel |
| 일반 서비스 웹/API 공개 | `infra load-balancer ...` 등 | OCI 권한, 인증서, DNS·앱 인증 |

프록시 설정이 번거롭고 대상이 적다면 고정 포워딩부터 사용하십시오. sshuttle도 Bastion을 경유하면 최대 3시간 세션 제약이 남습니다. Bastion 세션 수명과 독립된 장기 접속이 필요하면 승인된 VPN이나 Tailscale 구성을 검토합니다. [세부 비교](alternatives.md)

## 공통 준비

저장소 루트에서 실행합니다. Python 3.10 이상과 선택한 방법의 외부 CLI가 필요합니다. `sh scripts/workflow.sh`를 인자 없이 실행하면 도움말을 볼 수 있습니다.

```sh
# 예제 설정으로 미리보기만 하기
OCI_ACCESS_CONFIG=config/access.example.json sh scripts/workflow.sh list
```

Bastion을 실제 사용하려면 기존 파일이 없는 경우 예제를 복사하고 실제 값을 입력합니다.

```sh
cp config/access.example.json config/access.json
sh scripts/workflow.sh validate
sh scripts/workflow.sh doctor
```

`OCI_ACCESS_CONFIG`로 다른 설정 파일을 선택할 수 있습니다. `PYTHON_BIN`으로 Python 실행 파일을 지정할 수도 있습니다. 셸 도구는 현재 디렉터리와 무관하게 저장소 내부 스크립트를 찾으며 설정·키 내용은 명령에 삽입하지 않습니다.

### 어떤 값을 바꾸나요

예제 주소와 이름은 사용자의 실제 환경으로 바꿔야 합니다. 전체 서비스를 설치할 필요는 없고 선택한 방법의 항목만 준비합니다.

| 설정 | 예제 | 바꿀 값 |
|---|---|---|
| `profile` | `DEFAULT` | 실제 OCI 테넌시에 인증된 CLI 프로파일 이름 |
| `regions.REGION.bastion_id` | `ocid1.bastion...REPLACE` | 대상 VCN의 Bastion OCID |
| `public_key`, `private_key` | `~/.ssh/oci-bastion...` | Bastion 세션 인증에 쓸 한 쌍의 로컬 키 경로 |
| `targets.dev-web.host`, `port` | `10.0.1.10`, `8080` | 웹앱이 실제 실행 중인 사설 IP와 포트 |
| `targets.dev-ssh.user`, `identity_file` | `opc`, `~/.ssh/oci-vm` | VM 로그인 사용자와 해당 VM의 SSH 키 |
| `local_port` | `8080` 또는 `2222` | PC에서 비어 있는 포트. 이후 앱이 이 포트에 접속 |

PC의 `127.0.0.1`과 VM의 `127.0.0.1`은 서로 다른 컴퓨터입니다. Bastion에서 VM의 사설 주소로 연결하려면 웹앱이 해당 인터페이스에서 요청을 받을 수 있어야 합니다. 접속 확인은 가능하면 단순한 IP·포트부터 시작하고, 도메인·TLS·로그인 순서로 확장합니다.

## 고정 포트 포워딩

본인의 개발 웹 화면 하나를 열 때 사용합니다. [Bastion 준비](bastion.md)를 완료하고 target이 실제 VM과 포트를 가리키는지 확인합니다.

```sh
sh scripts/workflow.sh plan dev-web
sh scripts/workflow.sh connect dev-web --execute
```

터미널을 열어 둔 상태에서 브라우저에 `http://127.0.0.1:8080`을 입력합니다. 프록시 설정은 필요 없습니다. SSH는 `dev-ssh`, DB는 `dev-db`, RDP는 `dev-rdp`처럼 대상 설정을 바꿔 같은 명령을 사용합니다.

```sh
sh scripts/workflow.sh connect dev-ssh --execute
# 다른 터미널에서 SSH 설정 블록을 확인하고 기존 ~/.ssh/config에 추가
sh scripts/workflow.sh ssh-config dev-ssh
```

종료는 터널 터미널의 `Ctrl+C`입니다. 남은 OCI 세션은 출력된 정리 명령으로 삭제하거나 TTL 만료를 기다립니다.

## SOCKS5

```sh
sh scripts/workflow.sh connect seoul-socks --execute
```

브라우저에 SOCKS5 `127.0.0.1:1080`을 설정하고 주소창에는 사설 서비스 URL을 입력합니다. 종료 시 브라우저 프록시를 원래 값으로 복구합니다. [브라우저 설정부터 종료까지](socks5-walkthrough.md)

## sshuttle

브라우저마다 프록시를 설정하지 않고 지정한 사설 대역의 TCP 서비스를 이용할 때 선택합니다.

```text
앱 → 로컬 sshuttle → localhost:2222의 SSH 연결
                  → OCI Bastion → 사설 Linux VM → 다른 사설 서비스
```

sshuttle은 **사설 Linux VM에서 Python을 실행**합니다. 관리형 Bastion 자체에 sshuttle을 실행시키는 구조가 아닙니다. 현재 sshuttle 2.0.0은 PC와 원격 서버에 Python 3.10 이상을 요구합니다. PC에는 선택한 OS 방식에 맞는 방화벽 도구와 관리자 권한이 필요합니다. macOS의 일반 pf 방식은 TCP/DNS를 대상으로 하므로 UDP 전체나 ping까지 된다고 가정하지 않습니다.

1. [공식 설치 안내](https://sshuttle.readthedocs.io/en/stable/installation.html)에 따라 sshuttle을 설치합니다. 전역 Python 대신 도구 전용 환경을 써도 됩니다.
2. 원격 Linux VM이 목표 서비스에 연결할 수 있는지, 회사·집의 사설 대역이 목적지 CIDR과 충돌하지 않는지 확인합니다.
3. 터미널 1에서 Bastion SSH 터널을 엽니다.

```sh
sh scripts/workflow.sh connect dev-ssh --execute
```

4. 터미널 2에서 `dev-ssh`의 VM 사용자와 키로 SSH 로그인이 되는지 먼저 확인합니다. 출력한 [SSH 설정](clients.md#ssh와-vs-code)을 적용했다면 `ssh dev-ssh`를 사용합니다. 확인 후 해당 SSH 셸에서는 나옵니다.
5. 같은 터미널 2에서 계획을 보고 sshuttle을 실행합니다.

```sh
sh scripts/workflow.sh sshuttle dev-ssh --cidr 10.0.1.0/24
sh scripts/workflow.sh sshuttle dev-ssh --cidr 10.0.1.0/24 --execute
```

이제 브라우저에서 `http://10.0.1.20:3000`처럼 실제 사설 주소로 접속합니다. 앱별 SOCKS 프록시 설정은 필요 없습니다. 원격 VM에서 최종 서비스까지의 방화벽은 원격 VM을 기준으로 확인합니다. Bastion endpoint만 허용한 규칙과는 다릅니다.

대역을 추가하려면 `--cidr`를 반복합니다. 전체 인터넷 경로와 공개 IP는 도우미가 거부합니다.

```sh
sh scripts/workflow.sh sshuttle dev-ssh --cidr 10.0.1.0/24 --cidr 10.0.2.0/24
```

기본은 DNS 중계를 켜지 않습니다. 사설 이름 조회가 필요하고 회사 DNS에 미치는 영향을 확인했다면 `--dns`를 추가합니다. 이 옵션은 선택한 웹앱 외의 DNS 요청에도 영향을 줄 수 있습니다. 종료 시 먼저 sshuttle에서 `Ctrl+C`, 그다음 터널을 종료합니다. 종료 후 기존 네트워크·DNS가 정상인지 확인합니다. Bastion 만료 시 두 연결도 다시 열어야 합니다.

도우미의 명령 생성·인자 파싱·OpenSSH 설정 해석은 테스트했습니다. 실제 sudo 방화벽 변경과 OCI 경유 트래픽은 별도 검증이 필요합니다. [sshuttle 사용법](https://sshuttle.readthedocs.io/en/stable/usage.html), [요구사항](https://sshuttle.readthedocs.io/en/stable/requirements.html)

## Tailscale

PC와 서버를 조직의 Tailscale 네트워크에 등록해 장시간 사설 접속에 사용합니다. Bastion을 경유하지 않는 구성은 Bastion TTL과 독립됩니다. 외부 계정·중계 경로 사용이 조직 정책에 맞는지 확인하고 [공식 클라이언트](https://tailscale.com/download)를 설치합니다. 이 도우미는 클라이언트를 설치하거나 조직의 사용 승인을 대신하지 않습니다.

PC와 대상 서버 각각에서 다음을 사용합니다. 미리보기 후 실제 실행하고 조직 로그인 절차를 완료합니다. Linux의 권한 요구는 해당 설치 방식에 맞춰 처리합니다.

```sh
sh scripts/workflow.sh tailscale connect
sh scripts/workflow.sh tailscale connect --execute
sh scripts/workflow.sh tailscale status --execute
```

서버에도 클라이언트를 설치한 단순 구성은 status에 나오는 **Tailscale IP 또는 이름**으로 SSH·웹에 접속합니다. OCI의 `10.x` 주소가 자동으로 라우팅되는 것은 아닙니다. 웹앱이 Tailscale 인터페이스의 연결도 받을 수 있는지와 서버 방화벽을 확인합니다. IP를 얻었다고 사설 IP에만 바인딩된 서비스가 자동으로 연결되지는 않습니다.

여러 사설 서비스에 원래 IP로 접근하려면 OCI 안에 subnet router를 둡니다. 다음 순서로 구성합니다.

1. 대상 VCN에 접근할 수 있는 VM에서 Tailscale 로그인과 OS IP forwarding을 설정합니다. 로컬 방화벽은 필요한 전달만 허용합니다.
2. 현재 광고 중인 대역을 기록한 후, **그 VM에서** 다음을 실행합니다. 이 명령은 기존 광고 목록 전체를 지정한 값으로 바꿉니다. 여러 기존 경로를 유지하려면 모두 `--cidr`로 넣어야 합니다.

```sh
sh scripts/workflow.sh tailscale advertise --cidr 10.0.1.0/24
sh scripts/workflow.sh tailscale advertise --cidr 10.0.1.0/24 --execute
```

3. 관리자 Console에서 경로를 승인하고 사용자·기기·목적지에 대한 접근 정책을 설정합니다. 경로 승인은 접속 권한 부여와 별개입니다.
4. PC의 OS에 맞게 subnet route 수신을 설정합니다. Linux 클라이언트는 필요 시 다음 도우미를 사용합니다.

```sh
sh scripts/workflow.sh tailscale accept-routes --execute
```

5. 허용한 계정으로 사설 서비스가 연결되고, 허용하지 않은 계정에서는 거부되는지 확인합니다. 원래 서비스 로그인도 유지합니다.

복구 시 기록한 광고 경로·클라이언트 경로 수신 상태를 원래 값으로 되돌리고 Console에서 필요한 경로 승인을 해제합니다. 공유 subnet router에서 무조건 `tailscale down`을 실행하면 다른 사용자 연결도 끊길 수 있으므로 도우미는 일괄 종료를 제공하지 않습니다.

명령 생성과 셸 호출 경로는 모의 클라이언트로 검증했습니다. 실제 Tailscale 로그인·라우팅·조직 ACL은 시험하지 않았습니다. [Subnet router 구성](https://tailscale.com/docs/features/subnet-routers)

## Cloudflare Tunnel

사용자가 브라우저 로그인 후 웹 URL로 접속하도록 할 때 선택합니다. 서버의 `cloudflared`가 외부로 연결하고 Cloudflare Access가 사용자 인증을 담당합니다. OCI 서버에는 필요한 외부 통신 경로가 있어야 합니다.

이 도우미는 **로컬 관리 named tunnel**용입니다. Dashboard에서 토큰으로 관리하는 remote tunnel과 설정 방식을 섞지 않습니다. 계정에 도메인을 연결하고 cloudflared를 설치한 뒤 [로컬 터널 생성 절차](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/create-local-tunnel/)에 따라 준비합니다. 이미 같은 터널이 있으면 새로 만들지 않고 기존 UUID와 credentials를 사용합니다.

아래는 **실제 계정 인증과 터널 생성 명령**입니다. 본 도구의 미리보기와 달리 즉시 공식 CLI를 실행합니다. 이 저장소의 테스트에서는 실행하지 않았습니다.

```sh
cloudflared tunnel login
cloudflared tunnel create dev-app
```

생성 결과의 UUID와 credentials JSON 경로를 기록합니다. 터널 생성만으로 웹앱과 연결되거나 Access 인증이 설정되지는 않습니다. `cloudflared`를 실행할 서버에 터널별 credentials JSON을 안전하게 배치하고 다음 예제를 복사합니다.

```sh
cp config/cloudflared.example.yml config/cloudflared.yml
```

파일의 `tunnel`, `credentials-file`, `hostname`, `service`를 실제 값으로 바꿉니다. credentials JSON은 저장소 밖의 제한된 경로에 보관합니다. 이 파일의 ingress는 어느 URL을 어느 서버로 전달할지만 지정하며 **Access 사용자 인증 정책을 만들지 않습니다.** Access 애플리케이션과 허용 사용자 정책을 먼저 설정하고 DNS를 연결해야 합니다.

Cloudflare Zero Trust에서 해당 hostname의 self-hosted Access 애플리케이션과 허용 대상을 구성합니다. [Access 웹 접근 안내](https://developers.cloudflare.com/cloudflare-one/setup/secure-private-apps/private-web-app/)를 따라 먼저 보호 정책을 준비한 뒤, 해당 도메인을 관리할 권한이 있는 환경에서 DNS를 연결합니다. 아래 명령은 **실제 CNAME 레코드를 생성**합니다. `app.example.com`은 본인 도메인으로 바꿉니다.

```sh
cloudflared tunnel route dns dev-app app.example.com
```

```sh
# 로컬 설정 검사. --execute 전에는 명령만 표시합니다.
sh scripts/workflow.sh cloudflare validate --config config/cloudflared.yml
sh scripts/workflow.sh cloudflare validate --config config/cloudflared.yml --execute
# 실제 터널을 포그라운드에서 실행
sh scripts/workflow.sh cloudflare run --config config/cloudflared.yml --tunnel dev-app --execute
```

허용한 사용자가 `https://app.example.com`으로 로그인해 서비스를 이용하는지 확인하고, 로그아웃 상태와 허용하지 않은 사용자에서는 차단되는지도 확인합니다. 예제의 마지막 404 규칙은 알 수 없는 호스트에 대한 전달을 막는 용도이며 사용자 인증을 대신하지 않습니다.

실행 중인 터널은 `Ctrl+C`로 종료합니다. 운영 서비스로 계속 사용할 경우 승인된 서비스 관리자·재시작·모니터링 구성을 별도로 정합니다. 도우미는 자동 service install을 하지 않습니다.

공식 cloudflared로 예제 ingress 문법·호스트 매칭·404 규칙을 실제 검사했습니다. 계정 인증·외부 터널 연결·Access 정책·DNS는 시험하지 않았습니다. [Cloudflare 구성 원리](https://developers.cloudflare.com/cloudflare-one/setup/secure-private-apps/private-web-app/)

## 성공 여부와 막힌 위치 확인

미리보기에 명령이 출력되거나 도구의 상태가 Online이라고 나오는 것과 실제 서비스 이용 성공은 구분합니다.

| 방법 | 실제 성공 판단 | 먼저 확인할 실패 원인 |
|---|---|---|
| 고정 포워딩 | 로컬 포트로 접속해 대상 웹·SSH·DB의 예상 응답 확인 | 로컬 포트 충돌, Bastion allowlist, 대상 포트·서비스 listen 주소 |
| SOCKS5 | 프록시를 지정한 앱에서 사설 URL의 예상 응답 확인 | 앱 프록시 미설정, 우회 목록, 사설 DNS |
| sshuttle | 선택한 사설 대역의 서비스에 앱 프록시 없이 연결, 종료 후 기존 경로 복구 | 터널 선행 실행, VM의 Python, 로컬 방화벽 권한, 대역 충돌 |
| Tailscale | 허용한 계정과 기기에서 서비스 연결, 허용하지 않은 대상은 거부 | 기기 등록, 서비스 바인딩, 경로 승인과 수신, 별도 접근 정책 |
| Cloudflare | 실제 hostname에서 Access 로그인 후 웹 이용, 비허용 사용자는 차단 | 터널 상태, DNS, Access hostname·허용 정책, backend 접근 |

HTTP 401·403은 서버까지 도달했어도 서비스 인증이 남아 있다는 신호일 수 있습니다. timeout·연결 거부·DNS 오류와 같은 원인으로 취급하지 마십시오. 도구가 실행됐다는 사실만으로 정책 준수나 사용자 인증까지 완료됐다고 판단하지 않습니다.

## 회사 VPN과 서비스용 LB

기존 회사 VPN에서 OCI VCN에 이미 도달할 수 있다면 새 프록시 도구 없이 그 경로를 쓰는 것이 단순합니다. 신규 Site-to-Site VPN·FastConnect는 회사측 장비·DRG·라우팅 설계가 필요하므로 일괄 실행 스크립트 대신 [준비 항목](alternatives.md#회사망-연결-요청에-필요한-정보)을 제공합니다.

여러 사용자에게 제공하는 웹/API에는 기존 Terraform 도우미를 사용할 수 있습니다.

```sh
sh scripts/workflow.sh infra load-balancer plan
sh scripts/workflow.sh infra api-gateway plan
```

각각 실제 tfvars와 init을 준비한 후 실행합니다. 계획을 확인한 뒤 적용하는 절차는 [인프라 구성](infrastructure.md)에 있습니다.
