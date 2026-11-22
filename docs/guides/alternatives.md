# 접속 방식 비교와 확장 기준

혼합 용도의 기본안은 개발·관리용 Bastion과 서비스용 LB입니다. API 정책이 필요하면 API Gateway를 선택하고, 서버 외부 통신은 NAT로 준비합니다.

예를 들어 본인이 SSH로 개발하고 동료가 완성된 데모 웹을 보는 상황이면, 본인은 Bastion 고정 포워딩으로 SSH에 접속하고 동료에게는 LB의 HTTPS URL을 알려 줍니다. 본인이 별도 사설 관리 화면 여러 개도 열어야 할 때만 SOCKS5를 추가하면 됩니다. 처음부터 모든 방식을 함께 구축할 필요는 없습니다. 용어와 흐름은 [접속 방식의 원리](../explanation/access-model.md)에 설명했습니다.

| 방법 | 잘 맞는 상황 | 운영 제약 | 제공 상태 |
|---|---|---|---|
| Bastion 고정 포워딩 | SSH, DB, 단일 개발 포트, RDP | TCP·세션 TTL, 대상마다 터널 | 실행 CLI·생성 Terraform |
| Bastion SOCKS5 | 여러 사설 웹·서버·API 탐색 | 앱 프록시 지원·DNS·세션 TTL | 실행 CLI·클라이언트 예제 |
| Public HTTPS LB | 웹사이트, 웹앱, 일반 HTTP API | TLS·health·앱 인증·비용 | Terraform |
| Public API Gateway | JWT 검증·rate limit이 필요한 HTTP API | 경로·메서드·timeout·payload 설계 | JWT 필수 Terraform |
| Private LB/API Gateway | 내부 사용자 서비스 | 먼저 사설망 접속 경로 필요 | 선택 가이드만 |
| Network Load Balancer | HTTP 이외 TCP/UDP 서비스 | 앱 인증·원본 IP·반환 라우팅 설계 | 선택 가이드만 |
| Site-to-Site VPN / FastConnect | 팀 단위 장시간 개발·내부 서비스 | 회사망·DRG·CIDR·DNS 운영 | 구성 요구사항만 |
| 자체 점프 VM | 특수 프록시·전용 관리 도구 | 패치·고가용성·Public Compute 제약 | 기본안에서 제외 |
| 외부 터널·오버레이 VPN | 승인된 외부 중계가 필요한 경우 | 보안 경계·외부 계정·운영 주체 검토 | 자동 설치·배포 없음 |

## Bastion이 불편해지는 시점

최대 3시간 세션 안에서 사람이 필요할 때 접속하는 작업에는 Bastion이 간단합니다. 하루 종일 IDE를 연결하거나 상시 배포·백업을 수행한다면 작업 실행기를 VCN 내부에 두거나 기존 회사 사설망 경로를 이용하는 편을 검토합니다. Bastion 자동 세션 생성 반복을 가용성 보장 수단으로 삼지 않습니다.

## 회사망 연결 요청에 필요한 정보

기존 회사 VPN에서 대상 VCN 사설 주소로 이미 라우팅되는지 먼저 네트워크 담당자에게 확인합니다. 새 Site-to-Site VPN이면 회사측 CPE와 OCI DRG 사이에 IPSec 연결이 필요합니다. 개인 노트북 VPN 클라이언트 하나만 설치하는 구성과 다릅니다.

요청에는 VCN·서브넷 CIDR, 회사망 CIDR과 중복 여부, 필요한 리전·VCN, 포트·대상·사용자 범위, 사설 DNS 조회·반환 경로, 방화벽, 이중 터널 운영·장애 대응 주체를 포함합니다. 회사망 구조가 확인되지 않아 이 패키지에는 VPN 자동 생성 스크립트를 넣지 않았습니다.

## NLB 선택

NLB는 TCP/UDP 같은 네트워크 트래픽을 전달할 때 검토합니다. SSH나 DB를 Public NLB 뒤에 두면 Compute의 직접 Public IP와 별개로 관리 서비스가 인터넷에 노출됩니다. 이번 관리 접속의 기본 경로는 Bastion으로 유지합니다. 웹서비스는 TLS·HTTP 처리가 쉬운 일반 LB부터 검토합니다.

출처: [Site-to-Site VPN](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/overviewIPsec.htm), [NLB 개념](https://docs.oracle.com/en-us/iaas/Content/NetworkLoadBalancer/introduction.htm), [Bastion](https://docs.oracle.com/en-us/iaas/Content/Bastion/Concepts/bastionoverview.htm).
