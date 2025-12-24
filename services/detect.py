import pyrealsense2 as rs
import numpy as np
import cv2
import time
from deepface import DeepFace
import warnings

warnings.filterwarnings('ignore')


class DepthFaceAnalyzer:
    """Intel RealSense D415 카메라를 이용한 깊이 기반 얼굴 분석기"""
    
    def __init__(self):
        self.pipeline = None
        self.align = None
        self.latest_analysis = None
        self.is_analyzing = False
        self.face_detected = False  # 얼굴 감지 상태
        self.face_detected_time = 0  # 얼굴 감지 시작 시간
        self.depth_threshold = 1.5  # 1.5미터 이내
        self.last_detection_time = 0
        self.cooldown_period = 3  # 3초 쿨다운
        
    def initialize_camera(self) -> bool:
        """D415 카메라 초기화"""
        try:
            self.pipeline = rs.pipeline()
            config = rs.config()
            
            # 해상도를 낮춰서 성능 향상
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            
            profile = self.pipeline.start(config)
            
            # Depth와 Color 정렬
            align_to = rs.stream.color
            self.align = rs.align(align_to)
            
            # 카메라 워밍업 (처음 몇 프레임 버리기)
            print("⏳ 카메라 워밍업 중...")
            for i in range(5):
                try:
                    self.pipeline.wait_for_frames(timeout_ms=2000)
                except:
                    pass
            
            print("✅ 카메라 초기화 완료")
            return True
        except Exception as e:
            print(f"❌ 카메라 초기화 실패: {e}")
            return False
    
    def get_frames(self):
        """카메라에서 프레임 가져오기"""
        try:
            # 타임아웃을 10초로 증가 (초기 프레임은 시간이 걸릴 수 있음)
            frames = self.pipeline.wait_for_frames(timeout_ms=10000)
            aligned_frames = self.align.process(frames)
            
            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()
            
            if not depth_frame or not color_frame:
                return None, None
            
            depth_image = np.asanyarray(depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())
            
            return depth_image, color_image
        except RuntimeError as e:
            # 타임아웃 에러는 심각하지 않으므로 조용히 처리
            if "Frame didn't arrive" in str(e):
                return None, None
            print(f"⚠️ 프레임 가져오기 실패: {e}")
            return None, None
        except Exception as e:
            print(f"⚠️ 프레임 가져오기 실패: {e}")
            return None, None
    
    def detect_face_in_range(self, depth_image, color_image):
        """일정 거리 내 얼굴 감지"""
        # OpenCV의 Haar Cascade로 얼굴 감지 (가벼움)
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        for (x, y, w, h) in faces:
            # 얼굴 중심의 깊이 측정
            center_x = x + w // 2
            center_y = y + h // 2
            
            # 얼굴 영역의 평균 깊이 계산
            depth_roi = depth_image[y:y+h, x:x+w]
            depth_roi = depth_roi[depth_roi > 0]  # 유효한 깊이값만
            
            if len(depth_roi) > 0:
                avg_depth = np.median(depth_roi) / 1000.0  # 미터 단위로 변환
                
                if avg_depth < self.depth_threshold:
                    print(f"👤 얼굴 감지! 거리: {avg_depth:.2f}m")
                    return True, color_image, (x, y, w, h)
        
        return False, None, None
    
    def analyze_face(self, image, face_coords):
        """얼굴 분석 (나이, 성별)"""
        try:
            x, y, w, h = face_coords
            # 얼굴 영역 추출 (여유 공간 추가)
            margin = 20
            face_img = image[
                max(0, y-margin):min(image.shape[0], y+h+margin), 
                max(0, x-margin):min(image.shape[1], x+w+margin)
            ]
            
            # DeepFace로 분석 (한국인 얼굴에 좋은 성능)
            # enforce_detection=False로 설정하여 감지 실패 시에도 진행
            result = DeepFace.analyze(
                face_img, 
                actions=['age', 'gender'],
                enforce_detection=False,
                detector_backend='opencv',  # 가벼운 opencv 사용
                silent=True
            )
            
            # 결과가 리스트인 경우 첫 번째 요소 사용
            if isinstance(result, list):
                result = result[0]
            
            age = result['age']
            gender = result['dominant_gender']
            
            # 성별을 한국어로 변환
            gender_kr = '남성' if gender == 'Man' else '여성'
            
            analysis_result = {
                'age': int(age),
                'gender': gender_kr,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print(f"📊 분석 결과: {analysis_result}")
            return analysis_result
            
        except Exception as e:
            print(f"❌ 얼굴 분석 실패: {e}")
            return None
    
    def run_detection_loop(self):
        """메인 감지 루프"""
        print("🔄 감지 루프 시작...")
        
        while True:
            try:
                depth_image, color_image = self.get_frames()
                
                if depth_image is None or color_image is None:
                    time.sleep(0.1)
                    continue
                
                # 쿨다운 체크
                current_time = time.time()
                if current_time - self.last_detection_time < self.cooldown_period:
                    time.sleep(0.1)
                    continue
                
                # 일정 거리 내 얼굴 감지
                face_in_range, face_image, face_coords = self.detect_face_in_range(
                    depth_image, color_image
                )

                # ===== 🔽 여기부터 추가 =====
                display_image = color_image.copy()

                # 얼굴 박스 그리기
                if face_in_range and face_coords:
                    x, y, w, h = face_coords
                    cv2.rectangle(display_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(
                        display_image,
                        "Face Detected",
                        (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

                # 상태 텍스트
                status_text = "Analyzing..." if self.is_analyzing else "Running"
                cv2.putText(
                    display_image,
                    status_text,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255) if self.is_analyzing else (255, 255, 255),
                    2
                )

                cv2.imshow("RealSense Face Monitor", display_image)

                # q 키로 종료
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                # ===== 🔼 여기까지 =====
                
                if face_in_range and not self.is_analyzing:
                    # 얼굴 감지 시작
                    if not self.face_detected:
                        self.face_detected = True
                        self.face_detected_time = current_time
                        print("👤 얼굴 감지 시작...")
                    
                    # 1초 이상 감지되면 분석 시작
                    if current_time - self.face_detected_time >= 1.0:
                        print("⏳ 1초 이상 감지됨! 분석 시작...")
                        self.is_analyzing = True
                        self.last_detection_time = current_time
                        
                        # 얼굴 분석
                        analysis = self.analyze_face(face_image, face_coords)
                        
                        if analysis:
                            self.latest_analysis = analysis
                            print("✅ 분석 완료! 결과 저장됨")
                        
                        self.is_analyzing = False
                        # face_detected는 그대로 유지 (얼굴이 계속 있는 한)
                
                elif not face_in_range:
                    # 얼굴이 감지되지 않으면 초기화
                    if self.face_detected:
                        print("❌ 얼굴 감지 중단")
                    self.face_detected = False
                    self.face_detected_time = 0
                
                time.sleep(0.1)  # CPU 사용량 감소
                
            except Exception as e:
                print(f"⚠️ 감지 루프 오류: {e}")
                self.face_detected = False
                time.sleep(1)
    
    def stop(self):
        """카메라 종료"""
        if self.pipeline:
            self.pipeline.stop()
            print("🛑 카메라 종료")
    
    def get_latest_analysis(self):
        """최신 분석 결과 반환"""
        return self.latest_analysis
    
    def clear_analysis(self):
        """분석 데이터 초기화"""
        self.latest_analysis = None
        print("🗑️ 분석 데이터 초기화됨")
    
    def get_status(self):
        """현재 시스템 상태 반환"""
        return {
            'status': 'running',
            'is_analyzing': self.is_analyzing,
            'face_detected': self.face_detected,
            'has_data': self.latest_analysis is not None,
            'depth_threshold': self.depth_threshold,
            'cooldown_period': self.cooldown_period
        }