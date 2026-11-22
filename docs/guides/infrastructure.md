# Bastion과 서비스 진입점 구성

기존 VCN·서브넷에 필요한 OCI 서비스를 추가합니다. Terraform 스택은 각각 별도 state를 사용하며 기존 Compute·서브넷·Public IP를 관리하지 않습니다. 같은 자원을 중복 생성하지 않도록 기존 Bastion·NAT·LB를 먼저 확인합니다.

## 공통 실행

Terraform 1.7 이상, OCI 프로파일 인증, 각 서비스와 NSG·라우트 테이블에 대한 생성 권한이 필요합니다. 실제 생성 시 요금과 서비스 할당량이 적용됩니다. provider는 9.14.0으로 고정하고 lock 파일을 포함합니다.

아래 `bastion`을 `load-balancer`, `api-gateway`, `nat`로 바꾸어 각 스택에 사용합니다. 예제의 OCID·IP·도메인·인증 설정을 먼저 바꿉니다.

```sh
cp terraform/bastion/terraform.example.tfvars terraform/bastion/terraform.tfvars
bash scripts/infra.sh bastion init
bash scripts/infra.sh bastion validate
bash scripts/infra.sh bastion plan
bash scripts/infra.sh bastion show
```

`plan`은 OCI를 조회하고 `review.tfplan`을 만듭니다. 대상 tenancy·region·compartment, 생성/변경/삭제 자원, CIDR·포트·TLS를 검토합니다. 의도한 계획만 적용합니다.

```sh
bash scripts/infra.sh bastion apply
```

스택 이름을 입력하면 **저장된 계획을 실제 적용**합니다. 계획 이후 설정을 바꿨다면 다시 plan을 실행해야 합니다. 적용 후 완료된 계획은 `.applied`로 이동합니다. 오래된 계획을 재사용하지 마십시오. 동시 작업 시 로컬 state 대신 조직의 승인된 원격 backend와 잠금 체계를 사용합니다.

## Bastion

본인이 SSH로 코드를 수정하거나 사설 개발 화면을 잠깐 확인할 때 사용할 입구입니다. 대상 VM에는 Public IP를 두지 않고, 허용된 개발자 PC가 Bastion 세션을 통해 들어갑니다. 이 Bastion 위에서 고정 포워딩 또는 SOCKS5를 선택하는 것이며 두 서비스를 각각 설치하는 구조가 아닙니다. [두 접속 방식의 차이](../explanation/access-model.md)를 먼저 확인할 수 있습니다.

`terraform/bastion`은 FQDN/SOCKS5 활성 Bastion과 backend NSG를 만듭니다. `target_subnet_id`는 대상 VCN에 속해야 하고 `vcn_id`는 NSG를 생성하는 같은 VCN이어야 합니다. 서브넷·라우팅·Security List는 기존 구성을 사용합니다.

- `client_cidrs`: 개발자 또는 회사 VPN의 공인 출구 CIDR. `0.0.0.0/0`는 거부합니다.
- `target_ports`: 대상 Compute에 허용할 TCP 포트. VM별로 더 좁은 규칙이 필요하면 스택/NSG를 나눕니다.
- `ttl_seconds`: 1800~10800초.

생성 후 `bastion_id` 출력을 `config/access.json`에 넣고, `backend_nsg_id`를 대상 VM의 VNIC에 연결합니다. Bastion 서브넷 egress와 대상 OS 방화벽은 별도 확인합니다. 대상 VNIC에 NSG를 연결하지 않으면 이 스택의 backend 규칙이 적용되지 않습니다.

## HTTPS Load Balancer

여러 사용자가 `https://app.example.com` 같은 URL로 웹앱을 이용하게 하려면 공개 HTTPS 입구가 필요합니다. LB가 그 입구를 맡고 내부의 VM으로 요청을 전달합니다. 사용자는 Bastion이나 프록시를 설정하지 않습니다. 이 구성에서는 VM 한 대만 있어도 Public IP를 VM에서 분리하기 위해 LB를 사용할 수 있습니다. 서버가 여러 대라면 요청 분산에도 활용합니다.

