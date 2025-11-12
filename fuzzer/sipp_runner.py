import subprocess
import time
from typing import Optional, Dict, List
import signal
import os

class SIPpRunner:
    """SIPp 실행 및 관리"""
    
    def __init__(self, target_ip: str, target_port: int = 5060):
        self.target_ip = target_ip
        self.target_port = target_port
        self.process: Optional[subprocess.Popen] = None
        self.output = []
        self.error = []
        
    def run_scenario(
        self,
        scenario_file: str,
        auth_file: Optional[str] = None,
        timeout: int = 30,
        trace: bool = True
    ) -> Dict:
        """SIPp 시나리오 실행
        
        Returns:
            {
                'success': bool,
                'stdout': str,
                'stderr': str,
                'exit_code': int,
                'duration': float,
                'timeout': bool
            }
        """
        cmd = [
            'docker', 'exec', '-i', 'sipp-test',
            'sipp', f'{self.target_ip}:{self.target_port}',
            '-sf', scenario_file,
            '-m', '1',  # 1번만 실행
            '-l', '1',  # 동시 호 1개
        ]
        
        if auth_file:
            cmd.extend(['-inf', auth_file])
        
        if trace:
            cmd.extend([
                '-trace_msg',
                '-trace_err',
                '-message_file', f'/workspace/output/logs/sipp_{int(time.time())}_msg.log',
                '-error_file', f'/workspace/output/logs/sipp_{int(time.time())}_err.log'
            ])
        
        start_time = time.time()
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid  # 프로세스 그룹 생성
            )
            
            # 타임아웃 적용
            stdout, stderr = self.process.communicate(timeout=timeout)
            
            duration = time.time() - start_time
            
            return {
                'success': self.process.returncode == 0,
                'stdout': stdout,
                'stderr': stderr,
                'exit_code': self.process.returncode,
                'duration': duration,
                'timeout': False
            }
            
        except subprocess.TimeoutExpired:
            # 타임아웃 시 프로세스 강제 종료
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            time.sleep(1)
            
            if self.process.poll() is None:
                os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Timeout',
                'exit_code': -1,
                'duration': timeout,
                'timeout': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'exit_code': -1,
                'duration': time.time() - start_time,
                'timeout': False
            }
    
    def run_batch(self, scenario_files: List[str], auth_file: str) -> List[Dict]:
        """여러 시나리오 배치 실행"""
        results = []
        
        for i, scenario in enumerate(scenario_files):
            print(f'[{i+1}/{len(scenario_files)}] Running {os.path.basename(scenario)}...')
            
            result = self.run_scenario(scenario, auth_file)
            result['scenario_file'] = scenario
            results.append(result)
            
            # 네트워크 안정화를 위한 대기
            time.sleep(2)
        
        return results
