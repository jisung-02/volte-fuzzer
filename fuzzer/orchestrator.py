import os
import json
import time
from datetime import datetime
from typing import Dict, List
import yaml

from .xml_generator import SIPpXMLGenerator
from .sipp_runner import SIPpRunner
from .adb_monitor import ADBMonitor

class FuzzingOrchestrator:
    """VoLTE SIP 퍼징 오케스트레이터"""
    
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.sipp_runner = SIPpRunner(
            self.config['target']['ip'],
            self.config['target']['port']
        )
        
        self.adb_monitor = ADBMonitor(
            self.config.get('android', {}).get('device_id')
        )
        
        self.results = []
        self.crashes = []
    
    def run_baseline_test(self) -> Dict:
        """기본 REGISTER 시나리오 실행 (변조 없음)"""
        print('[*] Running baseline REGISTER test (no fuzzing)')
        
        template_path = self.config['fuzzing']['template']
        print(f'[*] Using template: {template_path}')
        
        # ADB 모니터링 시작 (옵션)
        if self.config.get('android', {}).get('enabled', False):
            print('[*] Starting ADB monitoring...')
            
            logcat_file = os.path.join(
                self.config['output']['logcat_dir'],
                f'logcat_baseline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
            
            self.adb_monitor.register_callback(self._on_crash_detected)
            self.adb_monitor.start_monitoring(logcat_file)
            time.sleep(2)
        
        # 기본 시나리오 실행
        print('[*] Executing baseline scenario...')
        result = self.sipp_runner.run_scenario(
            scenario_file=template_path,
            auth_file=self.config['authentication']['csv_file'],
            timeout=self.config['fuzzing']['timeout']
        )
        
        # 결과 출력
        print('\n' + '='*60)
        print('BASELINE TEST RESULT')
        print('='*60)
        print(f'Success: {result["success"]}')
        print(f'Exit Code: {result["exit_code"]}')
        print(f'Duration: {result["duration"]:.2f}s')
        print(f'Timeout: {result["timeout"]}')
        
        if result['stdout']:
            print('\n--- STDOUT ---')
            print(result['stdout'][:1000])
        
        if result['stderr']:
            print('\n--- STDERR ---')
            print(result['stderr'][:1000])
        
        print('='*60)
        
        # ADB 모니터링 중지
        if self.config.get('android', {}).get('enabled', False):
            time.sleep(2)  # 로그 수집 대기
            print('\n[*] Stopping ADB monitoring...')
            self.adb_monitor.stop_monitoring()
            
            if self.crashes:
                print(f'[!] Crashes detected during baseline test: {len(self.crashes)}')
                for crash in self.crashes:
                    print(f'    - {crash["pattern_name"]}: {crash["log_line"][:80]}...')
        
        # 결과 저장
        baseline_result = {
            'test_type': 'baseline',
            'timestamp': datetime.now().isoformat(),
            'scenario': template_path,
            'result': result,
            'crashes': self.crashes
        }
        
        output_file = os.path.join(
            self.config['output']['base_dir'],
            f'baseline_result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        
        with open(output_file, 'w') as f:
            json.dump(baseline_result, f, indent=2, default=str)
        
        print(f'\n[*] Baseline result saved to: {output_file}')
        
        return baseline_result
        
    def run_fuzzing_campaign(self) -> None:
        """퍼징 캠페인 실행"""
        print('[*] Starting VoLTE SIP Fuzzing Campaign')
        print(f'[*] Target: {self.config["target"]["ip"]}:{self.config["target"]["port"]}')
        
        # 1. 템플릿 로드
        template_path = self.config['fuzzing']['template']
        print(f'[*] Loading template: {template_path}')
        
        # 2. 퍼징 변형 생성
        print('[*] Generating fuzz variations...')
        generator = SIPpXMLGenerator(template_path)
        
        fuzz_scenarios = generator.generate_fuzz_variations(
            base_name='volte_register',
            output_dir=self.config['output']['scenarios_dir'],
            count=self.config['fuzzing']['iterations']
        )
        
        print(f'[*] Generated {len(fuzz_scenarios)} fuzz scenarios')
        
        # 3. ADB 모니터링 시작
        if self.config.get('android', {}).get('enabled', False):
            print('[*] Starting ADB monitoring...')
            
            logcat_file = os.path.join(
                self.config['output']['logcat_dir'],
                f'logcat_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            )
            
            self.adb_monitor.register_callback(self._on_crash_detected)
            self.adb_monitor.start_monitoring(logcat_file)
            time.sleep(2)  # 모니터링 안정화 대기
        
        # 4. 각 시나리오 실행
        print('[*] Running fuzz scenarios...')
        
        for i, scenario in enumerate(fuzz_scenarios):
            print(f'\n[{i+1}/{len(fuzz_scenarios)}] Testing: {os.path.basename(scenario)}')
            
            test_start = datetime.now()
            
            # SIPp 실행
            result = self.sipp_runner.run_scenario(
                scenario_file=scenario,
                auth_file=self.config['authentication']['csv_file'],
                timeout=self.config['fuzzing']['timeout']
            )
            
            test_end = datetime.now()
            
            # 결과 기록
            test_result = {
                'scenario': scenario,
                'timestamp': test_start.isoformat(),
                'duration': result['duration'],
                'success': result['success'],
                'exit_code': result['exit_code'],
                'timeout': result['timeout'],
                'stdout': result['stdout'][:500],  # 일부만 저장
                'stderr': result['stderr'][:500],
            }
            
            self.results.append(test_result)
            
            # 크래시 여부 확인
            if result['exit_code'] != 0 or result['timeout']:
                print(f'  [!] Potential issue detected (exit_code: {result['exit_code']})')
                self._save_crash_case(scenario, test_result)
            
            # 안정화 대기
            time.sleep(self.config['fuzzing']['delay_between_tests'])
        
        # 5. ADB 모니터링 중지
        if self.config.get('android', {}).get('enabled', False):
            print('\n[*] Stopping ADB monitoring...')
            self.adb_monitor.stop_monitoring()
        
        # 6. 결과 저장
        self._save_results()
        
        print(f'\n[*] Fuzzing campaign completed')
        print(f'[*] Total tests: {len(self.results)}')
        print(f'[*] Crashes detected: {len(self.crashes)}')
    
    def _on_crash_detected(self, match_result: Dict) -> None:
        """크래시 탐지 콜백"""
        print(f'\n[!!!] CRASH DETECTED: {match_result["pattern_name"]}')
        print(f'      Severity: {match_result["severity"]}')
        print(f'      Log: {match_result["log_line"][:100]}...')
        
        self.crashes.append(match_result)
    
    def _save_crash_case(self, scenario: str, result: Dict) -> None:
        """크래시 케이스 저장 (재현 가능하도록)"""
        crash_dir = self.config['output']['crashes_dir']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        crash_case = {
            'scenario_file': scenario,
            'timestamp': timestamp,
            'result': result,
            'crashes': [c for c in self.crashes if c['timestamp'] > result['timestamp']]
        }
        
        # JSON 저장
        crash_file = os.path.join(crash_dir, f'crash_{timestamp}.json')
        with open(crash_file, 'w') as f:
            json.dump(crash_case, f, indent=2, default=str)
        
        # 시나리오 파일 복사
        import shutil
        shutil.copy(scenario, os.path.join(crash_dir, f'crash_{timestamp}.xml'))
    
    def _save_results(self) -> None:
        """전체 결과 저장"""
        output_file = os.path.join(
            self.config['output']['base_dir'],
            f'fuzzing_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
        
        summary = {
            'config': self.config,
            'total_tests': len(self.results),
            'crashes': len(self.crashes),
            'results': self.results,
            'crash_details': self.crashes
        }
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f'[*] Results saved to: {output_file}')