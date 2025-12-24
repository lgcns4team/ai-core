# 🚀 Integrated API - Face Detection & Voice Order

Intel RealSense 기반 얼굴 감지/분석 API와 음성 인식 기반 주문 API를 하나의 서버에서 제공하는 통합 서비스입니다.

## 📋 목차

- [주요 기능](#-주요-기능)
- [프로젝트 구조](#-프로젝트-구조)
- [설치 방법](#-설치-방법)
- [실행 방법](#-실행-방법)
- [API 엔드포인트](#-api-엔드포인트)
- [사용 예시](#-사용-예시)
- [설정](#-설정)
- [문제 해결](#-문제-해결)

---

## 🎯 주요 기능

### 1️⃣ 얼굴 감지 및 분석 (Face Detection)

- **Intel RealSense D415** 카메라 기반 깊이 측정
- **거리 필터링**: 1.5m 이내의 얼굴만 감지
- **지속 감지**: 1초 이상 얼굴이 감지되어야 분석 시작
- **AI 분석**: DeepFace를 이용한 나이/성별 추정
- **실시간 스트리밍**: SSE(Server-Sent Events)로 상태 실시간 업데이트
- **쿨다운 시스템**: 3초 쿨다운으로 중복 분석 방지

### 2️⃣ 음성 주문 (Voice Order)

- **음성 인식**: Faster-Whisper 기반 고속 STT
- **노이즈 제거**: 자동 배경 소음 제거로 인식률 향상
- **AI 의도 분석**: GPT-4를 활용한 지능형 주문 파악
- **발음 교정**: 부정확한 발음 자동 수정
- **다양한 명령어**: ADD/UPDATE/REMOVE/CLEAR 지원
- **옵션 처리**: 온도, 사이즈, 추가 옵션 자동 매핑

---

## 📁 프로젝트 구조

```
integrated_api/
├── main.py                    # ⭐ 통합 메인 애플리케이션
├── run.py                     # Windows 실행 스크립트
├── requirements.txt           # 패키지 의존성
├── .env.example              # 환경 변수 예시
├── .gitignore                # Git 제외 파일
│
├── config/                    # 설정
│   ├── __init__.py
│   └── settings.py           # 전역 설정 (API 키, 모델 설정)
│
├── routers/                   # API 라우터 (엔드포인트)
│   ├── __init__.py
│   ├── detect.py             # 얼굴 감지 API
│   └── voice.py              # 음성 주문 API
│
├── services/                  # 비즈니스 로직
│   ├── __init__.py
│   ├── detect.py             # 얼굴 감지 서비스
│   └── voice.py              # 음성 주문 서비스
│
├── schemas/                   # 데이터 검증 (Pydantic)
│   ├── __init__.py
│   ├── detect.py             # 얼굴 감지 스키마
│   └── voice.py              # 음성 주문 스키마
│
├── models/                    # 데이터 모델
│   ├── __init__.py
│   └── voice.py              # 메뉴/옵션 데이터베이스
│
└── utils/                     # 유틸리티
    ├── __init__.py
    ├── audio.py              # 오디오 처리 (노이즈 제거)
    └── parser.py             # 명령어 파싱
```

---

## 🔧 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd integrated_api
```

### 2. 가상환경 생성 (권장)

```bash
# Python 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 패키지 설치

```bash
pip install -r my_req.txt
```

**참고**: 처음 설치 시 10-15분 정도 걸릴 수 있습니다.

### 4. 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일을 열어 OpenAI API 키 입력
# OPENAI_API_KEY=sk-your-actual-api-key-here
HOST=0.0.0.0
PORT=8000
ENABLE_VOICE=true
ENABLE_DETECTION=false
ENABLE_GESTURE=true
GESTURE_CAMERA_INDEX=1
```

---

## 🚀 실행 방법

### 방법 1: run.py 사용 (권장)

```bash
python run.py
```

### 방법 2: main.py 직접 실행

```bash
python main.py
```

### 방법 3: uvicorn 명령어

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 실행 로그 예시

```
============================================================
🚀 통합 API 시스템 시작...
============================================================

[1/2] 얼굴 감지 서비스 초기화 중...
⏳ 카메라 워밍업 중...
✅ 카메라 초기화 완료
🔄 감지 루프 시작...
✅ 얼굴 감지 서비스 시작 완료

[2/2] 음성 주문 서비스 초기화 중...
🔄 Faster-Whisper 모델 로드 중 (small)...
✅ Whisper 모델 로드 완료
✅ OpenAI 클라이언트 초기화 완료
✅ 음성 주문 서비스 시작 완료

============================================================
✅ 모든 서비스 준비 완료!
📍 서버 주소: http://0.0.0.0:8000
📚 API 문서: http://0.0.0.0:8000/docs
============================================================
```

서버는 `http://0.0.0.0:8000`에서 실행됩니다.

---

## 📚 API 엔드포인트

### 🏠 루트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 서비스 정보 및 엔드포인트 목록 |
| GET | `/docs` | Swagger UI (API 문서) |
| GET | `/redoc` | ReDoc (API 문서) |

### 👤 얼굴 감지 (Face Detection)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/analysis` | 최신 분석 결과 조회 |
| DELETE | `/api/analysis` | 분석 데이터 초기화 |
| GET | `/api/status` | 시스템 상태 확인 |
| GET | `/api/stream/status` | 실시간 상태 스트리밍 (SSE) |

### 🎤 음성 주문 (Voice Order)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/order/voice` | 음성 파일 업로드 및 주문 처리 |
| GET | `/order/test` | API 테스트 |

---

## 💡 사용 예시

### 1️⃣ 얼굴 감지 API 사용

#### 상태 확인

```bash
curl http://localhost:8000/api/status
```

**응답 예시:**
```json
{
  "status": "running",
  "is_analyzing": false,
  "face_detected": false,
  "has_data": true,
  "depth_threshold": 1.5,
  "cooldown_period": 3
}
```

#### 분석 결과 조회

```bash
curl http://localhost:8000/api/analysis
```

**응답 예시:**
```json
{
  "age": 28,
  "gender": "남성",
  "timestamp": "2024-12-16 15:30:45"
}
```

#### Python 예시

```python
import requests

# 상태 확인
response = requests.get("http://localhost:8000/api/status")
print(response.json())

# 분석 결과 조회
response = requests.get("http://localhost:8000/api/analysis")
if response.status_code == 200:
    data = response.json()
    print(f"나이: {data['age']}세, 성별: {data['gender']}")
else:
    print("분석 데이터 없음")
```

---

### 2️⃣ 음성 주문 API 사용

#### 음성 파일 업로드

```bash
curl -X POST "http://localhost:8000/order/voice" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@audio.webm"
```

**응답 예시:**
```json
{
  "text": "아메리카노 아이스로 한 잔 주세요",
  "actions": [
    {
      "type": "ADD",
      "data": {
        "id": "americano",
        "name": "아메리카노",
        "options": ["아이스", "그란데 사이즈"],
        "option_ids": ["cold", "grande"],
        "price": 4000,
        "quantity": 1
      }
    }
  ]
}
```

#### Python 예시

```python
import requests

# 음성 파일 업로드
url = "http://localhost:8000/order/voice"
files = {"file": open("order.webm", "rb")}

response = requests.post(url, files=files)
result = response.json()

print(f"인식된 텍스트: {result['text']}")
for action in result['actions']:
    if action['type'] == 'ADD':
        data = action['data']
        print(f"메뉴: {data['name']}")
        print(f"옵션: {', '.join(data['options'])}")
        print(f"가격: {data['price']}원")
```

---

## ⚙️ 설정

### 얼굴 감지 설정 (services/detect.py)

```python
# 감지 거리 조정 (미터)
self.depth_threshold = 1.5  # 기본값: 1.5m

# 쿨다운 시간 조정 (초)
self.cooldown_period = 3  # 기본값: 3초
```

### 음성 주문 설정 (config/settings.py)

```python
# Whisper 모델 크기
WHISPER_MODEL_SIZE = "small"  # tiny, base, small, medium, large

# 노이즈 감소 비율
NOISE_REDUCTION_PROP = 0.75  # 0.0~1.0
```

---

## 🛠 문제 해결

### 카메라가 인식되지 않는 경우

1. USB 3.0 포트 확인
2. RealSense SDK 설치 확인
3. Intel RealSense Viewer로 테스트

### ImportError 발생

```bash
python run.py  # 경로 문제 자동 해결
```

### OpenAI API 에러

- `.env` 파일에 올바른 API 키 확인

---

## 📦 시스템 요구사항

- **Python 3.8+**
- **4GB+ RAM** (권장: 8GB)
- **Intel RealSense D415** 카메라 (얼굴 감지용)
- **OpenAI API Key** (음성 주문용)

---

## 🌟 특징

- ✅ **단일 서버**: 하나의 main.py에서 두 서비스 처리
- ✅ **독립적 동작**: 한 서비스 실패해도 다른 서비스는 작동
- ✅ **체계적 구조**: 유지보수 쉬운 파일 구조
- ✅ **완벽한 문서**: README, QUICKSTART 포함

---

## 📝 라이센스

MIT License

---
