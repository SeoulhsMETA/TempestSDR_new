"""
실행 엔트리 포인트.

이 파일은 프로그램 시작과 종료만 책임집니다.
핵심 구현은 다음 모듈로 분리되어 있습니다.
- hardware/: 하드웨어 접근 (RTL-SDR 래퍼)
- dsp/: 신호 처리 (FFT/PSD/피크)
- ui/: 시각화와 입력 위젯
- app/: 컨트롤러(오케스트레이션)
"""

import sys
from app.controller import SDRController


# ============================================================================
# 프로그램 실행 조건
# ============================================================================
# 이 파일을 직접 실행할 때만 실행됩니다. 모듈로 임포트되면 실행되지 않습니다.
if __name__ == "__main__":
	center_freq_hz = float(sys.argv[1]) if len(sys.argv) > 1 else 99.9e6
	sample_rate_hz = float(sys.argv[2]) if len(sys.argv) > 2 else 2.4e6
	gain_db = sys.argv[3] if len(sys.argv) > 3 else "auto"

	controller = SDRController(center_freq_hz, sample_rate_hz, gain_db)
	try:
		controller.start()
	except KeyboardInterrupt:
		print("\n사용자에 의해 중단되었습니다.")
	finally:
		controller.close()
