# OCI Secure Workflows 설계

작성: 2026-11-22. 상태: 로컬 구현 설계. 실제 OCI 적용·Assurance 판정 검증 전.

## 목적과 완료 기준

Public IP를 사용하는 Compute의 개발·관리 접속과 웹/API 접속을 분리한다. 사용자는 설정 파일에서 대상을 골라 Bastion 터널을 열고, Terraform 계획으로 공개 진입점과 아웃바운드 경로를 검토할 수 있어야 한다. 기본 명령은 OCI 변경을 수행하지 않으며, 테스트는 실제 테넌시를 호출하지 않는다.

## 범위

독립 프로젝트 `oci-secure-workflows`로 구성하고 GitHub에서 문서·실행 도구·예제를 함께 관리한다. 설계를 먼저 작성하고 구현과 검증 결과를 연결한다. 실제 자원 인벤토리와 운영 환경별 설정은 저장소에 포함하지 않는다.

- Python 표준 라이브러리 CLI: 설정 검증, 대상 목록, 포트포워딩/SOCKS5 계획, 명시적 실행, SSH 설정 출력, VNIC NSG 병합 연결.
- 별도 Terraform 스택: 관리형 Bastion, HTTPS LB, JWT 인증 API Gateway, NAT와 신규 라우트 테이블.
- SSH·VS Code·DB·브라우저·RDP·kubectl 사용법, VPN/NLB 선택 기준, 단계별 전환·복구 절차.
- 서비스 생성이나 Public IP 제거를 자동으로 실행하지 않는다. 기존 서브넷의 라우트 테이블 연결도 자동 변경하지 않는다.

## 공통 기반 검토

python-foundation은 FastAPI/DB/인증/미디어 실행 라이브러리이며 OCI 접속 CLI 공통 기반은 확인되지 않았다. 기존 scripts/inventory.py는 import 시 출력 디렉터리 생성과 환경별 상수가 있어 접속 도구에서 재사용하기 어렵다. 새 웹앱·DB·Python 패키지 의존성을 추가하지 않고, OCI API 처리는 설치된 공식 OCI CLI에 위임한다. 프로젝트 공통 실행·검증은 access.py 내부 함수로 통일한다.

## 안전성과 수명

JSON은 데이터로만 읽고 eval/source/shell=True를 쓰지 않는다. 터널은 127.0.0.1에 바인딩한다. SSH 호스트키 검증을 끄지 않는다. --execute에서만 세션을 생성하며, 세션은 매번 신규 생성한다. 응답이 불확실한 생성 명령은 자동 재시도하지 않는다. 생성 후 세션 ID와 정리 명령을 표시하고, TTL 만료 후에는 다시 실행한다. 재접속으로 기존 연결을 복원한다고 주장하지 않는다.

설정의 키는 파일 경로만 담는다. 개인키·OCI 자격증명·실제 tfvars/state/plan은 배포물에 넣지 않는다. Terraform에는 기존 Certificate Service 인증서 OCID를 사용해 TLS 개인키를 넣지 않는다. LB/API용 backend NSG는 생성하되 VNIC에 연결하는 별도 단계가 필요하다. 기존 NSG·Security List의 넓은 허용 규칙은 별도로 정리해야 한다.

## 검증

설정 오류, 기본 실행의 무변경, 명령 인자 처리, OCI session 상태 전이·실패·타임아웃, loopback 바인딩, NSG 기존 목록 보존을 모의 실행기로 검증한다. Terraform은 fmt와 공식 provider 기반 validate를 수행한다. 실제 plan/apply와 네트워크 연결·정책 해소는 미검증 범위로 표시한다.

## 근거

Oracle Bastion/CLI/provider 공식 문서와 TheKoguryo/oci-bastion-proxy의 사용 흐름을 참고한다. 외부 코드는 복사하지 않고 출처별 채택·차이·한계를 reference/sources.md에 기록한다. 개인 연락처·실제 자원 목록은 예제에 포함하지 않는다.
