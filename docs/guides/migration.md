# Public IP 제거와 복구 절차

개발·관리와 서비스 접속을 먼저 검증한 뒤 Compute의 Public IP를 제거합니다. 단순 방화벽 차단으로 finding이 해소되는지는 내부 constraint의 판정 조건에 따라 다릅니다. Public IP 제거도 전체 Security Zone recipe 준수를 보장하지 않습니다.

## 전환 전 기록

- 대상 tenancy·compartment·region·instance·모든 VNIC와 private/public IP.
- Public IP의 ephemeral/reserved 구분, 도메인 DNS·TTL, 허용된 외부 소비자.
- SSH·VS Code·DB·웹/API·배포·백업·webhook·예약 작업의 접속 경로.
- 현재 subnet·route table·NSG·Security List·OS 방화벽과 복구 가능한 설정 사본.
- 외부 API가 허용하는 출구 IP, OAuth callback URL·쿠키 도메인·인증서.
- 개별 Security Central finding의 원인·권고·재평가 조건.

개인 연락처·키·wallet·토큰을 배포용 문서나 예제에 넣지 않습니다. 실제 인벤토리도 자원 메타데이터를 포함하므로 저장소와 분리해 관리합니다.

## 실행 순서

1. **대체 관리 접속 확보:** 기존 Public IP를 유지한 상태에서 Bastion으로 새 SSH 연결을 열고 재접속도 시험합니다. 기존 SSH 창만 살아 있는 상태를 성공으로 판단하지 않습니다.
2. **아웃바운드 준비:** NAT 또는 승인된 사설 경로로 외부 API·패키지·백업·OCI 서비스가 동작하는지 확인합니다. 공유 서브넷 전체 영향을 검토합니다.
3. **서비스 진입점 준비:** LB 또는 API Gateway를 만들고 backend NSG를 연결합니다. 상태 검사·인증·업로드·긴 응답·WebSocket/SSE·CORS·callback을 시험합니다.
4. **DNS 전환:** 기존 도메인을 새 진입점으로 변경하고 DNS 캐시·TTL에 따른 전환 시간을 둡니다. old/new 경로의 요청과 오류를 확인합니다.
5. **Public IP 제거:** 영향받는 모든 VNIC와 secondary private IP의 연결을 검토하고 Console의 해당 IP에서 Public IP 할당을 해제합니다. 이 도구는 해제를 자동 실행하지 않습니다.
6. **새 연결 검증:** 외부에서 VM 직접 접속이 차단됐는지, Bastion과 서비스 URL로는 접속되는지 확인합니다. 예약 작업은 실제 한 주기까지 관찰합니다.
7. **finding 재평가:** Security Central의 실제 재평가 결과와 나머지 원인을 확인합니다. IP 제거 직후 완료로 기록하지 않습니다.

IPv6가 구성되어 있다면 해당 주소·라우트·보안 규칙도 별도 검토합니다. 본 접속 CLI와 예제는 IPv4 기준입니다. NSG 규칙뿐 아니라 서비스 자체의 익명 접근·인증·관리 API 공개 여부도 확인합니다.

## 실패 시 복구

| 상황 | 우선 복구 |
|---|---|
| 새 서비스 진입점의 문제 | 애플리케이션 설정·backend health·NSG·인증서를 수정합니다. DNS 원복은 기존 경로가 아직 동작하고 정책상 허용되는 단계에서만 유효합니다 |
| NAT 전환 후 회사망·OCI 서비스 장애 | 기록한 route table과 경로를 대조하고 승인된 절차로 기존 subnet 연결을 복구합니다 |
| Bastion 연결 실패 | client CIDR·키·세션·target 방화벽을 수정합니다. 사전에 검증한 별도 승인 관리 경로를 사용합니다 |
| Public IP 제거 후 장애 | Bastion으로 진단하고 LB/API/사설 경로를 복구합니다. Public IP 재할당이 허용된다고 가정하지 않습니다 |

ephemeral Public IP는 제거 후 같은 주소로 되돌릴 수 있다고 보장할 수 없습니다. 정책 강제 적용 후에는 신규 Public IP 할당 자체가 차단될 수 있으므로 **Public IP 재할당을 유일한 복구 수단으로 삼지 않습니다.**

정리 시 Terraform 자원에 의존하는 DNS·NSG membership·subnet 라우트 연결부터 확인합니다. wrapper는 일괄 destroy를 제공하지 않습니다. 필요하면 검토된 `terraform plan -destroy`를 별도로 만들고 승인된 변경 절차로 적용합니다.

## 적용 일정 확인

정책 적용 시점과 예외는 조직·테넌시·자원에 따라 다릅니다. 현재 정책 안내와 개별 finding에서 기한·조치·예외 절차를 확인하고 변경 일정을 정합니다. 한 종류의 정책이 변경되었다고 다른 정책도 함께 변경되었다고 해석하지 않습니다.

출처: [OCI Public IP 개념](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingpublicIPs.htm), [NAT Gateway](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/NATgateway.htm).