`terraform/load-balancer`는 Public Flexible LB, 443 TLS 리스너, HTTP 백엔드·상태 검사와 frontend/backend NSG를 생성합니다. 기존 Certificate Service의 인증서 OCID를 사용하므로 TLS 개인키를 tfvars에 넣지 않습니다. 인증서 읽기·사용 권한과 올바른 인증서 도메인이 필요합니다.

`subnet_ids`에는 Internet Gateway 경로가 있는 public subnet을 넣습니다. regional subnet이면 하나를 사용하고, AD-specific subnet의 요건은 해당 리전에 맞춰 확인합니다.

- `client_cidrs`: 허용할 사용자 네트워크. 예제는 문서용 IP/32이므로 실제 접속은 차단됩니다. 일반 공개가 필요한 서비스에서만 의도적으로 `0.0.0.0/0`를 지정합니다.
- `backend_ips`, `backend_port`: 사설 애플리케이션 주소. 이 예제는 HTTP 백엔드입니다.
- `health_path`: 인증 없이 LB가 200 응답을 받을 수 있는 최소 상태 경로. 민감 정보를 반환하지 않도록 합니다.
- `idle_timeout_seconds`: 기본 300초. WebSocket·SSE는 heartbeat, 실제 처리 시간과 함께 시험합니다.

TLS 1.2와 명시적 ECDHE/AES-GCM cipher 집합을 예제로 사용합니다. 내부 cipher 정책에 대한 준수 인증을 의미하지 않습니다. 백엔드 구간에도 TLS가 필요하면 backend set SSL과 인증서 신뢰를 별도 구성해야 합니다.

생성된 backend NSG를 VM VNIC에 연결하고 상태 검사 통과를 확인합니다. DNS를 전환하기 전에 기존 도메인과 TLS로 검사할 수 있습니다.

```sh
curl --resolve app.example.com:443:LB_PUBLIC_IP https://app.example.com/health
```

LB는 사용자 로그인을 대신하지 않습니다. 기존 애플리케이션 인증을 유지하고, forwarded header를 신뢰할 프록시 범위를 제한합니다. 이 스택은 도메인 DNS·WAF·로그 저장소를 생성하지 않습니다.

## API Gateway

외부 프로그램이나 다른 서비스가 HTTP API를 호출할 때, 입구에서 요청을 검사하는 구성이 필요하면 사용합니다. 예를 들어 유효한 토큰이 있는 요청만 사설 API로 전달하거나 호출량을 제한할 수 있습니다. JWT는 서명을 확인할 수 있는 토큰 형식이고, JWKS는 서명 검증에 사용할 공개키 목록입니다. 실제 토큰을 발급하는 인증 공급자는 별도로 필요합니다. LB 뒤의 애플리케이션이 이미 필요한 인증과 제한을 제공한다면 Gateway를 추가할 이유부터 확인합니다.

`terraform/api-gateway`는 Public Gateway와 **JWT 필수** deployment를 생성합니다. 예제는 `/api/health`의 GET 요청을 사설 백엔드 `/health`로 전달하고, client IP별 초당 10건 제한을 설정합니다. 임의 경로를 전부 공개하는 catch-all 예제는 제공하지 않습니다.

`jwt_issuer`, `jwt_audiences`, `jwks_uri`를 실제 인증 공급자 값으로 바꿉니다. JWKS는 인증서 검증이 가능한 HTTPS URL이어야 하고 Gateway에서 접근 가능해야 합니다. 외부 JWKS 조회를 위해 frontend NSG에 TCP 443 egress가 열립니다. 더 제한적인 환경은 승인된 키 배포 방식과 목적지 규칙으로 바꿉니다.

