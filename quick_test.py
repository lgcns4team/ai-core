"""
간단한 웹캠 테스트
quick_test.py

웹캠이 작동하는지 빠르게 확인합니다.
"""

import cv2
import sys

def quick_test(camera_index=1):
    """빠른 웹캠 테스트"""
    print(f"카메라 {camera_index} 테스트 중...")
    
    cap = cv2.VideoCapture(camera_index)
    
    if not cap.isOpened():
        print(f"❌ 카메라 {camera_index}를 열 수 없습니다.")
        print("\n다른 인덱스 시도:")
        
        # 0~4까지 빠르게 테스트
        for i in range(5):
            test_cap = cv2.VideoCapture(i)
            status = "✅ 작동" if test_cap.isOpened() else "❌ 없음"
            print(f"   카메라 {i}: {status}")
            test_cap.release()
        
        return False
    
    print(f"✅ 카메라 {camera_index} 열림!")
    
    # 해상도 확인
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"해상도: {width}x{height}")
    
    # 프레임 읽기
    ret, frame = cap.read()
    if ret:
        print(f"✅ 프레임 읽기 성공!")
        print(f"프레임 크기: {frame.shape}")
        
        # 창에 표시 (5초간)
        print("\n카메라 화면을 5초간 표시합니다...")
        print("ESC 키를 누르면 종료됩니다.")
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < 5:
            ret, frame = cap.read()
            if ret:
                # 화면에 텍스트 표시
                cv2.putText(frame, f"Camera {camera_index} - Press ESC to exit", 
                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                          0.7, (0, 255, 0), 2)
                
                cv2.imshow(f'Webcam Test - Camera {camera_index}', frame)
                
                # ESC 키로 종료
                if cv2.waitKey(1) & 0xFF == 27:
                    break
        
        cv2.destroyAllWindows()
        print("✅ 테스트 완료!")
        
    else:
        print("❌ 프레임 읽기 실패")
    
    cap.release()
    return ret

if __name__ == "__main__":
    # 명령행 인자로 카메라 인덱스 받기
    camera_index = 1
    if len(sys.argv) > 1:
        try:
            camera_index = int(sys.argv[1])
        except:
            pass
    
    print("=" * 60)
    print("🎥 웹캠 빠른 테스트")
    print("=" * 60)
    print(f"사용법: python quick_test.py [카메라_인덱스]")
    print(f"예시: python quick_test.py 1")
    print("=" * 60 + "\n")
    
    success = quick_test(camera_index)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ 카메라가 정상적으로 작동합니다!")
        print("=" * 60)
        print(f"\n.env 파일에 설정:")
        print(f"GESTURE_CAMERA_INDEX={camera_index}")
    else:
        print("\n" + "=" * 60)
        print("❌ 카메라 활성화 실패")
        print("=" * 60)
        print("\n해결 방법:")
        print("1. 다른 인덱스 시도:")
        print("   python quick_test.py 0")
        print("   python quick_test.py 2")
        print("2. 카메라 연결 확인")
        print("3. 다른 프로그램에서 카메라 사용 중인지 확인")
        print("4. macOS: 시스템 설정 > 개인정보 보호 > 카메라 권한")