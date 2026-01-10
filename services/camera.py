"""
RealSense 카메라 통합 관리 서비스
services/camera.py
"""

import pyrealsense2 as rs
import numpy as np
import threading
import time
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class RealSenseCameraService:
    """RealSense D415 카메라 통합 관리자 (싱글톤)"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.pipeline = None
        self.align = None
        self.running = False
        self.frame_lock = threading.Lock()
        
        # 최신 프레임 저장
        self.latest_color_frame = None
        self.latest_depth_frame = None
        self.latest_color_image = None
        self.latest_depth_image = None
        
        # 구독자 관리
        self.subscribers = []
        
        logger.info("RealSenseCameraService 초기화")
    
    def initialize(self) -> bool:
        """카메라 초기화"""
        if self.running:
            logger.warning("카메라가 이미 실행 중입니다")
            return True
        
        try:
            self.pipeline = rs.pipeline()
            config = rs.config()
            
            # 스트림 설정 (640x480, 30fps)
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
            
            profile = self.pipeline.start(config)
            
            # Depth와 Color 정렬
            align_to = rs.stream.color
            self.align = rs.align(align_to)
            
            # 카메라 워밍업
            logger.info("⏳ 카메라 워밍업 중...")
            for i in range(5):
                try:
                    self.pipeline.wait_for_frames(timeout_ms=2000)
                except:
                    pass
            
            logger.info("✅ RealSense 카메라 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 카메라 초기화 실패: {e}")
            return False
    
    def start(self):
        """프레임 수집 스레드 시작"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._frame_loop, daemon=True)
        self.thread.start()
        logger.info("📹 프레임 수집 시작")
    
    def _frame_loop(self):
        """메인 프레임 수집 루프"""
        while self.running:
            try:
                frames = self.pipeline.wait_for_frames(timeout_ms=1000)
                aligned_frames = self.align.process(frames)
                
                depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()
                
                if not depth_frame or not color_frame:
                    continue
                
                with self.frame_lock:
                    self.latest_depth_frame = depth_frame
                    self.latest_color_frame = color_frame
                    self.latest_depth_image = np.asanyarray(depth_frame.get_data())
                    self.latest_color_image = np.asanyarray(color_frame.get_data())
                
                # 구독자들에게 프레임 전달
                self._notify_subscribers()
                
            except RuntimeError:
                # 타임아웃은 정상적인 상황
                continue
            except Exception as e:
                logger.error(f"프레임 수집 오류: {e}")
                time.sleep(0.1)
    
    def get_frames(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """최신 depth, color 이미지 반환"""
        with self.frame_lock:
            if self.latest_depth_image is None or self.latest_color_image is None:
                return None, None
            return self.latest_depth_image.copy(), self.latest_color_image.copy()
    
    def subscribe(self, callback):
        """프레임 수신 콜백 등록"""
        if callback not in self.subscribers:
            self.subscribers.append(callback)
            logger.info(f"구독자 추가: {callback.__name__}")
    
    def unsubscribe(self, callback):
        """프레임 수신 콜백 제거"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.info(f"구독자 제거: {callback.__name__}")
    
    def _notify_subscribers(self):
        """구독자들에게 새 프레임 알림"""
        with self.frame_lock:
            depth = self.latest_depth_image
            color = self.latest_color_image
        
        for callback in self.subscribers:
            try:
                callback(depth.copy(), color.copy())
            except Exception as e:
                logger.error(f"구독자 콜백 오류: {e}")
    
    def stop(self):
        """카메라 중지"""
        self.running = False
        if self.pipeline:
            self.pipeline.stop()
            logger.info("🛑 RealSense 카메라 중지")
    
    def get_status(self) -> dict:
        """카메라 상태 반환"""
        return {
            'running': self.running,
            'camera_connected': self.pipeline is not None,
            'subscribers_count': len(self.subscribers)
        }
