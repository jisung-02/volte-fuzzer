import argparse
import os
from fuzzer.orchestrator import FuzzingOrchestrator

def main():
    parser = argparse.ArgumentParser(description='VoLTE SIP Fuzzing Framework')
    parser.add_argument('--config', default='config/fuzzing_config.yaml',
                       help='Fuzzing configuration file')
    parser.add_argument('--template', help='SIPp XML template override')
    parser.add_argument('--iterations', type=int, help='Number of iterations')
    
    args = parser.parse_args()
    
    # 출력 디렉토리 생성
    os.makedirs('output/scenarios', exist_ok=True)
    os.makedirs('output/logs', exist_ok=True)
    os.makedirs('output/logcat', exist_ok=True)
    os.makedirs('output/crashes', exist_ok=True)
    
    # 오케스트레이터 실행
    orchestrator = FuzzingOrchestrator(args.config)
    orchestrator.run_fuzzing_campaign()

if __name__ == '__main__':
    main()