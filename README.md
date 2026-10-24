<p>
  <a href="https://mixedcas-lab.github.io/"><img src="assets/mcaslab.png" alt="MCAS Lab" height="34"></a>
  &nbsp;&nbsp;
  <a href="https://www.uos.ac.kr"><img src="assets/uos.png" alt="University of Seoul" height="20"></a>
</p>

# AI Accelerator Census

AI 가속기(NPU·DNN/Transformer 프로세서)와 Compute-in-Memory(CIM)·Processing-in-Memory(PIM) 논문을 회로·아키텍처·설계자동화 분야의 상위 IEEE 학회와 저널에서 모아 보여주는 사이트입니다. MCAS Lab(서울시립대학교 첨단융합학부)에서 운영합니다. 자매 사이트: [ADC](https://mixedcas-lab.github.io/adc-census/) · [PLL](https://mixedcas-lab.github.io/pll-census/) · [LDO](https://mixedcas-lab.github.io/ldo-census/) · [PMIC](https://mixedcas-lab.github.io/pmic-census/) Census.

- 사이트: https://mixedcas-lab.github.io/accel-census/
- 데이터 출처: IEEE Xplore API (서지 메타데이터와 링크만 공개, 초록·본문은 올리지 않음)

## 대상 venue (2012년부터)

| 분야 | 학회 | 저널 |
|---|---|---|
| 회로 | ISSCC, VLSI Symposium, CICC, ESSCIRC/ESSERC, A-SSCC | JSSC, SSC-L, TCAS-I, JETCAS, TVLSI |
| 아키텍처 | MICRO, HPCA | IEEE Transactions on Computers, IEEE Micro |
| 설계자동화 | DAC, ICCAD, DATE | TCAD |

ISCA와 ASPLOS는 ACM Digital Library에만 있어 IEEE Xplore API로 받을 수 없습니다.

## 구성

```
index.html, app.js, style.css   사이트 (빌드 과정 없음, GitHub Pages가 그대로 서비스)
data/papers.json                논문 목록 (빌더가 생성)
data/meta.json                  갱신일, 범위, 집계
data/annotations.csv            검수 값 (사람이 편집)
collector/build.py              adc-census 캐시를 읽어 papers.json 생성 (Python 3.8+, 표준 라이브러리만)
collector/classify.py           판별, 유형(Digital / CIM·PIM)·구조·응용 태깅, 실측 칩 여부, 수치 추출 규칙
collector/venues.json           시작 연도, 캐시 위치, venue 매칭 규칙
scripts/update.sh               랩 서버 cron용: 재생성 → 커밋 → push
```

## 동작 방식

1. **데이터**: adc-census 수집기가 위 학회·저널의 전체 논문을 랩 서버 캐시(`~/adc-census/cache/raw`)에 받아 둡니다(수집 범위는 adc-census `collector/venues.json`). 이 저장소는 캐시를 읽기만 하므로 IEEE API를 따로 쓰지 않습니다.
2. **분류**: 제목에 compute-in-memory·PIM·CIM이 있거나, 기계학습 워크로드(neural network, DNN, CNN, Transformer, LLM, SNN 등)와 하드웨어(accelerator, processor, NPU, macro, SoC 등)가 함께 있으면 core입니다. 초록에서만 가속기를 언급하면 related입니다. 신경 신호 기록 회로, 기계학습을 *이용한* EDA(배치·배선·타이밍 예측 등), RF·전력 회로의 transformer는 제외합니다.
3. **실측 칩(Measured silicon)**: 회로 학회·저널 논문이거나 초록에 fabricated·test chip·measured 등이 있으면 실측 칩, 나머지는 시뮬레이션 아키텍처로 봅니다.
4. **수치**: 제목·초록에서 에너지 효율(TOPS/W; GOPS/mW, fJ/op, pJ/MAC도 환산), 최대 처리량(TOPS), 면적 효율(TOPS/mm²), 전력, 클록, 정밀도(bit), 온칩 메모리, 공정, 면적을 정규식으로 뽑습니다. 여러 값이 있으면 최고값(peak)을 씁니다. 논문에 효율이 없으면 처리량/전력, 처리량/면적으로 계산합니다(≈ 표시).
5. **공개**: cron이 매일 07:02(adc-census 06:17 갱신 뒤) 재생성하고, 바뀐 것이 있으면 커밋·push합니다.

## 그래프

Chart 메뉴: TOPS/W vs. TOPS, TOPS/W vs. 전력(등처리량선), TOPS/W vs. 공정, TOPS/W vs. 정밀도, TOPS/W vs. TOPS/mm², TOPS/W 연도별 추세(누적 상위 3편 기하평균과 연간 배율), Custom(x·y축 직접 선택). 색은 구조, 연도, 공정, 정밀도, Digital/CIM 중에서 고릅니다.

TOPS/W는 논문마다 연산 정의(1 MAC = 2 ops), 비트 정밀도, 희소성 가정이 달라 직접 비교에 주의가 필요합니다. 정밀도 필터와 색으로 같은 조건끼리 비교하세요.

## 검수 값 넣기

GitHub 웹에서 `data/annotations.csv`를 열어 연필 아이콘으로 편집합니다. 사이트에 즉시 반영됩니다.

| 열 | 내용 |
|---|---|
| `id` | IEEE article number (Xplore 주소 끝의 숫자) |
| `exclude` | `1`이면 목록에서 제외 (오탐) |
| `type` | `Digital` 또는 `CIM/PIM` |
| `silicon` | `1` 실측 칩, `0` 시뮬레이션 |
| `arch`, `app` | 여러 개면 `;`로 구분 (예: `SRAM CIM;Sparsity`) |
| `eff`, `thr`, `aeff` | TOPS/W, TOPS, TOPS/mm² |
| `p`, `f` | W, Hz (`9.4m`, `200M`) |
| `prec`, `mem` | bit, byte (`512k`) |
| `node`, `area` | nm, mm² |
| `note`, `by` | 메모, 검수자 |

값을 지우려면 `-`를 넣습니다. 출처 우선순위는 사람 검수 > AI 추출 > 정규식이며, ADC·PLL Census와 같은 규칙입니다.

## 랩 서버 설정 (1회)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/accel_census -N "" -C "accel-census@lab-server"   # 공개키를 저장소 Deploy keys에 쓰기 권한으로 등록
cat >> ~/.ssh/config <<'CFG'
Host github-accel-census
  HostName ssh.github.com
  Port 443
  User git
  IdentityFile ~/.ssh/accel_census
  IdentitiesOnly yes
CFG
git clone github-accel-census:mixedcas-lab/accel-census.git ~/accel-census
mkdir -p ~/accel-census/logs
( crontab -l; echo "2 7 * * * PYTHON=$(command -v python3) $HOME/accel-census/scripts/update.sh >> $HOME/accel-census/logs/update.log 2>&1" ) | crontab -
```

GitHub Pages: 저장소 **Settings → Pages**에서 Source를 **Deploy from a branch**, Branch를 **main / (root)**로 지정합니다.

## 참고

- IEEE Xplore API 이용약관을 따릅니다. 초록과 본문은 공개하지 않고, 서지 정보와 Xplore 링크만 제공합니다.
- 자동 추출 수치는 오류가 있을 수 있습니다. 원문을 확인하고, 다르면 각 논문 아래 **Report a fix**로 알려 주세요.
