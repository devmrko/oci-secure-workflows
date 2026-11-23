# 참고 구현과 공식 근거

확인 날짜: 2026-11-22. 외부 코드를 복제하지 않고 아래 패턴과 서비스 계약을 참고했습니다. 저장소의 사용법은 upstream 변경에 따라 달라질 수 있습니다.

## 채택한 구현 패턴

| 출처 | 채택한 부분 | 이 도구에서 달리한 부분 |
|---|---|---|
| [TheKoguryo OCI Bastion Proxy](https://github.com/TheKoguryo/oci-bastion-proxy/blob/main/README.ko.md) | 로컬 SOCKS5 → 관리형 Bastion → 사설 서비스, 리전별 설정, 기존 도구의 프록시 활용 | Bash 내 설정 대신 JSON 사용, 고정 포워딩 포함, 명시적 실행, 세션 재사용 없음 |
| [Oracle provider Bastion 예제](https://github.com/oracle/terraform-provider-oci/tree/master/examples/bastion) | 인프라 수명과 접속 세션 수명 분리 | 세션 키를 Terraform state에 넣지 않고 로컬 CLI로 처리 |
| [Oracle provider Load Balancer 예제](https://github.com/oracle/terraform-provider-oci/tree/master/examples/load_balancer) | LB·backend set·listener 분리 | 기존 인증서 OCID 사용, HTTPS만 제공, backend NSG 별도 연결 |
| [Oracle provider API Gateway 예제](https://github.com/oracle/terraform-provider-oci/tree/master/examples/api_gateway) | Gateway·deployment·route·policy 구분 | JWT 필수, 최소 health 경로만 제공, 익명 catch-all 제외 |
| [Oracle baseline landing zone](https://github.com/oracle-quickstart/oci-enterprise-scale-baseline-landing-zone/blob/main/IMPLEMENTATION.md) | 관리 접근을 서비스 공개와 분리 | 전체 landing zone 도입 대신 기존 VCN에 독립 스택 제공 |

위 표는 설계 참고 관계입니다. upstream 코드를 다운로드·vendoring하거나 라이선스가 불명확한 코드를 복사하지 않았습니다. 재배포 라이선스는 이 작업에서 새로 부여하지 않았습니다.

## 서비스와 명령 계약

- [Bastion 개념과 세션 종류](https://docs.oracle.com/en-us/iaas/Content/Bastion/Concepts/bastionoverview.htm): 고정/동적 포워딩, Managed SSH와 agent 요구사항 차이.
- [Bastion 생성](https://docs.oracle.com/en-us/iaas/Content/Bastion/Tasks/create-bastion.htm): CIDR·FQDN/SOCKS5·최대 TTL.
- [Bastion 접속 규칙](https://docs.oracle.com/en-us/iaas/Content/Bastion/Tasks/connectingtosessions.htm): 사설 엔드포인트에서 대상 포트 허용.
- [고정 포워딩 생성](https://docs.oracle.com/en-us/iaas/Content/Bastion/Tasks/create-session-port-forwarding.htm): 대상 IP·포트와 키.
- [OCI CLI 고정 포워딩](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/bastion/session/create-port-forwarding.html), [동적 포워딩](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/bastion/session/create-session-create-dynamic-port-forwarding-session-target-resource-details.html): 두 명령의 TTL·키 입력 옵션을 구분. 로컬 OCI CLI 3.88.0 `--help`와 JSON 입력 샘플로 대조.
- [Bastion 요금](https://www.oracle.com/security/cloud-security/bastion/): 서비스 자체 무료. 다른 서비스·트래픽 비용과 별개.
- [API Gateway 개념](https://docs.oracle.com/en-us/iaas/Content/APIGateway/Concepts/apigatewayconcepts.htm), [기능](https://docs.oracle.com/en-us/iaas/Content/APIGateway/Concepts/apigatewayoverview.htm): 사설 HTTP backend와 인증·요청 제한.
- [LB 생성](https://docs.oracle.com/en-us/iaas/Content/Balance/Tasks/managingloadbalancer_topic-Creating_Load_Balancers.htm), [연결 timeout](https://docs.oracle.com/en-us/iaas/Content/Balance/Reference/connectionreuse.htm): 공개 frontend와 backend, 긴 연결의 idle 설정.
- [Cipher suites](https://docs.oracle.com/en-us/iaas/Content/Balance/Tasks/managingciphersuites_topic-Predefined_Cipher_Suites.htm): 이름에 modern이 있어도 내부 정책 준수를 자동으로 의미하지 않음. 이 예제는 명시적 cipher 목록 사용.
- [NAT](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/NATgateway.htm), [Site-to-Site VPN](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/overviewIPsec.htm), [NLB](https://docs.oracle.com/en-us/iaas/Content/NetworkLoadBalancer/introduction.htm): outbound·사설망·네트워크 서비스 전달 역할 구분.
- [Kubeconfig proxy-url](https://kubernetes.io/docs/reference/config-api/kubeconfig.v1/): SOCKS5와 SPDY 스트리밍 제약.
- [Firefox 연결 설정](https://support.mozilla.org/en-US/kb/connection-settings-firefox): 브라우저 수동 프록시와 프록시 우회 목록. 메뉴 위치는 버전별로 달라질 수 있음.
- [curl 공식 매뉴얼](https://curl.se/docs/manpage.html): SOCKS5 프록시와 `socks5h`의 이름 조회 방식.

## 추가 접속 클라이언트

- [sshuttle 2.0.0 사용법](https://sshuttle.readthedocs.io/en/stable/usage.html), [옵션](https://sshuttle.readthedocs.io/en/stable/manpage.html), [요구사항](https://sshuttle.readthedocs.io/en/stable/requirements.html): SSH 목적지·CIDR·DNS·원격 Python과 로컬 방화벽 요구. 실제 패키지의 parser로 생성 명령을 확인했습니다.
- [Tailscale subnet router](https://tailscale.com/docs/features/subnet-routers): IP forwarding, 경로 광고와 승인, access rule·클라이언트 route 수신 구분. 실제 계정 연결은 수행하지 않았습니다.
- [Tailscale 연결 종류](https://tailscale.com/docs/reference/connection-types), [포트 안내](https://tailscale.com/docs/reference/faq/firewall-ports): VM Public IP 없이 필요한 외부 연결을 갖춘 NAT 환경에서 직접 또는 중계 연결 사용. OCI NAT와 상대 기기의 조합은 실측하지 않았으므로 직접 연결·성능을 보장하지 않습니다.
- [Cloudflare 사용자 인증 웹 접근](https://developers.cloudflare.com/cloudflare-one/setup/secure-private-apps/private-web-app/), [로컬 named tunnel 설정](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/configuration-file/): Tunnel과 Access의 역할 구분, ingress와 마지막 catch-all 규칙. 공식 cloudflared 2026.11.1로 로컬 설정과 URL 매칭을 검사했습니다.

## 관리형 서비스 접속

- [ADB 네트워크 선택](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/network-access-options.html), [Private Endpoint](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/private-endpoints-autonomous.html): 공개 ACL·사설 endpoint·공개 접속 병행 여부, NSG·DNS.
- [ADB 연결과 TLS/mTLS](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/connect-introduction.html): mTLS 1522, TLS 1521/1522와 wallet 요구 구분.
- [Bastion DB 연결](https://docs.oracle.com/en-us/iaas/Content/Bastion/Tasks/connect-port-forwarding.htm), [ADB 터널 구성 예](https://docs.oracle.com/en/solutions/migrate-tomcat-workloads/migrate-application-database.html): TCP 중계와 클라이언트 설정. 후자의 원래 DB 이름 유지 방식을 참고하되 공개 점프 VM 대신 관리형 Bastion 사용.
- [Database Actions](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/connect-database-actions.html), [APEX Service 제한](https://docs.oracle.com/en-us/iaas/autonomous-database-serverless/doc/apex-workload-limitations.html): HTTPS 경로와 별도 APEX Service의 SQL*Net 제한.
- [Service Gateway](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/servicegateway.htm): 같은 리전의 지원 OSN 서비스로 가는 사설 경로. 서비스 endpoint 자체의 사설 IP와 구분.

## Terraform resource 계약

[Bastion](https://docs.oracle.com/en-us/iaas/tools/terraform-provider-oci/latest/docs/r/bastion_bastion.html) · [LB listener](https://docs.oracle.com/en-us/iaas/tools/terraform-provider-oci/latest/docs/r/load_balancer_listener.html) · [LB backend set](https://docs.oracle.com/en-us/iaas/tools/terraform-provider-oci/latest/docs/r/load_balancer_backend_set.html) · [NSG rule](https://docs.oracle.com/en-us/iaas/tools/terraform-provider-oci/latest/docs/r/core_network_security_group_security_rule.html) · [API Gateway](https://docs.oracle.com/en-us/iaas/tools/terraform-provider-oci/latest/docs/r/apigateway_gateway.html) · [API deployment](https://docs.oracle.com/en-us/iaas/tools/terraform-provider-oci/latest/docs/r/apigateway_deployment.html) · [NAT Gateway](https://docs.oracle.com/en-us/iaas/tools/terraform-provider-oci/latest/docs/r/core_nat_gateway.html).

`latest` 문서는 향후 바뀔 수 있으므로 실행 파일은 provider 9.14.0으로 고정하고 해당 버전의 스키마로 validate했습니다. 내부 Assurance constraint의 정확한 판정식은 공개 provider 문서로 확정할 수 없습니다.
