import os
import uuid
import shutil
from faster_whisper import WhisperModel
from openai import OpenAI
from typing import List, Dict, Any
import numpy as np

from config.settings import (
    OPENAI_API_KEY,
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    MENU_KEYWORDS
)
from models.voice import get_all_menu_ids, get_all_option_ids
from utils.audio import load_audio_with_ffmpeg
from utils.parser import process_commands


class VoiceOrderService:
    """음성 주문 처리 서비스"""
    
    def __init__(self):
        self.whisper_model = None
        self.openai_client = None
        
    def initialize(self):
        """서비스 초기화"""
        print(f"🔄 Faster-Whisper 모델 로드 중 ({WHISPER_MODEL_SIZE})...")
        
        # Whisper 모델 로드
        self.whisper_model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE
        )
        print("✅ Whisper 모델 로드 완료")
        
        # OpenAI 클라이언트 초기화
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI 클라이언트 초기화 완료")
    
    def transcribe_audio(self, audio_data: np.ndarray) -> str:
        """
        오디오 데이터(Numpy Array)를 텍스트로 변환
        """
        try:
            # Whisper는 파일 경로뿐만 아니라 Numpy Array도 입력받음
            segments, info = self.whisper_model.transcribe(
                audio_data,
                language="ko",
                beam_size=5,
                initial_prompt=MENU_KEYWORDS,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            text = " ".join([segment.text for segment in segments]).strip()
            print(f"🎤 인식된 텍스트: {text}")
            return text
            
        except Exception as e:
            print(f"⚠️ STT 변환 실패: {e}")
            return ""
    
    
    def analyze_intent(self, text: str) -> str:
        """
        LLM을 사용하여 주문 의도 분석
        
        Args:
            text: 인식된 텍스트
            
        Returns:
            LLM이 생성한 명령어 문자열
        """
        menu_keys = ", ".join(get_all_menu_ids())
        option_keys = ", ".join(get_all_option_ids())

        system_prompt = f"""
        너는 카페의 '주문 의도 파악 및 오타 교정 AI'다.
        사용자의 음성 인식(STT) 결과는 부정확하거나 발음이 어눌할 수 있다.
        너의 임무는 엉망인 텍스트 속에서 **사용자의 진짜 의도(메뉴와 옵션)**를 추리해내는 것이다.

        [행동 지침]
        1. **문맥 추론**: "아이스티" -> "복숭아 아이스티", "바닐라 랖데" -> "바닐라라떼"
        2. **발음 기반 매칭**: 입력된 텍스트와 발음이 가장 유사한 메뉴/옵션 ID를 찾아라.
        3. **불필요한 말 무시**: "어...", "음...", "저기요" 같은 추임새는 과감히 버려라.
        4. **보수적 판단**: 메뉴판에 없는 말은 무시해라.
        5. **메뉴, 옵션 분리**: 메뉴와 옵션을 명확히 구분하여 인식해라.

        [동작 종류]
        - ADD: 신규 추가
        - UPDATE: 변경/수정 (기존 메뉴ID를 찾아서 새 메뉴ID/수량/옵션으로 변경)
        - REMOVE: 삭제/취소

        [메뉴ID 목록]: {menu_keys}
        [옵션ID 목록]: {option_keys}

        [⭐ 핵심 규칙 (UPDATE 필독)]
        사용자가 "바꿔줘", "변경해줘", "아니", "잘못 말했어", **"취소하고 ~로 줘"** 하거나 **"옵션 추가해줘"**, **"바꿀래"** 라고 하면 **무조건 UPDATE**를 써라.
        ** UPDATE ** 쓸떄 는 바뀌거나 추가하는 옵션 말고 기존의 옵션은 유지 시켜라.

        # ✅ [추가된 삭제 규칙] 순서 지정 삭제
        # 사용자가 "처음", "맨 앞", "제일 먼저" 시킨걸 지우라고 하면 4번째 칸에 'first'를 적어라.
        # 언급이 없거나 "방금", "최근" 것이면 생략하거나 'last'로 간주한다.

        0. 문맥 참조 해결
        사용자가 메뉴명을 말하지 않고 "아까 담은 거", "방금 시킨 거", "그거", "이거" 라고 지칭하면 메뉴ID를 **`last_item`** 으로 적어라.
        
        [⭐ 출력 형식 - 정확히 지켜라]
        ADD 형식: ADD | 메뉴ID | 메뉴명 | 수량 | 옵션1,옵션2
        UPDATE 형식: UPDATE | 찾을ID | 바뀔메뉴명 | 수량 | 새옵션1,새옵션2
        REMOVE 형식: REMOVE | 메뉴ID | 삭제수량 | 삭제모드

        [삭제 패턴 처리]
        - "1잔만 빼줘" → REMOVE | last_item | 1 | last
        - "첫 번째 라떼 삭제" → REMOVE | 카페라떼 | all | first  
        - "아메리카노 2개 빼줘" → REMOVE | 아메리카노 | 2 | last

        [올바른 예시]
        ADD | 아메리카노 | 아메리카노 | 2 | cold
        ADD | 카페라떼 | 카페라떼 | 1 | hot,grande
        UPDATE | last_item | 카페라떼 | 1 | cold,shot

        [⭐ 고급 키워드 처리 규칙]
        너는 다음 순서로 키워드를 처리해라:

        1. 정확한 매칭 우선

        2. 유사음 보정:
        - ㄱ/ㄲ 혼동: "까페라떼"→"카페라떼", "까푸치노"→"카푸치노"
        - 받침 변화: "아메리까노"→"아메리카노", "에스프렛소"→"에스프레소"
        - 발음 생략: "카라멜마끼아또"→"카라멜 마키아토", "바닐라랕데"→"바닐라라떼"
        - 자음동화: "콜드브루"→"콜드브루", "핫초콜릿"→"핫초콜릿"

        3. 방언/사투리:
        - 온도: "찬거"→cold, "뜨신거"→hot, "미지근한거"→온도없음, "차가운거"→cold
        - 크기: "큰거"→venti, "작은거"→tall, "중간거"→grande, "제일큰거"→venti
        - 양: "많이"→more_ice, "조금"→less_ice, "적게"→less_ice, "가득"→more_ice

        4. 오타/발음 허용:
        - 모음혼동: "아이스으"→cold, "따듯하게"→hot, "그란데이"→grande
        - 받침오타: "벤티으"→venti, "샷으"→shot, "휘핑으"→whip
        - 띄어쓰기: "벤티사이즈"→venti, "샷추가"→shot, "얼음많이"→more_ice

        5. 의미 추론:
        - 온도표현: "시원하게"→cold, "차갑게"→cold, "따뜻하게"→hot, "뜨겁게"→hot
        - 강도표현: "연하게"→weak, "진하게"→shot, "강하게"→shot
        - 양표현: "듬뿍"→more_ice, "살짝"→less_ice, "평소대로"→normal_ice

        [🎯 특별 처리 패턴]
        생략형 메뉴:
        - "아아" = "아이스 아메리카노"  
        - "뜨아" = "아메리카노" + hot
        - "아라" = "아이스 카라멜 마키아토"
        - "바라" = "바닐라라떼"

        복합 표현:
        - "차갑게 해주세요" = cold 추가
        - "뜨겁게 주세요" = hot 추가  
        - "큰 사이즈로" = venti 추가
        - "얼음 빼주세요" = less_ice 추가

        변경/수정 요청:
        - "뜨겁게 바꿔줘" = 온도를 hot으로 UPDATE
        - "큰걸로 바꿔줘" = 사이즈를 venti로 UPDATE
        - "샷 하나 더" = shot 옵션 추가 UPDATE

        추가 요청 패턴:
        - "휘핑 올려줘" = whip 추가
        - "샷 넣어줘" = shot 추가  
        - "얼음 많이" = more_ice 추가
        - "연하게 해줘" = weak 추가

        [옵션 매핑 규칙]
        - "아이스", "차가운거", "냉", "아아", "차갑게" -> cold
        - "따뜻한거", "뜨거운거", "따뜻하게", "핫" -> hot
        - "톨", "작은거", "스몰", "스몰사이즈" -> tall
        - "그란데", "중간사이즈", "미디엄" -> grande
        - "벤티", "큰거", "라지", "라지 사이즈" -> venti
        - "얼음 적게", "얼음 조금" -> less_ice, "얼음 많이", "얼음 추가" -> more_ice
        - "샷 추가" -> shot, "휘핑", "힙", "휩" -> whip, "연하게" -> weak

        [출력]
        오직 데이터 라인만 출력해라. 설명 금지.
        """

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"In: {text}"}
                ],
                temperature=0.0,
                max_tokens=200
            )
            answer = response.choices[0].message.content.strip()
            print("--------------------------------------------------")
            print(f"🤖 LLM의 응답 원본:\n{answer}")
            print("--------------------------------------------------")
            return answer
        
        except Exception as e:
            print(f"⚠️ LLM API 에러: {e}")
            return ""
    
    def process_voice_order(self, file_bytes: bytes) -> Dict[str, Any]:
        """
        업로드된 파일 바이트를 직접 처리 (속도 최적화)
        """
        try:
            # 1. FFmpeg로 노이즈 제거 및 디코딩 (In-Memory)
            # 파일 저장 과정(shutil.copy) 삭제됨 -> 속도 대폭 향상
            clean_audio = load_audio_with_ffmpeg(file_bytes)
            
            if clean_audio.size == 0:
                return {"text": "", "actions": []}

            # 2. STT 변환 (Numpy Array 직접 입력)
            text = self.transcribe_audio(clean_audio)
            
            if not text:
                return {"text": "", "actions": []}
            
            # 3. LLM 분석 (기존 로직 사용, analyze_intent 구현 필요)
            # 임시로 위에서 생략했으므로, 실제 파일에는 기존 코드가 있어야 함
            llm_output = self.analyze_intent(text)
            
            # 4. 명령어 파싱
            actions = process_commands(llm_output)
            
            return {"text": text, "actions": actions}
        
        except Exception as e:
            print(f"⚠️ 음성 주문 처리 실패: {e}")
            return {"text": "오류 발생", "actions": []}
    
    def cleanup(self):
        print("✅ 서비스 종료")