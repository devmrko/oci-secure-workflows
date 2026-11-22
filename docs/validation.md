# 검증 결과

검증 날짜: 2026-11-22. 실행 환경: macOS arm64, Python 3.15.0, OCI CLI 3.88.0, Terraform 1.14.0, OCI provider 9.14.0.

## 수행한 검증

| 범위 | 결과 |
|---|---|
| Python unittest | 35개 통과, skip 없음. 기존 18개에 sshuttle 계획 7개, 추가 클라이언트·셸 연결 7개, 실제 cloudflared 설정 계약 3개 포함 |
| 셸 진입점 | 미리보기 시 외부 프로그램 미실행, --execute 시 전달 인자·오류 코드, 다른 작업 디렉터리와 공백 경로를 실제 하위 프로세스로 검증. 외부 네트워크 클라이언트 실행은 기록용 대체 프로그램 사용 |
| sshuttle 2.0.0 | 실제 패키지의 옵션 파서로 remote·CIDR·DNS 옵션 확인. 실제 방화벽·트래픽 시험과 별개 |
| OpenSSH | 생성된 SSH 옵션을 실제 `ssh -G`로 해석, localhost 포트·host key alias 확인. 네트워크 접속 없음 |
| cloudflared 2026.11.1 | 공식 배포물 SHA256 확인 후 예제 ingress validate, URL별 사설 backend 매칭과 알 수 없는 호스트 404 매칭 검사. 외부 터널 연결 없음 |
| Bastion Terraform validate | 통과 |
| HTTPS LB Terraform validate | 통과 |
| API Gateway Terraform validate | 통과 |
| NAT Terraform validate | 통과 |
| Terraform mock plan test | 8개 통과. Bastion 3, LB 1, API Gateway 2, NAT 2 |
| Terraform fmt | 적용 후 check 통과 |
| Bash 구문 | `bash -n scripts/infra.sh` 통과 |
| CLI 예제 | example 설정의 list, validate, plan 실행 확인 |
| 문서 실행 경로 | README의 도움말·목록·고정 포워딩 계획·sshuttle 계획·Tailscale 미리보기·Cloudflare 미리보기 6개 명령 실행. 로컬 링크·제목 anchor와 전체 문서의 셸 블록 구문 검사 통과 |
| OCI CLI 명령 계약 | 설치된 CLI의 help·JSON 샘플과 고정/동적 세션 입력 대조 |

Terraform mock test는 `mock_provider "oci"`로 실제 OCI API 호출을 대체하고 `command = plan`만 실행합니다. 실제 프로파일·키·인프라를 사용하지 않습니다. Provider 바이너리는 첫 init에서 서명을 확인한 것을 나머지 스택의 로컬 검증에도 재사용했습니다. 환경별 인증·정책·서비스 내부 제약을 모의 테스트가 검증하지는 않습니다.

## 재현

저장소 루트 `oci-secure-workflows/`에서 실행합니다. init은 provider 다운로드를 위해 인터넷에 접속합니다.

```sh
sh scripts/test.sh
terraform fmt -check -recursive terraform
```

기본 실행에서 sshuttle 패키지나 `CLOUDFLARED_BIN`이 없으면 해당 실제 클라이언트 계약 검사는 skip으로 표시합니다. 35개 전체 검사를 재현하려면 테스트 전용 환경에 sshuttle 2.0.0을 설치하고 공식 cloudflared 실행 파일을 준비합니다. 클라이언트 설치 경로에 맞춰 아래 값을 바꿉니다.

```sh
python3 -m venv .venv-test
.venv-test/bin/python -m pip install sshuttle==2.0.0
PYTHON_BIN=.venv-test/bin/python CLOUDFLARED_BIN=/absolute/path/to/cloudflared sh scripts/test.sh --clients
```

이 테스트는 로그인·경로 광고·방화벽 변경·DNS 등록을 수행하지 않습니다. Tailscale의 명령 호출 경로는 대체 실행 파일로 검사했으며 실제 클라이언트의 로그인·경로 적용은 수행하지 않았습니다. 설치된 macOS Tailscale launcher가 preferences 로딩 오류를 반환해 로컬 실제 CLI 검사도 성공으로 기록하지 않았습니다.

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
- Cloudflare 계정·named tunnel 인증·Access의 허용/거부·DNS·외부 URL 연결.

실제 OCI plan/apply, 세션 생성, DNS·서브넷·VNIC 변경과 Public IP 제거는 수행하지 않았습니다.
