# Bastion 준비와 접속

개발자 PC에서 Compute의 사설 IP로 SSH 또는 TCP 연결을 엽니다. 관리형 Bastion을 사용하므로 별도 점프 VM을 운영하지 않습니다.

## 준비

1. 로컬에 OCI CLI와 OpenSSH를 설치하고 사용할 OCI 프로파일을 구성합니다. Cloud Shell을 사용하지 않아도 됩니다.
2. 대상 VCN·서브넷에 Bastion을 생성하거나 기존 Bastion을 사용합니다. 생성 예제는 [Terraform 안내](infrastructure.md#bastion)에 있습니다.
3. 여러 사설 주소에 접근하려면 Bastion의 `FQDN Support and SOCKS5`를 활성화합니다.
4. Bastion의 client CIDR allowlist에 회사·VPN 출구 또는 현재 PC의 공인 IP를 허용합니다. 사설 IP나 VM IP를 넣는 항목이 아닙니다.
5. 대상 NSG 또는 Security List에서 Bastion **사설 엔드포인트 IP/32 → 필요한 TCP 포트**를 허용합니다. 대상 OS 방화벽도 확인합니다.
6. Bastion이 사용하는 서브넷의 egress 규칙이 해당 대상과 포트에 도달할 수 있어야 합니다.
7. Bastion 조회와 세션 생성·조회·삭제 IAM 권한이 필요합니다. 관리자에게 특정 Bastion으로 범위를 제한해 요청합니다.
8. [공식 Bastion 생성 문서](https://docs.oracle.com/en-us/iaas/Content/Bastion/Tasks/create-bastion.htm)에 명시된 **Service Gateway와 해당 경로 규칙**을 준비합니다. 이 저장소의 Bastion Terraform 예제는 기존 네트워크를 사용하며 Service Gateway를 자동 생성하지 않습니다.

**관리형 Bastion으로 사설 대상에 포워딩하려고 고객 VCN에 IGW나 NAT를 추가할 필요는 없습니다.** Service Gateway 준비와 대상 접근 규칙은 필요합니다. Public IP를 붙인 자체 점프 VM의 SSH 접속은 별도 구성이며, 인터넷에서 직접 접속하려면 IGW가 필요합니다. [방식별 비교](../../README.md#igwnat-필요-조건)

Bastion은 단일 VCN에 연결됩니다. 리전 이름만 같다고 다른 VCN의 대상을 사용할 수 있다고 가정하지 마십시오. 관리 대상 VCN별 Bastion을 설정에 구분해 등록합니다.

공개키와 개인키는 한 쌍이어야 합니다. 새 키가 필요하면 다음처럼 생성합니다.

```sh
ssh-keygen -t ed25519 -f ~/.ssh/oci-bastion
chmod 600 ~/.ssh/oci-bastion
```

개인키 암호를 설정할 수 있습니다. 이 도구는 암호를 저장하지 않고 SSH의 입력 절차를 사용합니다. VM 로그인 키는 Bastion 세션 인증 키와 별도로 설정할 수 있습니다.

## 설정과 실행

저장소 루트 `oci-secure-workflows/`에서 다음을 실행합니다.

```sh
cp config/access.example.json config/access.json
```

`regions`에 프로파일에 맞는 리전·Bastion OCID·키 경로·TTL을 넣고, `targets`에 VM의 사설 IP와 포트를 입력합니다. 예제의 `REPLACE`와 `203.0.113.*`는 실제 값으로 바꿉니다.

```sh
python3 scripts/access.py validate
python3 scripts/access.py doctor
python3 scripts/access.py plan dev-ssh
python3 scripts/access.py connect dev-ssh --execute
```

`validate`는 설정 형식만 확인합니다. `doctor`는 로컬 실행 파일과 키 파일 존재 여부를 확인합니다. 실제 실행 시 Bastion 상태·TTL·SOCKS5 활성화 여부를 추가 확인한 뒤 세션 하나를 생성합니다.

SSH 호스트키 확인이 나타나면 조직의 확인 절차에 따라 검증합니다. `StrictHostKeyChecking=no`로 생략하지 마십시오. `Ctrl+C`로 로컬 터널을 종료합니다.

## 세션 수명과 정리

세션은 최대 3시간입니다. 도구는 세션 재사용·자동 갱신·백그라운드 재접속을 하지 않습니다. 만료되면 다시 실행하고 클라이언트도 재접속합니다. 기존 TCP 연결은 새 터널로 이전되지 않습니다.

실행 시 표시되는 `Session:` ID와 삭제 명령을 사용 후 보관·실행합니다. 로컬 SSH 종료만으로 OCI 세션은 삭제되지 않습니다. 키가 틀리거나 터널 연결에 실패해도 생성된 세션은 남을 수 있습니다.

생성 요청이 타임아웃되면 OCI에서 세션이 만들어졌을 수 있습니다. 즉시 반복 실행하지 말고 Console의 해당 Bastion Sessions에서 상태와 `oci-secure-workflows` 이름·생성 시간을 확인합니다. 세션 삭제도 비동기일 수 있으므로 Console에서 최종 상태를 확인합니다.

## 문제 해결

| 증상 | 확인 순서 |
|---|---|
| CLI Unauthorized / NotAuthorizedOrNotFound | profile·region·Bastion OCID·IAM |
| Bastion SSH 타임아웃 | client allowlist의 실제 공인 출구 IP, 회사망의 outbound TCP 22 허용 |
| 세션은 ACTIVE지만 대상 연결 실패 | Bastion endpoint에서 대상 포트까지 egress·NSG·Security List·OS 방화벽·서비스 listen 주소 |
| SOCKS5 실행 거부 | Bastion DNS/SOCKS5 활성화 여부 |
| Address already in use | 해당 target의 local_port 변경 또는 기존 터널 종료 |
| 3시간 이내에 끊김 | 생성 시각과 TTL, 네트워크 변경, 노트북 잠자기, SSH 오류 확인 |
| key permission 오류 | 개인키 `chmod 600`, 공개키·개인키 쌍 확인 |

출처: [Bastion 개념](https://docs.oracle.com/en-us/iaas/Content/Bastion/Concepts/bastionoverview.htm), [세션 접속과 네트워크 규칙](https://docs.oracle.com/en-us/iaas/Content/Bastion/Tasks/connectingtosessions.htm), [TTL 설정](https://docs.oracle.com/en-us/iaas/Content/Bastion/Tasks/create-bastion.htm).
