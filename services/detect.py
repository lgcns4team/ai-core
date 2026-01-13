import pyrealsense2 as rs
import numpy as np
import cv2
import time
from deepface import DeepFace
import warnings
from services.camera import RealSenseCameraService

warnings.filterwarnings('ignore')

class DepthFaceAnalyzer:
    """Intel RealSense D415 카메라를 이용한 깊이 기반 얼굴 분석기"""
    
    def __init__(self):
        self.camera = RealSenseCameraService()  # 싱글톤 인스턴스
        self.latest_analysis = None
        self.is_analyzing = False
        self.face_detected = False
        self.face_detected_time = 0
        self.depth_threshold = 1.5
        self.last_detection_time = 0
        self.cooldown_period = 3
        
        # 프레임 저장용
        self.current_depth = None
        self.current_color = None
        
    def initialize_camera(self) -> bool:
        """D415 카메라 초기화"""
        success = self.camera.initialize()
        if success:
            self.camera.start()
            # 프레임 수신 콜백 등록
            self.camera.subscribe(self._on_frame_received)
        return success
    
    def _on_frame_received(self, depth_image, color_image):
        """카메라 서비스로부터 프레임 수신"""
        self.current_depth = depth_image
        self.current_color = color_image
    
    def get_frames(self):
        """카메라에서 프레임 가져오기 (카메라 서비스 사용)"""
        return self.current_depth, self.current_color
    
    def detect_face_in_range(self, depth_image, color_image):
        """일정 거리 내 얼굴 감지"""
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        for (x, y, w, h) in faces:
            center_x = x + w // 2
            center_y = y + h // 2
            
            depth_roi = depth_image[y:y+h, x:x+w]
            depth_roi = depth_roi[depth_roi > 0]
            
            if len(depth_roi) > 0:
                avg_depth = np.median(depth_roi) / 1000.0
                
                if avg_depth < self.depth_threshold:
                    print(f"👤 얼굴 감지! 거리: {avg_depth:.2f}m")
                    return True, color_image, (x, y, w, h)
        
        return False, None, None
    
    def analyze_face(self, image, face_coords):
        """얼굴 분석 (나이, 성별)"""
        try:
            x, y, w, h = face_coords
            margin = 20
            face_img = image[
                max(0, y-margin):min(image.shape[0], y+h+margin), 
                max(0, x-margin):min(image.shape[1], x+w+margin)
            ]
            
            result = DeepFace.analyze(
                face_img, 
                actions=['age', 'gender'],
                enforce_detection=False,
                detector_backend='opencv',
                silent=True
            )
            
            if isinstance(result, list):
                result = result[0]
            
            age = result['age']
            gender = result['dominant_gender']
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
                
                current_time = time.time()
                if current_time - self.last_detection_time < self.cooldown_period:
                    time.sleep(0.1)
                    continue
                
                face_in_range, face_image, face_coords = self.detect_face_in_range(
                    depth_image, color_image
                )

                display_image = color_image.copy()

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

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                if face_in_range and not self.is_analyzing:
                    if not self.face_detected:
                        self.face_detected = True
                        self.face_detected_time = current_time
                        print("👤 얼굴 감지 시작...")
                    
                    if current_time - self.face_detected_time >= 1.0:
                        print("⏳ 1초 이상 감지됨! 분석 시작...")
                        self.is_analyzing = True
                        self.last_detection_time = current_time
                        
                        analysis = self.analyze_face(face_image, face_coords)
                        
                        if analysis:
                            self.latest_analysis = analysis
                            print("✅ 분석 완료! 결과 저장됨")
                        
                        self.is_analyzing = False
                
                elif not face_in_range:
                    if self.face_detected:
                        print("❌ 얼굴 감지 중단")
                    self.face_detected = False
                    self.face_detected_time = 0
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"⚠️ 감지 루프 오류: {e}")
                self.face_detected = False
                time.sleep(1)
    
    def stop(self):
        """카메라 종료"""
        self.camera.unsubscribe(self._on_frame_received)
        print("🛑 얼굴 분석 서비스 종료")
    
    def get_latest_analysis(self):
        """최신 분석 결과 반환"""
        return self.latest_analysis
    
    def clear_analysis(self):
        """분석 데이터 초기화"""
        self.latest_analysis = None
        print("🗑️ 분석 데이터 초기화됨")
    
    def get_status(self):
        """현재 시스템 상태 반환"""
        camera_status = self.camera.get_status()
        return {
            'status': 'running',
            'is_running': camera_status['running'],
            'camera_connected': camera_status['camera_connected'],
            'is_analyzing': self.is_analyzing,
            'face_detected': self.face_detected,
            'has_data': self.latest_analysis is not None,
            'depth_threshold': self.depth_threshold,
            'cooldown_period': self.cooldown_period
        }
