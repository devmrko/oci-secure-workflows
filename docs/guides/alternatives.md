# 접속 방식 비교와 확장 기준

혼합 용도의 기본안은 개발·관리용 Bastion과 서비스용 LB입니다. API 정책이 필요하면 API Gateway를 선택하고, 서버 외부 통신은 NAT로 준비합니다.

예를 들어 본인이 SSH로 개발하고 동료가 완성된 데모 웹을 보는 상황이면, 본인은 Bastion 고정 포워딩으로 SSH에 접속하고 동료에게는 LB의 HTTPS URL을 알려 줍니다. 본인이 별도 사설 관리 화면 여러 개도 열어야 할 때만 SOCKS5를 추가하면 됩니다. 처음부터 모든 방식을 함께 구축할 필요는 없습니다. 용어와 흐름은 [접속 방식의 원리](../explanation/access-model.md)에 설명했습니다.

| 방법 | 잘 맞는 상황 | 운영 제약 | 제공 상태 |
|---|---|---|---|
| Bastion 고정 포워딩 | SSH, DB, 단일 개발 포트, RDP | TCP·세션 TTL, 대상마다 터널 | 실행 CLI·생성 Terraform |
| Bastion SOCKS5 | 여러 사설 웹·서버·API 탐색 | 앱 프록시 지원·DNS·세션 TTL | 실행 CLI·클라이언트 예제 |
| sshuttle | 프록시 설정 없이 여러 사설 TCP 서비스 접근 | 로컬 방화벽 권한·원격 Linux/Python·Bastion 경유 시 TTL | 셸 실행·명령 파서 검증 |
| Tailscale | 장시간 개발, 여러 도구의 사설 접속 | 조직 계정·route 승인·접근 정책·외부 통신 | 셸 실행·실제 연결 미검증 |
| Cloudflare Tunnel와 Access | 허용된 사용자가 웹 URL로 앱 이용 | 외부 계정·도메인·Access 정책·터널 운영 | 셸 실행·예제 ingress 검증 |
| Public HTTPS LB | 웹사이트, 웹앱, 일반 HTTP API | TLS·health·앱 인증·비용 | Terraform |
| Public API Gateway | JWT 검증·rate limit이 필요한 HTTP API | 경로·메서드·timeout·payload 설계 | JWT 필수 Terraform |
| Private LB/API Gateway | 내부 사용자 서비스 | 먼저 사설망 접속 경로 필요 | 선택 가이드만 |
| Network Load Balancer | HTTP 이외 TCP/UDP 서비스 | 앱 인증·원본 IP·반환 라우팅 설계 | 선택 가이드만 |
| Site-to-Site VPN / FastConnect | 팀 단위 장시간 개발·내부 서비스 | 회사망·DRG·CIDR·DNS 운영 | 구성 요구사항만 |
| 자체 점프 VM | 특수 프록시·전용 관리 도구 | 패치·고가용성·Public Compute 제약 | 기본안에서 제외 |
| 외부 터널·오버레이 VPN | 승인된 외부 중계가 필요한 경우 | 보안 경계·외부 계정·운영 주체 검토 | 자동 설치·배포 없음 |

명령은 [방법별 쉬운 실행](easy-workflows.md)에 정리했습니다. 위의 도우미는 기존 공식 클라이언트를 실행하며, 외부 계정과 정책 전체를 자동 구성하지 않습니다. `--execute`를 붙이기 전에는 명령만 출력합니다.

## 프록시 설정을 피하고 싶을 때

웹 화면이 한두 개면 고정 포워딩이 가장 단순합니다. 서버별 로컬 주소로 접속하고 브라우저 설정은 그대로 둡니다. 여러 사설 서비스의 원래 주소를 쓰고 싶다면 sshuttle이나 승인된 VPN·Tailscale을 검토합니다.

sshuttle은 로컬 앱의 연결을 SSH로 중계하는 방식입니다. Bastion 뒤 VM에 Python을 실행하므로 관리형 Bastion 세션에 바로 연결해 쓰는 방식과는 다릅니다. Bastion → VM뿐 아니라 VM → 최종 서비스의 접근도 허용되어야 합니다. Tailscale subnet router는 서버에 없는 별도 클라이언트 없이도 사설 대역으로 접근하게 할 수 있지만, 경로 광고·승인·접근 권한을 각각 맞춰야 합니다.

웹서비스 이용자에게 도구 설치를 요구하고 싶지 않으면 LB 또는 Cloudflare Tunnel와 Access를 선택할 수 있습니다. Cloudflare 구성은 외부 통신·조직 정책·인증 운영을 함께 검토해야 합니다. 서비스별로 누가 접속하고 무엇을 신뢰하는지 정한 뒤 선택합니다.

## Bastion이 불편해지는 시점

최대 3시간 세션 안에서 사람이 필요할 때 접속하는 작업에는 Bastion이 간단합니다. 하루 종일 IDE를 연결하거나 상시 배포·백업을 수행한다면 작업 실행기를 VCN 내부에 두거나 기존 회사 사설망 경로를 이용하는 편을 검토합니다. Bastion 자동 세션 생성 반복을 가용성 보장 수단으로 삼지 않습니다.

## 회사망 연결 요청에 필요한 정보

기존 회사 VPN에서 대상 VCN 사설 주소로 이미 라우팅되는지 먼저 네트워크 담당자에게 확인합니다. 새 Site-to-Site VPN이면 회사측 CPE와 OCI DRG 사이에 IPSec 연결이 필요합니다. 개인 노트북 VPN 클라이언트 하나만 설치하는 구성과 다릅니다.

요청에는 VCN·서브넷 CIDR, 회사망 CIDR과 중복 여부, 필요한 리전·VCN, 포트·대상·사용자 범위, 사설 DNS 조회·반환 경로, 방화벽, 이중 터널 운영·장애 대응 주체를 포함합니다. 회사망 구조가 확인되지 않아 이 패키지에는 VPN 자동 생성 스크립트를 넣지 않았습니다.

## NLB 선택

NLB는 TCP/UDP 같은 네트워크 트래픽을 전달할 때 검토합니다. SSH나 DB를 Public NLB 뒤에 두면 Compute의 직접 Public IP와 별개로 관리 서비스가 인터넷에 노출됩니다. 이번 관리 접속의 기본 경로는 Bastion으로 유지합니다. 웹서비스는 TLS·HTTP 처리가 쉬운 일반 LB부터 검토합니다.

출처: [Site-to-Site VPN](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/overviewIPsec.htm), [NLB 개념](https://docs.oracle.com/en-us/iaas/Content/NetworkLoadBalancer/introduction.htm), [Bastion](https://docs.oracle.com/en-us/iaas/Content/Bastion/Concepts/bastionoverview.htm).

추가 출처: [sshuttle 사용법](https://sshuttle.readthedocs.io/en/stable/usage.html), [Tailscale subnet router](https://tailscale.com/docs/features/subnet-routers), [Cloudflare 사용자 인증 웹 접근](https://developers.cloudflare.com/cloudflare-one/setup/secure-private-apps/private-web-app/).
