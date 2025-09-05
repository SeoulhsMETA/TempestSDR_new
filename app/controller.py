from __future__ import annotations

"""
오케스트레이션(Controller) 모듈.

역할:
- 하드웨어 장치 초기화/설정
- 주기적으로 샘플 읽기 → DSP로 PSD 계산 → UI에 반영
- UI에서 중심 주파수 변경 이벤트를 받아 장치에 적용
"""

import numpy as np

from hardware.sdr_device import RtlSdrDevice
from dsp.spectrum import SpectrumAnalyzer, SpectrumConfig
from ui.viewer import SpectrumViewer


class SDRController:
	"""장치 <-> DSP <-> UI를 연결하고 주기적으로 업데이트합니다."""

	def __init__(
		self,
		center_freq_hz: float,
		sample_rate_hz: float,
		gain_db: str | float = "auto",
	) -> None:
		self.center_freq_hz = center_freq_hz
		self.sample_rate_hz = sample_rate_hz
		self.gain_db = gain_db

		self.device = RtlSdrDevice()
		self.spec = SpectrumAnalyzer(SpectrumConfig(fft_size=8192))

		self.viewer = SpectrumViewer(
			sample_rate_hz=self.sample_rate_hz,
			center_freq_hz=self.center_freq_hz,
			fft_size=self.spec.config.fft_size,
		)
		self.viewer.set_on_apply_center(self._apply_center_from_ui)
		self.viewer.set_on_apply_resolution(self._apply_resolution_from_ui)
		self.target_resolution = (1920, 1080)





	def _apply_center_from_ui(self, new_center_hz: float) -> None:
		"""UI에서 변경된 중심 주파수를 장치에 반영."""
		self.center_freq_hz = new_center_hz
		if self.device.is_open:
			self.device.center_freq = self.center_freq_hz






	def _apply_resolution_from_ui(self, wh: tuple[int, int]) -> None:
		"""실험 대상 화면 해상도(W,H) 변경을 저장.

		현재 파이프라인은 해상도값을 표시/로그 등에 활용할 수 있습니다.
		나중에 해상도 기반 후처리를 추가하기 쉬운 구조입니다.
		"""
		self.target_resolution = wh





	def start(self) -> None:
		"""장치를 초기화하고 애니메이션 루프를 시작."""
		# 장치 초기화
		self.device.open()
		self.device.sample_rate = self.sample_rate_hz
		self.device.center_freq = self.center_freq_hz
		self.device.gain = (
			"auto" if isinstance(self.gain_db, str) and self.gain_db.lower() == "auto"
			else float(self.gain_db)
		)

		# 메인 루프: matplotlib 애니메이션 없이 간단한 타이머 기반 업데이트로도 충분하지만
		# 기존 구조를 최대한 유지하기 위해 draw-idle 갱신만 사용한다.
		import matplotlib.animation as animation



		def _tick(_frame):
			"""주기 호출: 샘플 읽기 → PSD 계산 → 화면 반영."""
			samples = self.device.read_samples(self.spec.config.fft_size)
			psd = self.spec.compute_psd(samples)
			peaks_idx, peaks_val = self.spec.find_topk_peaks(psd, k=3)
			freq_axis = self.viewer.freq_axis
			peak_freqs = freq_axis[peaks_idx]
			power = float(np.mean(np.abs(samples)**2))
			power_db = 10 * np.log10(power + 1e-12)
			info_text = (
				f"중심 주파수: {self.center_freq_hz/1e6:.3f} MHz\n"
				f"샘플링 레이트: {self.sample_rate_hz/1e6:.2f} Msps\n"
				f"평균 전력: {power_db:.2f} dBFS\n"
				f"상위 피크:\n"
			)



			info_text += f"해상도: {self.target_resolution[0]}x{self.target_resolution[1]}\n"
			for i, (f, p) in enumerate(zip(peak_freqs, peaks_val)):
				info_text += f"  {i+1}. {f/1e3:+.1f} kHz ({p:.1f} dB)\n"
			self.viewer.update(psd, info_text)
			return []

            

		self._ani = animation.FuncAnimation(
			self.viewer.fig,
			_tick,
			interval=100,
			blit=False,
			cache_frame_data=False,
		)
		self.viewer.show()

	def close(self) -> None:
		self.device.close()