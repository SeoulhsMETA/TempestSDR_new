# ============================================================================
# SDR 실시간 스펙트럼 분석기 - 초보자를 위한 상세 주석 버전
# ============================================================================
# 이 프로그램은 RTL-SDR 하드웨어를 사용해서 라디오 신호를 실시간으로 분석합니다.
# 
# 프로그램의 전체 동작 흐름:
# 1. SDR 하드웨어 연결 및 초기화
# 2. GUI 창 생성 (그래프 2개: 스펙트럼 + 정보)
# 3. 실시간으로 신호를 받아서 FFT 분석
# 4. 결과를 그래프에 실시간 업데이트
# ============================================================================

import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.patches as patches
from matplotlib.widgets import TextBox, Button

# RTL-SDR 라이브러리 import 시도
# 이 라이브러리는 실제 SDR 하드웨어와 통신하는 역할을 합니다
try:
	from rtlsdr import RtlSdr
except Exception as e:
	print("pyrtlsdr가 설치되어 있는지 확인하세요: pip install -r requirements.txt", file=sys.stderr)
	raise


class SDRSpectrumAnalyzer:
	"""
	SDR 스펙트럼 분석기의 메인 클래스
	이 클래스는 SDR 하드웨어 제어, GUI 생성, 실시간 분석을 모두 담당합니다
	"""
	
	def __init__(self, center_freq_hz=99.9e6, sample_rate_hz=2.4e6, gain_db="auto"):
		"""
		초기화 함수 - 프로그램 시작 시 한 번만 실행됩니다
		
		매개변수 설명:
		- center_freq_hz: 듣고 싶은 주파수 (기본값: 99.9MHz = FM 라디오)
		- sample_rate_hz: 초당 샘플 수 (기본값: 2.4MHz = 240만개/초)
		- gain_db: 신호 증폭 정도 (기본값: "auto" = 자동)
		"""
		# 사용자가 설정한 값들을 저장
		self.center_freq_hz = center_freq_hz
		self.sample_rate_hz = sample_rate_hz
		self.gain_db = gain_db
		
		# SDR 하드웨어 객체 (아직 연결되지 않음)
		self.sdr = None
		
		# FFT 분석을 위한 샘플 개수 (8192개 = 2^13개)
		# FFT는 신호를 주파수별로 분해하는 수학적 기법입니다
		self.fft_size = 8192
		
		# GUI 창을 생성하고 설정합니다
		# 이 함수가 실행되면 화면에 그래프 창이 나타납니다
		self.setup_gui()
		
	def setup_gui(self):
		"""
		GUI 초기화 및 설정 함수
		이 함수는 matplotlib을 사용해서 사용자가 볼 그래프 창을 만듭니다
		"""
		# 그래프의 글꼴과 크기를 설정합니다
		plt.rcParams['font.family'] = 'Malgun Gothic'  # 기존 'DejaVu Sans' 대신
		plt.rcParams['axes.unicode_minus'] = False    # 폰트 잘되는지 확인하기.
		plt.rcParams['font.size'] = 10
		
		# 메인 윈도우를 생성합니다
		# 2개의 그래프를 세로로 배치: 위쪽은 스펙트럼, 아래쪽은 정보
		self.fig, (self.ax_spectrum, self.ax_info) = plt.subplots(2, 1, figsize=(12, 8), 
																   gridspec_kw={'height_ratios': [3, 1]})
		# 아래쪽에 입력 위젯을 놓을 공간을 조금 확보합니다
		self.fig.subplots_adjust(bottom=0.18)
		
		# 창의 제목을 설정합니다
		self.fig.suptitle(f'SDR 실시간 스펙트럼 분석기\n중심 주파수: {self.center_freq_hz/1e6:.3f} MHz', 
						 fontsize=14, fontweight='bold')
		
		# ===== 위쪽 그래프 (스펙트럼 분석) 설정 =====
		self.ax_spectrum.set_title('실시간 주파수 스펙트럼 (FFT)')
		self.ax_spectrum.set_xlabel('주파수 오프셋 (Hz)')  # X축: 중심 주파수에서 얼마나 떨어졌는지
		self.ax_spectrum.set_ylabel('신호 세기 (dB)')      # Y축: 신호가 얼마나 강한지
		self.ax_spectrum.grid(True, alpha=0.3)            # 격자 표시 (투명도 30%)
		self.ax_spectrum.set_ylim(-80, 0)                 # Y축 범위: -80dB ~ 0dB
		
		# ===== 아래쪽 그래프 (정보 표시) 설정 =====
		self.ax_info.axis('off')  # 축을 숨깁니다 (텍스트만 표시할 예정)
		
		# 주파수 축을 생성합니다
		# 중심 주파수를 0으로 하고, 양쪽으로 ±1.2MHz 범위
		# 예: 99.9MHz가 중심이면 98.7MHz ~ 101.1MHz 범위를 보여줍니다
		self.freq_axis = np.linspace(-self.sample_rate_hz/2, self.sample_rate_hz/2, self.fft_size)
		
		# 스펙트럼을 그릴 선을 초기화합니다 (처음에는 0으로 시작)
		self.line_spectrum, = self.ax_spectrum.plot(self.freq_axis, np.zeros(self.fft_size), 'b-', linewidth=1)
		
		# 정보를 표시할 텍스트 박스를 생성합니다
		# 위치: 왼쪽 위, 파란색 배경, 둥근 모서리
		self.text_info = self.ax_info.text(0.02, 0.8, '', transform=self.ax_info.transAxes, 
										  fontsize=10, verticalalignment='top',
										  bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
		
		# 그래프 레이아웃을 자동으로 조정합니다
		plt.tight_layout()
		
		# ===== 사용자 입력 위젯: 중심 주파수(MHz) 설정 =====
		# TextBox와 Button은 figure 좌표(0~1)로 위치를 지정합니다
		ax_box = self.fig.add_axes([0.12, 0.04, 0.25, 0.06])
		self.center_box = TextBox(ax_box, 'Center MHz: ', initial=f"{self.center_freq_hz/1e6:.3f}")
		
		ax_btn = self.fig.add_axes([0.39, 0.04, 0.10, 0.06])
		self.apply_button = Button(ax_btn, 'Apply')
		
		# Enter로 제출하거나 버튼을 클릭하면 동일한 핸들러를 사용합니다
		self.center_box.on_submit(self._on_apply_center_freq)
		self.apply_button.on_clicked(lambda _evt: self._on_apply_center_freq(self.center_box.text))

	def _on_apply_center_freq(self, text):
		"""TextBox/버튼으로 입력된 중심 주파수(MHz)를 적용하는 핸들러"""
		try:
			new_center_mhz = float(text)
			new_center_hz = new_center_mhz * 1e6
			self.center_freq_hz = new_center_hz
			# 하드웨어가 초기화되어 있으면 즉시 반영
			if self.sdr is not None:
				self.sdr.center_freq = self.center_freq_hz
			# 제목 업데이트
			self.fig.suptitle(f'SDR 실시간 스펙트럼 분석기\n중심 주파수: {self.center_freq_hz/1e6:.3f} MHz', 
							 fontsize=14, fontweight='bold')
			self.fig.canvas.draw_idle()
		except Exception as _:
			# 숫자 변환 실패 시, 입력 상자를 기존 값으로 복원
			self.center_box.set_val(f"{self.center_freq_hz/1e6:.3f}")
		
	def init_sdr(self):
		"""
		SDR 하드웨어 초기화 함수
		이 함수는 실제 SDR 장치에 연결하고 설정을 적용합니다
		"""
		try:
			# RTL-SDR 장치에 연결을 시도합니다
			self.sdr = RtlSdr()
			
			# SDR 장치의 설정을 변경합니다
			self.sdr.sample_rate = self.sample_rate_hz  # 샘플링 속도 설정
			self.sdr.center_freq = self.center_freq_hz  # 듣고 싶은 주파수 설정
			
			# 신호 증폭 설정
			if isinstance(self.gain_db, str) and self.gain_db.lower() == "auto":
				self.sdr.gain = 'auto'  # 자동으로 최적의 증폭을 찾습니다
			else:
				self.sdr.gain = float(self.gain_db)  # 사용자가 지정한 값으로 설정
				
			print(f"SDR 초기화 완료: {self.center_freq_hz/1e6:.3f} MHz, {self.sample_rate_hz/1e6:.2f} Msps")
			return True
		except Exception as e:
			print(f"SDR 초기화 실패: {e}")
			return False
	
	def update_spectrum(self, frame):
		"""
		실시간 스펙트럼 업데이트 함수
		이 함수는 matplotlib 애니메이션에 의해 주기적으로 호출됩니다 (100ms마다)
		
		매개변수 frame: 애니메이션 프레임 번호 (사용하지 않음)
		"""
		# SDR이 연결되지 않았다면 아무것도 하지 않습니다
		if self.sdr is None:
			return self.line_spectrum,
		
		try:
			# ===== 1단계: SDR에서 실제 신호 데이터를 읽어옵니다 =====
			samples = self.sdr.read_samples(self.fft_size)  # 8192개의 복소수 샘플
			
			# ===== 2단계: FFT 분석으로 주파수 스펙트럼을 계산합니다 =====
			# Hanning 윈도우를 적용해서 스펙트럼 누출을 줄입니다
			win = np.hanning(len(samples))
			# FFT 계산 후 주파수 순서를 재배열 (음수 주파수를 왼쪽으로)
			spec = np.fft.fftshift(np.fft.fft(samples * win))
			# 전력 스펙트럼 밀도(PSD)를 dB 단위로 변환
			psd = 20 * np.log10(np.abs(spec) / np.sqrt(len(samples)) + 1e-12)
			
			# ===== 3단계: 그래프를 업데이트합니다 =====
			self.line_spectrum.set_ydata(psd)  # 스펙트럼 선의 Y값을 새로운 데이터로 교체
			
			# ===== 4단계: 정보 텍스트를 업데이트합니다 =====
			# 전체 신호의 평균 전력을 계산합니다
			power = np.mean(np.abs(samples)**2)
			power_db = 10 * np.log10(power + 1e-12)
			
			# 가장 강한 신호 3개를 찾습니다 (피크 검출)
			peaks_idx = np.argsort(psd)[-3:][::-1]  # 내림차순으로 정렬
			peak_freqs = self.freq_axis[peaks_idx]   # 피크 주파수들
			peak_powers = psd[peaks_idx]             # 피크 전력들
			
			# 정보 텍스트를 구성합니다
			info_text = f"중심 주파수: {self.center_freq_hz/1e6:.3f} MHz\n"
			info_text += f"샘플링 레이트: {self.sample_rate_hz/1e6:.2f} Msps\n"
			info_text += f"평균 전력: {power_db:.2f} dBFS\n"
			info_text += f"상위 피크:\n"
			for i, (freq, power) in enumerate(zip(peak_freqs, peak_powers)):
				info_text += f"  {i+1}. {freq/1e3:+.1f} kHz ({power:.1f} dB)\n"
			
			# 텍스트 박스의 내용을 업데이트합니다
			self.text_info.set_text(info_text)
			
			# 애니메이션에 업데이트된 객체들을 반환합니다
			return self.line_spectrum, self.text_info
			
		except Exception as e:
			print(f"스펙트럼 업데이트 오류: {e}")
			return self.line_spectrum, self.text_info
	
	def start_analysis(self):
		"""
		실시간 분석을 시작하는 함수
		이 함수가 호출되면 GUI 창이 나타나고 실시간 분석이 시작됩니다
		"""
		# SDR 하드웨어를 초기화합니다
		if not self.init_sdr():
			return
		
		# matplotlib 애니메이션을 시작합니다
		# update_spectrum 함수를 100ms마다 호출해서 실시간 업데이트
		self.ani = FuncAnimation(self.fig, self.update_spectrum, interval=100, 
								blit=True, cache_frame_data=False)
		
		# GUI 창을 화면에 표시합니다
		plt.show()
	
	def cleanup(self):
		"""
		리소스 정리 함수
		프로그램 종료 시 SDR 연결을 안전하게 끊습니다
		"""
		if self.sdr:
			self.sdr.close()


def main():
	"""
	메인 함수 - 프로그램의 시작점
	명령줄 인수를 처리하고 SDR 분석기를 시작합니다
	"""
	# 명령줄 인수를 처리합니다 (기본값 제공)
	# 사용법: python sdr_check.py [주파수_MHz] [샘플링레이트_MHz] [증폭_dB]
	center_freq_hz = float(sys.argv[1]) if len(sys.argv) > 1 else 99.9e6
	sample_rate_hz = float(sys.argv[2]) if len(sys.argv) > 2 else 2.4e6
	gain_db = sys.argv[3] if len(sys.argv) > 3 else "auto"

	print(f"Center: {center_freq_hz/1e6:.3f} MHz, Fs: {sample_rate_hz/1e6:.2f} Msps, Gain: {gain_db}")
	print("실시간 스펙트럼 분석기를 시작합니다...")

	# SDR 스펙트럼 분석기 객체를 생성합니다
	analyzer = SDRSpectrumAnalyzer(center_freq_hz, sample_rate_hz, gain_db)
	
	try:
		# 분석을 시작합니다 (GUI 창이 나타남)
		analyzer.start_analysis()
	except KeyboardInterrupt:
		# Ctrl+C로 프로그램을 중단한 경우
		print("\n사용자에 의해 중단되었습니다.")
	finally:
		# 프로그램 종료 시 리소스를 정리합니다
		analyzer.cleanup()


# ============================================================================
# 프로그램 실행 조건
# ============================================================================
# 이 파일을 직접 실행할 때만 main() 함수를 호출합니다
# 다른 파일에서 import할 때는 main()이 실행되지 않습니다
if __name__ == "__main__":
	main()
