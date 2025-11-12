# main.py

import argparse
import os
from fuzzer.orchestrator import FuzzingOrchestrator

def main():
    parser = argparse.ArgumentParser(
        description='VoLTE SIP Fuzzing Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 기본 REGISTER 테스트 (변조 없음)
  python main.py --baseline
  
  # 퍼징 캠페인 실행 (변조된 패킷)
  python main.py --fuzz --iterations 100
  
  # 커스텀 설정으로 퍼징
  python main.py --fuzz --config my_config.yaml --iterations 500
        """
    )
    
    # 모드 선택
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--baseline', action='store_true',
                           help='Run baseline REGISTER test without fuzzing')
    mode_group.add_argument('--fuzz', action='store_true',
                           help='Run fuzzing campaign with mutated packets')
    
    # 공통 옵션
    parser.add_argument('--config', default='config/fuzzing_config.yaml',
                       help='Fuzzing configuration file (default: config/fuzzing_config.yaml)')
    
    # 퍼징 전용 옵션
    parser.add_argument('--iterations', type=int,
                       help='Number of fuzzing iterations (overrides config)')
    parser.add_argument('--template',
                       help='SIPp XML template override')
    
    args = parser.parse_args()
    
    # 출력 디렉토리 생성
    os.makedirs('output/scenarios', exist_ok=True)
    os.makedirs('output/logs', exist_ok=True)
    os.makedirs('output/logcat', exist_ok=True)
    os.makedirs('output/crashes', exist_ok=True)
    
    # 오케스트레이터 생성
    orchestrator = FuzzingOrchestrator(args.config)
    
    # 설정 오버라이드
    if args.iterations:
        orchestrator.config['fuzzing']['iterations'] = args.iterations
    if args.template:
        orchestrator.config['fuzzing']['template'] = args.template
    
    # 모드에 따라 실행
    if args.baseline:
        print('\n🔹 MODE: BASELINE TEST (No Fuzzing)')
        orchestrator.run_baseline_test()
    
    elif args.fuzz:
        print('\n🔸 MODE: FUZZING CAMPAIGN')
        orchestrator.run_fuzzing_campaign()

if __name__ == '__main__':
    main()