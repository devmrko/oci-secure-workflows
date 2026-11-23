# Cloudflare Tunnel·Access 실행과 검증

**Tunnel은 요청 전달 경로, Access는 사용자 인증·허용 정책**입니다. 사설 서버의 `cloudflared`가 외부로 연결하므로 서버 Public IP나 인터넷 인바운드 포트를 열지 않고 웹을 제공할 수 있습니다. OCI에서는 NAT 출구로 구성할 수 있으며, 라우트·DNS·필요한 외부 통신 허용이 필요합니다.

```text
사용자 → Cloudflare Access 로그인 → Cloudflare Tunnel → cloudflared → 사설 웹
                                                     서버에서 외부로 연결 시작
```

## 구성 선택

| 방식 | 설정 보관 위치 | 셸 입력 | 사용 조건 |
|---|---|---|---|
| Dashboard 관리 named tunnel | Cloudflare Dashboard | `--token-file` | 이번 실제 Access 시험에 사용 |
| 로컬 관리 named tunnel | 로컬 YAML·credentials JSON | `--config`와 `--tunnel` | [기존 로컬 구성 절차](easy-workflows.md#cloudflare-tunnel). 설정 검사까지 확인 |
| Quick Tunnel | 임시 생성 | 공식 CLI의 `--url` | 전달 경로의 임시 시험. named tunnel·Access 정책 검증을 대신하지 않음 |

## 1. 계정·비용 확인

Cloudflare 계정, 관리할 도메인, Zero Trust의 Access 사용 환경을 준비합니다. **Free의 기본료가 $0이라고 모든 사용의 무과금을 보장하지는 않습니다.** 이번 계정의 가입 화면은 카드 등록과 무료 한도 초과 시 과금 동의를 요구했습니다. 자신의 가입 화면·포함 한도·초과 요금을 확인하고 유료 옵션을 선택하지 않습니다.

## 2. 테스트용 웹 준비

커넥터가 있는 사설 VM은 **NAT 출구로 구성할 수 있으며, VM Public IP와 해당 서브넷의 Internet Gateway 경로는 필요하지 않습니다.** 단, DNS 조회와 Cloudflare 터널 목적지로 나가는 **TCP 7844(HTTP/2) 또는 UDP 7844(QUIC)**를 허용해야 합니다. 관리 API·다운로드용 HTTPS도 필요에 따라 허용합니다. TCP 443만 허용한 환경에서는 터널이 연결되지 않을 수 있습니다. 목적지 목록은 [공식 방화벽 요구사항](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-with-firewall/)을 확인합니다.

업무 데이터 대신 가상 응답으로 시험합니다. 아래는 별도 터미널에서 실행하는 로컬 서버 예제입니다. 저장소 전체나 홈 디렉터리를 공개하지 않습니다.

```sh
CF_DEMO_DIR=$(mktemp -d)
printf '%s\n' 'cloudflare-test-ok' > "$CF_DEMO_DIR/index.html"
python3 -m http.server 19090 --bind 127.0.0.1 --directory "$CF_DEMO_DIR"
```

같은 호스트의 cloudflared에서 `http://127.0.0.1:19090`을 사용합니다. 다른 서버가 backend이면 cloudflared에서 도달 가능한 사설 주소와 포트를 지정합니다.

## 3. Dashboard에서 앱·정책·터널 구성

Cloudflare One의 **Get started → Secure private apps → Private web application** 흐름을 사용할 수 있습니다. 메뉴 이름은 버전에 따라 달라질 수 있습니다.

1. 앱 이름과 backend `HTTP / 127.0.0.1 / 19090`을 지정합니다.
2. 기존 도메인 아래 테스트 전용 하위 도메인을 선택합니다. 기존 서비스의 DNS를 덮어쓰지 않습니다.
3. 접근을 허용할 본인 이메일을 지정하고 로그인 방법을 확인합니다. **Everyone 허용·인증 우회 정책은 사용하지 않습니다.**
4. 테스트 전용 named tunnel을 만들고, cloudflared를 실행할 호스트의 OS를 선택합니다.
5. 커넥터 토큰을 저장소 밖의 권한 제한 파일에 보관합니다. 토큰 값은 저장소·대화·셸 명령 인자에 넣지 않습니다.

Dashboard가 제시하는 `sudo ... service install`을 실행할 필요는 없습니다. 임시 시험은 아래 포그라운드 실행으로 진행합니다. 앱의 Access 정책과 DNS·터널 라우트가 만들어졌는지도 확인합니다. [공식 구성 절차](https://developers.cloudflare.com/cloudflare-one/setup/secure-private-apps/private-web-app/)

## 4. 셸 도우미로 실행

먼저 저장소 밖의 `$HOME/.cloudflared` 디렉터리를 만들고, 텍스트 편집기로 `oci-demo.token` 파일에 **토큰 문자열만** 저장합니다. Dashboard가 설치 명령을 보여주면 `sudo cloudflared service install` 부분은 파일에 넣지 않습니다. 셸에서 토큰을 직접 입력하면 명령 이력에 남을 수 있으므로 사용하지 않습니다. 이 도우미는 파일의 내용을 읽거나 출력하지 않고 경로를 공식 cloudflared에 전달합니다.

```sh
chmod 600 "$HOME/.cloudflared/oci-demo.token"
# 명령 미리보기
sh scripts/workflow.sh cloudflare run \
  --token-file "$HOME/.cloudflared/oci-demo.token" --protocol http2
# 실제 실행: 터미널 유지
sh scripts/workflow.sh cloudflare run \
  --token-file "$HOME/.cloudflared/oci-demo.token" --protocol http2 --execute
```

`--protocol`은 `auto`, `quic`, `http2` 중 선택합니다. 이번 환경에서는 일부 UDP 사전 검사가 실패했고 HTTP/2 연결은 성공했습니다. 연결 방식만 바꿔도 조직의 외부 통신 허용 규칙은 충족해야 합니다. `--config`와 `--token-file`을 함께 사용하지 않습니다. Dashboard 관리 모드에는 `--tunnel`을 추가하지 않습니다.

cloudflared의 `Registered tunnel connection`과 원격 ingress 설정 수신을 확인합니다. 초기 설정 수신 전의 `No ingress rules` 메시지만 보고 최종 실패로 판단하지 말고, 설정 수신·실제 응답까지 확인합니다.

## 5. 접속·차단 확인

실제 테스트 도메인으로 바꿔 실행합니다. `-L` 없이 첫 응답을 확인합니다.

```sh
CF_DEMO_URL='https://app.example.com/'
curl --silent --show-error --output /dev/null --dump-header - "$CF_DEMO_URL"
```

- **익명 요청:** 원본 문자열이 바로 나오지 않고 Access 로그인으로 이동해야 합니다. 이번 시험에서는 HTTP 302와 `cloudflareaccess.com` 로그인 URL을 확인했습니다.
- **허용 사용자:** 브라우저에서 원래 도메인을 열어 로그인한 뒤 `cloudflare-test-ok`를 확인합니다. 이번 실제 시험은 Cloudflare 계정 로그인을 사용했습니다.
- **위조 쿠키:** 아래 요청도 원본 응답을 받지 못해야 합니다. 이번 시험에서는 로그인으로 이동했습니다.

```sh
curl --silent --show-error --output /dev/null --dump-header - \
  --cookie 'CF_Authorization=invalid-test-value' "$CF_DEMO_URL"
```

다른 실제 사용자의 권한 거부, 이메일 PIN, 다른 IdP, 토큰 만료·회수는 별도 시험입니다. 로그인 화면 표시만으로 허용 사용자 시험까지 끝났다고 기록하지 않습니다. **Access를 만들지 않은 Quick Tunnel의 공개 URL은 인증된 웹 제공과 다릅니다.**

## 6. 종료와 정리

cloudflared와 테스트 웹 서버를 `Ctrl+C`로 종료합니다. 등록된 커넥터가 끊겼는지 확인하고, 테스트 앱·전용 정책·터널·DNS를 정리합니다. 임시 토큰 파일도 폐기합니다. 서비스 프로세스를 중지해도 Dashboard 자원과 DNS는 자동 삭제되지 않습니다. Zero Trust 플랜은 테스트 자원 삭제와 별도입니다.

이번 시험에서는 앱·전용 정책·터널·DNS 삭제와 로컬 프로세스 종료·임시 토큰 파일 폐기까지 확인했습니다. 사용자가 활성화한 Free 플랜은 유지했습니다.

## 실제 검증 범위

2026-11-23, cloudflared 2026.11.1·macOS 사설 LAN 호스트·루프백 가상 웹 서버로 확인했습니다.

| 시험 | 결과 |
|---|---|
| Quick Tunnel 외부 HTTPS | 로컬·외부 응답의 무작위 표식 일치, 별도 OCI VM에서도 응답 확인 |
| HTTP/2 전송 | 명시적 HTTP/2 연결·응답 성공 |
| Dashboard 관리 named tunnel | 원격 ingress 수신, 이 저장소 셸 도우미로 실행 성공 |
| Access 익명 요청·위조 쿠키 | HTTP 302로 Access 로그인 이동, 원본 응답 미제공 |
| 허용된 본인 계정 | 실제 브라우저 로그인 후 가상 서버 응답 확인, 커넥터의 HTTP 200 지표 확인 |
| 시험 범위 밖 | **OCI NAT Gateway를 통과하는 connector 배치**, 다른 사용자·IdP·PIN, 고가용성·성능 |

이번 결과를 OCI NAT 경유 검증으로 일반화하지 않습니다. [전체 검증 결과](../validation.md) · [Quick Tunnel 공식 범위](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
