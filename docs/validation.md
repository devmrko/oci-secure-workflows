# 검증 결과

검증 날짜: 2026-11-22. 실행 환경: macOS arm64, Python 3.15.0, OCI CLI 3.88.0, Terraform 1.14.0, OCI provider 9.14.0.

## 수행한 검증

| 범위 | 결과 |
|---|---|
| Python unittest | 18개 통과. 미리보기 무호출, CLI별 TTL 옵션, loopback, 서버 응답의 명령문 미실행, 세션 상태·실패·타임아웃, NSG 병합·ETag, 저장 계획 적용·실패 시 오래된 계획 격리, 패키지 민감 파일 제외 |
| Bastion Terraform validate | 통과 |
| HTTPS LB Terraform validate | 통과 |
| API Gateway Terraform validate | 통과 |
| NAT Terraform validate | 통과 |
| Terraform mock plan test | 8개 통과. Bastion 3, LB 1, API Gateway 2, NAT 2 |
| Terraform fmt | 적용 후 check 통과 |
| Bash 구문 | `bash -n scripts/infra.sh` 통과 |
| CLI 예제 | example 설정의 list, validate, plan 실행 확인 |
| OCI CLI 명령 계약 | 설치된 CLI의 help·JSON 샘플과 고정/동적 세션 입력 대조 |

Terraform mock test는 `mock_provider "oci"`로 실제 OCI API 호출을 대체하고 `command = plan`만 실행합니다. 실제 프로파일·키·인프라를 사용하지 않습니다. Provider 바이너리는 첫 init에서 서명을 확인한 것을 나머지 스택의 로컬 검증에도 재사용했습니다. 환경별 인증·정책·서비스 내부 제약을 모의 테스트가 검증하지는 않습니다.

## 재현

저장소 루트 `oci-secure-workflows/`에서 실행합니다. init은 provider 다운로드를 위해 인터넷에 접속합니다.

```sh
python3 -m unittest discover -s tests -v
bash -n scripts/infra.sh
terraform fmt -check -recursive terraform
```

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

실제 OCI plan/apply, 세션 생성, DNS·서브넷·VNIC 변경과 Public IP 제거는 수행하지 않았습니다.
