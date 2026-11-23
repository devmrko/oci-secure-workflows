# 명령과 설정 참조

모든 예제는 저장소 루트 `oci-secure-workflows/`에서 실행합니다. `--config`는 subcommand **앞에** 둡니다. 설정 JSON은 실행하지 않고 데이터로만 읽습니다. 프로파일 이름만 사용하며 OCI credential 내용을 읽거나 출력하지 않습니다.

| 명령 | 동작 | OCI 변경 |
|---|---|---|
| `python3 scripts/access.py list` | target 목록 | 없음, 오프라인 |
| `python3 scripts/access.py validate` | 설정 형식 검증 | 없음, 오프라인 |
| `python3 scripts/access.py doctor` | 실행 파일·키 존재 확인 | 없음, 오프라인 |
| `python3 scripts/access.py plan TARGET` | 접속 계획·SSH 명령 출력 | 없음, 오프라인 |
| `python3 scripts/access.py connect TARGET` | 같은 미리보기 | 없음, 오프라인 |
| `python3 scripts/access.py connect TARGET --execute` | 상태 확인·새 세션 생성·SSH 실행 | 세션 생성 |
| `python3 scripts/access.py ssh-config TARGET` | SSH 설정 블록 stdout 출력 | 없음, 파일 자동 수정 없음 |
| `python3 scripts/access.py sshuttle-plan TARGET --cidr CIDR` | Linux VM을 경유할 sshuttle 명령 출력 | 없음, 오프라인 |
| `python3 scripts/access.py attach-nsg --region REGION --vnic-id VNIC --nsg-id NSG` | NSG 연결 절차 출력 | 없음, 오프라인 |
| 위 attach-nsg에 `--execute` 추가 | 기존 목록 조회·ETag 조건부 병합 갱신 | VNIC NSG 목록 변경 |

## JSON 필드

| 위치 | 필드 | 의미 |
|---|---|---|
| root | `profile` | 공식 OCI CLI에 전달할 프로파일 이름 |
| root | `regions` | 리전별 Bastion과 키 설정 |
| regions.REGION | `bastion_id` | 관리형 Bastion OCID |
| regions.REGION | `public_key`, `private_key` | 한 쌍의 로컬 키 경로, `~` 확장 지원 |
| regions.REGION | `ttl_seconds` | 기본 10800, 허용 1800~10800, Bastion 최대값 이내 |
| root | `targets` | 이름으로 선택할 접속 대상 |
| targets.NAME | `region` | regions에 있는 키 |
| targets.NAME | `mode` | `forward` 또는 `socks` |
| targets.NAME | `local_port` | loopback 바인딩 포트 |
| forward target | `host`, `port` | RFC1918 IPv4 주소와 TCP 포트 |
| SSH target | `user`, `identity_file` | 대상 VM 로그인 정보, ssh-config 출력용 |

사설 FQDN을 고정 포워딩 대상으로 넣는 기능, IPv6, Managed SSH 세션, 리전/VCN 간 자동 라우팅, 세션 재사용은 구현하지 않았습니다. SOCKS5의 도달 범위는 실제 Bastion·VCN·보안 규칙에 의해 정해집니다.

## 셸 진입점과 추가 접속 도구

`sh scripts/workflow.sh`로 기존 접속 명령과 추가 방법을 사용합니다. `OCI_ACCESS_CONFIG`는 Bastion target 설정 파일, `PYTHON_BIN`은 사용할 Python 실행 파일 경로입니다. network.py의 `--json`은 실행하지 않는 명령 배열 출력이며 `--execute`와 함께 사용할 수 없습니다.

| 셸 명령 | --execute 동작 | 기본 동작 |
|---|---|---|
| `connect TARGET` | Bastion 세션 생성·SSH 터널 실행 | 연결 계획 |
| `sshuttle TARGET --cidr CIDR` | 이미 열린 로컬 SSH 포워딩을 통해 sshuttle 실행 | 필요한 두 터미널 명령 출력 |
| `tailscale status` | 설치된 CLI의 상태 조회 | 명령 출력 |
| `tailscale connect` | `tailscale up`으로 로그인·연결 | 명령 출력 |
| `tailscale advertise --cidr CIDR` | `tailscale set --advertise-routes=...` | 기존 광고 목록 교체 안내·명령 출력 |
| `tailscale accept-routes` | `tailscale set --accept-routes` | 클라이언트 경로 수신 변경 안내 |
| `cloudflare validate --config FILE` | 로컬 named tunnel의 ingress 검증 | 검증 명령 출력 |
| `cloudflare run --config FILE --tunnel NAME` | 로컬 설정으로 named tunnel 실행 | 실행 명령 출력 |
| `cloudflare run --token-file FILE [--protocol http2]` | Dashboard 관리 터널 실행. 토큰 파일은 소유자만 읽기·쓰기 | 파일 내용을 읽거나 외부 도구를 실행하지 않고 명령만 출력 |

`--cidr`는 반복할 수 있고 RFC1918 IPv4 범위만 허용합니다. 기본 경로·공개 IP·IPv6·비정규 CIDR은 거부합니다. `--dns`는 sshuttle에서만 지원하고 기본 꺼짐입니다. Cloudflare의 설정에는 `config/cloudflared.example.yml`을 사용할 수 있으며 실제 `.yml`과 credentials JSON은 Git·ZIP에서 제외합니다. 로그인·경로 승인·DNS·접근 정책 구성은 [사용 절차](../guides/easy-workflows.md)에 있습니다.

개인키 파일의 group/other 권한은 실제 실행 전에 거부합니다. 공개키 형식은 ssh-keygen으로 확인하지만, 암호화된 개인키와 공개키의 쌍 일치까지 사전 검증하지는 않습니다. 연결 실패 시 남은 세션을 정리합니다.

세션 생성·연결은 공식 OCI CLI의 JSON을 사용합니다. 응답의 SSH command에서 해당 session ID의 destination만 추출하며 명령문 전체를 실행하지 않습니다. subprocess는 shell을 사용하지 않습니다.

## Terraform wrapper

```text
bash scripts/infra.sh STACK init|validate|plan|show|apply
STACK = bastion | load-balancer | api-gateway | nat
```

`TF_BIN` 환경 변수로 사용할 Terraform 실행 파일을 지정할 수 있습니다. 일반 사용자는 PATH의 `terraform`을 사용합니다. 설치 프로그램은 포함하지 않습니다. `plan` 전 실제 tfvars를 준비해야 하고, `apply`는 저장된 review.tfplan만 사용합니다. 설정 변경 후 다시 plan을 생성하십시오.

실제 tfvars, state, plan에는 내부 메타데이터가 포함되므로 공유하지 않습니다. `.gitignore`는 이 파일들과 로컬 키를 제외합니다. provider lock과 예제 tfvars는 유지합니다.