생성된 backend NSG를 대상 VNIC에 연결합니다. Gateway subnet의 public 연결·라우팅과 OS 방화벽도 필요합니다. client CIDR에서 호출해 토큰 없이는 거부되고, 올바른 issuer/audience/signature의 토큰만 통과하는지 확인합니다. 실제 토큰은 명령 이력이나 문서에 기록하지 마십시오.

서비스별 API는 `routes`에 메서드·경로·backend URL을 명시적으로 추가합니다. 요청 크기·timeout·스트리밍·CORS·권한 검증은 실제 요구에 맞게 확인해야 합니다. JWT 인증 성공만으로 개별 업무 자원의 접근 권한이 모두 해결되지는 않습니다.

## NAT Gateway

이 설정은 VM이 외부 API를 호출하거나 패키지를 내려받을 때 필요합니다. 사용자 PC가 VM에 들어오는 경로와 반대 방향입니다. `사설 VM → NAT → 인터넷`으로 나가고 그 요청의 응답을 돌려받습니다. NAT를 만들었다고 브라우저나 SSH에서 VM으로 들어갈 수 있는 것은 아닙니다. 또한 개발 PC에서 사용하는 SOCKS5와 서버의 외부 통신용 NAT는 서로 다른 역할입니다.

`terraform/nat`는 NAT Gateway와 **새 라우트 테이블만** 생성합니다. 기존 서브넷의 연결은 바꾸지 않습니다. 이미 VCN에 NAT가 있으면 재사용을 우선 검토합니다.

1. 현재 대상 서브넷의 route table ID와 모든 라우트 규칙을 기록합니다.
2. Service Gateway, DRG, 피어링 등 필요한 경로를 `additional_routes`에 넣습니다. 기본 경로는 NAT용 `0.0.0.0/0` 하나만 둡니다.
3. plan/apply 후 새 route table의 내용을 Console에서 대조합니다.
4. Compute가 있는 서브넷에 새 테이블을 연결하는 변경을 별도 수행합니다. **같은 서브넷의 모든 자원에 영향**이 있습니다.
5. 외부 HTTPS·패키지 저장소·OCI 서비스·회사망·피어링 연결을 시험합니다.

Public LB/API Gateway가 있는 서브넷의 Internet Gateway 경로를 NAT로 바꾸지 마십시오. Compute와 공개 진입점이 같은 서브넷이라면 서브넷 분리 또는 더 세밀한 라우팅 설계부터 필요합니다. NAT는 인터넷에서 들어오는 신규 연결을 제공하지 않습니다. 외부 시스템이 출구 IP를 허용 목록으로 사용한다면 새 `nat_public_ip`도 등록합니다.

## 대상 VNIC에 backend NSG 연결

각 스택의 output을 확인합니다.

```sh
terraform -chdir=terraform/bastion output -raw backend_nsg_id
```

VNIC ID와 NSG ID를 지정해 먼저 미리봅니다. 다음 명령의 `REPLACE`를 바꾸어 사용합니다.

```sh
python3 scripts/access.py attach-nsg --region ap-seoul-1 \
  --vnic-id ocid1.vnic.oc1.ap-seoul-1.REPLACE \
  --nsg-id ocid1.networksecuritygroup.oc1.ap-seoul-1.REPLACE
```

확인 후 같은 명령에 `--execute`를 추가하면 기존 NSG 목록을 조회하고 새 NSG를 병합합니다. ETag 조건부 갱신으로 동시 변경이 있으면 실패하게 합니다. 실패 시 최신 목록부터 다시 확인합니다. 도구는 서브넷/VNIC/NSG의 VCN 일치를 사전에 조회하지 않으므로 대상 자원을 Console에서 확인해야 합니다.

기존 NSG가 5개이면 자동 교체하지 않습니다. 기존 NSG·Security List의 넓은 허용 규칙이 남아 있으면 이 NSG를 추가해도 접근 범위가 좁아지지 않습니다. 보안 규칙은 허용 규칙의 합집합으로 검토해야 합니다.

출처와 provider 문서: [참고 자료](../reference/sources.md).
