시나리오 1: USB로 연결된 실제 Android 단말bash# Ubuntu 머신에서

# 1. ADB 설치 확인
which adb
# 없으면 설치:
sudo apt-get update
sudo apt-get install -y adb

# 2. Android 단말 USB 연결

# 3. 단말에서 USB 디버깅 활성화
# Settings → Developer Options → USB Debugging ON

# 4. 연결 확인
adb devices

# 출력 예시:
# List of devices attached
# RF8M802XXXXXX    device퍼징 프레임워크 실행:
yaml# config/fuzzing_config.yaml
android:
  enabled: true
  device_id: "RF8M802XXXXXX"  # adb devices 출력 결과

-----
cd ~/volte_test/volte-fuzzer

# 1. ADB 연결 확인
adb devices

# 2. 로그캣 실시간 테스트
adb logcat -v threadtime *:V | grep -i "ims\|volte\|sip"

# 3. 퍼징 프레임워크 실행
python main.py --iterations 10

# 4. 결과 확인
ls -lh output/crashes/
cat output/logcat/logcat_*.log | grep -i "fatal\|crash"