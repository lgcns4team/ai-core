import os
import uuid
import shutil
from faster_whisper import WhisperModel
from openai import OpenAI
from typing import List, Dict, Any

from config.settings import (
    OPENAI_API_KEY,
    WHISPER_MODEL_SIZE,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    MENU_KEYWORDS
)
from models.voice import get_all_menu_ids, get_all_option_ids
from utils.audio import remove_noise, validate_audio_file
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
    
    def transcribe_audio(self, audio_path: str) -> str:
        """
        오디오 파일을 텍스트로 변환 (STT)
        
        Args:
            audio_path: 오디오 파일 경로
            
        Returns:
            인식된 텍스트
        """
        try:
            segments, info = self.whisper_model.transcribe(
                audio_path,
                language="ko",
                beam_size=5,
                initial_prompt=MENU_KEYWORDS,
                vad_filter=True,  # 목소리가 없는 구간 자동 필터링
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
        
        Format(형식): UPDATE | 찾을ID | 바뀔ID | 수량 | 새옵션1,새옵션2...

        [옵션 매핑 규칙]
        - "아이스", "차가운거", "냉", "아아", "차갑게" -> [cold]
        - "따뜻한거", "뜨거운거", "따뜻하게", "핫" -> [hot]
        - "톨", "작은거", "스몰", "스몰사이즈" -> [tall]
        - "그란데", "중간사이즈", "미디엄" -> [grande]
        - "벤티", "큰거", "라지", "라지 사이즈" -> [venti]
        - "얼음 적게", "얼음 조금" -> [less_ice], "얼음 많이", "얼음 추가" -> [more_ice]
        - "샷 추가" -> [shot], "휘핑", "힙", "휩" -> [whip], "연하게" -> [weak]

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
    
    def process_voice_order(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        음성 파일을 처리하여 주문 액션 반환
        
        Args:
            file_path: 업로드된 파일 경로
            filename: 원본 파일명
            
        Returns:
            주문 결과 (text, actions)
        """
        # 고유 ID 생성
        unique_id = str(uuid.uuid4())
        temp_filename = f"temp_{unique_id}.webm"
        clean_filename = f"clean_{unique_id}.wav"
        
        try:
            # 1. 원본 저장
            shutil.copy(file_path, temp_filename)
            
            # 2. 노이즈 제거
            remove_noise(temp_filename, clean_filename)
            
            # 3. STT 변환
            text = self.transcribe_audio(clean_filename)
            
            if not text:
                return {"text": "", "actions": []}
            
            # 4. LLM 분석
            llm_output = self.analyze_intent(text)
            
            # 5. 명령어 파싱
            actions = process_commands(llm_output)
            
            return {"text": text, "actions": actions}
        
        except Exception as e:
            print(f"⚠️ 음성 주문 처리 실패: {e}")
            return {"text": "오류 발생", "actions": []}
        
        finally:
            # 6. 임시 파일 정리
            for path in [temp_filename, clean_filename]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass
    
    def cleanup(self):
        """서비스 종료 시 정리 작업"""
        print("🧹 서비스 정리 중...")
        # 필요시 추가 정리 작업
        print("✅ 정리 완료")