# 개발 도구별 사설 접속

아래 명령은 저장소 루트 `oci-secure-workflows/`에서 실행합니다. 예제 대상은 `config/access.json`에서 실제 주소로 바꾸어야 합니다. 터널 터미널을 열어 둔 상태로 다른 터미널이나 앱을 사용합니다.

## SSH와 VS Code

고정 포워딩으로 VM의 22번 포트를 연결합니다.

```sh
python3 scripts/access.py connect dev-ssh --execute
```

별도 터미널에서 대상 VM의 키와 사용자로 접속합니다.

```sh
ssh -i ~/.ssh/oci-vm -o HostKeyAlias=oci-ap-seoul-1-10.0.1.10 -p 2222 opc@127.0.0.1
```

반복 접속은 다음 명령으로 생성되는 블록을 확인한 뒤 `~/.ssh/config`에 추가합니다. 기존 설정 파일을 덮어쓰지 마십시오.

```sh
python3 scripts/access.py ssh-config dev-ssh
```

그 뒤 `ssh dev-ssh`, 또는 VS Code의 Remote SSH에서 `dev-ssh`를 선택합니다. HostKeyAlias는 localhost 포트를 재사용할 때 서로 다른 VM의 호스트키가 혼동되지 않도록 합니다. IP가 바뀌면 설정을 다시 생성합니다.

연결 만료 후에도 작업이 필요하면 VM에서 `tmux` 또는 작업 스케줄러로 작업을 실행합니다. 터널 재접속으로 VS Code 연결이 항상 자동 복구되지는 않습니다.

## 단일 웹 개발 서버

```sh
python3 scripts/access.py connect dev-web --execute
```

브라우저에서 `http://127.0.0.1:8080`에 접속합니다. 대상 애플리케이션은 VM 사설 IP 또는 적절한 인터페이스에 listen해야 합니다. VM의 `127.0.0.1`에만 바인딩된 서비스는 Bastion이 직접 접근할 수 없습니다.

OAuth callback, 쿠키 도메인, Host 검증 때문에 localhost URL이 맞지 않는 앱은 아래 SOCKS5 방식으로 원래 사설 도메인을 사용하는 편이 낫습니다. 인증서 검증을 끄는 방법으로 해결하지 않습니다.

## 여러 웹과 사설 API를 SOCKS5로 사용

개발 웹앱과 관리 화면처럼 여러 사설 주소를 번갈아 열 때 사용합니다. `127.0.0.1:1080`에 중계기를 하나 열고 브라우저나 도구가 접속할 사설 IP·포트를 요청마다 알려 주는 방식입니다. 터널 실행 후 **앱에도 프록시를 지정해야** 동작합니다. 처음이면 [SOCKS5로 사설 웹 화면 두 개 열기](socks5-walkthrough.md)를 먼저 따라가십시오.

```sh
python3 scripts/access.py connect seoul-socks --execute
```

브라우저의 SOCKS5 호스트를 `127.0.0.1`, 포트를 `1080`으로 설정합니다. 사설 도메인을 사용한다면 SOCKS를 통한 DNS 조회도 켭니다. 개발용 브라우저 프로파일을 분리하면 일반 인터넷 요청까지 VCN으로 전달되는 일을 줄일 수 있습니다.

curl에서 원격 DNS 조회를 포함하려면 다음과 같이 사용합니다.

```sh
curl --proxy socks5h://127.0.0.1:1080 http://10.0.1.10:8080/health
```

`http://127.0.0.1:1080`을 브라우저 주소창에 입력하는 방식은 아닙니다. 해당 포트는 HTTP 서버가 아니라 SOCKS 프록시입니다. TLS 서비스는 실제 인증서와 일치하는 호스트 이름으로 호출합니다.

macOS의 OpenBSD 계열 `nc`를 사용하는 SSH 프록시 예제입니다. OS별 nc 옵션이 다를 수 있습니다.

```sh
ssh -o 'ProxyCommand=nc -X 5 -x 127.0.0.1:1080 %h %p' \
  -i ~/.ssh/oci-vm opc@10.0.1.10
```

## DB

```sh
python3 scripts/access.py connect dev-db --execute
```

DB 클라이언트에는 host `127.0.0.1`, port `11521`을 입력합니다. 서비스명·계정·인증서는 실제 DB 설정을 유지합니다. ADB의 mTLS wallet·TLS 호스트명·접속 문자열은 별도로 맞춰야 하며, 일반 DB용 예제를 그대로 적용할 수 있다고 가정하지 않습니다.

ADB는 [관리형 서비스 접속](managed-services.md)을 따릅니다. SQL·웹 443·앱의 직접 연결과 TLS 이름·wallet을 설명합니다. 동시 접속은 [여러 목적지 연결](multiple-targets.md)을 확인합니다.

## Windows RDP

```sh
python3 scripts/access.py connect dev-rdp --execute
```

Windows App 또는 RDP 클라이언트의 PC 주소는 `127.0.0.1:13389`, 계정은 대상 Windows 계정입니다. 이 경로는 TCP 기반이며 RDP의 UDP 최적화 경로는 제공하지 않습니다.

## kubectl

단일 Kubernetes API는 해당 사설 IP:6443을 고정 포워딩하는 구성을 우선 검토합니다. API 서버 인증서의 원래 DNS 이름을 `tls-server-name`으로 유지하고 kubeconfig server 주소를 로컬 포트로 연결해야 할 수 있습니다.

기존 kubeconfig를 변경하지 않고 SOCKS5를 일회성 사용하려면, `kubectl options`에 `--proxy-url`이 있는 버전에서 다음처럼 실행합니다.

```sh
kubectl --proxy-url=socks5://127.0.0.1:1080 --context YOUR_CONTEXT get nodes
```

원래 API server 주소·TLS 인증서를 유지합니다. 클라이언트 버전과 원격 DNS 처리를 확인하십시오. Kubernetes 문서상 SOCKS5 프록시는 SPDY 스트리밍 경로인 `exec`, `attach`, `port-forward`를 지원하지 않습니다. 실제 전송 프로토콜과 버전에 따라 동작이 달라지므로 해당 작업까지 일반화하지 않습니다. OKE 인증에 필요한 로컬 OCI 인증도 별도로 유효해야 합니다.

출처: [공유 스크립트 활용 예](https://github.com/TheKoguryo/oci-bastion-proxy/blob/main/README.ko.md), [Kubernetes kubeconfig proxy-url](https://kubernetes.io/docs/reference/config-api/kubeconfig.v1/), [OCI 포트포워딩 접속](https://docs.oracle.com/en-us/iaas/Content/Bastion/Tasks/connect-port-forwarding.htm).
