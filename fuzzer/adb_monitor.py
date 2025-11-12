import subprocess
import threading
import queue
import re
from typing import List, Dict, Optional, Callable
from datetime import datetime

class ADBMonitor:
    """Android ADB logcat 실시간 모니터링 및 패턴 매칭"""
    
    def __init__(self, device_id: Optional[str] = None):
        self.device_id = device_id
        self.process: Optional[subprocess.Popen] = None
        self.log_queue = queue.Queue()
        self.monitoring = False
        self.crash_patterns = self._load_crash_patterns()
        self.callbacks = []
        
    def _load_crash_patterns(self) -> List[Dict]:
        """크래시 탐지 패턴 정의"""
        return [
            {
                'name': 'Native Crash',
                'pattern': re.compile(r'.*FATAL EXCEPTION.*|.*Fatal signal.*|.*SIGSEGV.*'),
                'severity': 'critical'
            },
            {
                'name': 'ANR',
                'pattern': re.compile(r'.*ANR in.*|.*Application Not Responding.*'),
                'severity': 'high'
            },
            {
                'name': 'IMS Error',
                'pattern': re.compile(r'.*ImsService.*error.*|.*VoLTE.*fail.*', re.IGNORECASE),
                'severity': 'medium'
            },
            {
                'name': 'SIP Error',
                'pattern': re.compile(r'.*SIP.*40[0-9].*|.*SIP.*50[0-9].*'),
                'severity': 'medium'
            },
            {
                'name': 'Segfault',
                'pattern': re.compile(r'.*segmentation fault.*|.*SIGSEGV.*', re.IGNORECASE),
                'severity': 'critical'
            },
            {
                'name': 'Buffer Overflow',
                'pattern': re.compile(r'.*buffer overflow.*|.*stack smashing.*', re.IGNORECASE),
                'severity': 'critical'
            },
        ]
    
    def start_monitoring(self, output_file: Optional[str] = None) -> None:
        """Logcat 모니터링 시작"""
        cmd = ['adb']
        
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        
        # 기존 로그 클리어
        subprocess.run(cmd + ['logcat', '-c'], capture_output=True)
        
        # Logcat 시작
        cmd.extend([
            'logcat',
            '-v', 'threadtime',  # 타임스탬프 포함
            '*:V'  # 모든 로그 레벨
        ])
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        self.monitoring = True
        
        # 로그 읽기 스레드 시작
        self.reader_thread = threading.Thread(
            target=self._read_logs,
            args=(output_file,),
            daemon=True
        )
        self.reader_thread.start()
        
        # 패턴 매칭 스레드 시작
        self.matcher_thread = threading.Thread(
            target=self._match_patterns,
            daemon=True
        )
        self.matcher_thread.start()
    
    def _read_logs(self, output_file: Optional[str]) -> None:
        """로그 읽기 스레드"""
        file_handle = None
        
        if output_file:
            file_handle = open(output_file, 'w', buffering=1)
        
        try:
            for line in iter(self.process.stdout.readline, ''):
                if not self.monitoring:
                    break
                
                # 큐에 추가
                self.log_queue.put({
                    'timestamp': datetime.now(),
                    'line': line.strip()
                })
                
                # 파일에 기록
                if file_handle:
                    file_handle.write(line)
                    
        finally:
            if file_handle:
                file_handle.close()
    
    def _match_patterns(self) -> None:
        """패턴 매칭 스레드"""
        while self.monitoring:
            try:
                log_entry = self.log_queue.get(timeout=0.1)
                line = log_entry['line']
                
                # 각 패턴과 매칭
                for pattern_def in self.crash_patterns:
                    if pattern_def['pattern'].search(line):
                        match_result = {
                            'timestamp': log_entry['timestamp'],
                            'pattern_name': pattern_def['name'],
                            'severity': pattern_def['severity'],
                            'log_line': line
                        }
                        
                        # 콜백 실행
                        for callback in self.callbacks:
                            callback(match_result)
                            
            except queue.Empty:
                continue
            except Exception as e:
                print(f'Pattern matching error: {e}')
    
    def register_callback(self, callback: Callable) -> None:
        """크래시 탐지 콜백 등록"""
        self.callbacks.append(callback)
    
    def stop_monitoring(self) -> None:
        """모니터링 중지"""
        self.monitoring = False
        
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
    
    def get_logs_between(self, start_time: datetime, end_time: datetime) -> List[str]:
        """특정 시간 범위의 로그 추출"""
        # 실제 구현에서는 로그를 버퍼에 저장하고 시간 기반 필터링
        pass
    
    def search_pattern(self, pattern: str, log_file: str) -> List[Dict]:
        """로그 파일에서 패턴 검색"""
        results = []
        regex = re.compile(pattern, re.IGNORECASE)
        
        with open(log_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if regex.search(line):
                    results.append({
                        'line_number': line_num,
                        'content': line.strip()
                    })
        
        return results