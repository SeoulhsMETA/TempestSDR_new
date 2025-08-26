"""
신호 처리(DSP) 전용 모듈: FFT/PSD 계산과 피크 검출.

이 레이어는 하드웨어/GUI와 독립적이므로 단위 테스트가 쉽습니다.
입력은 넘파이 배열, 출력은 넘파이 배열로 통일합니다.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class SpectrumConfig:
	fft_size: int = 8192


class SpectrumAnalyzer:
	"""신호 → 윈도우 → FFT → PSD → 피크 검출 파이프라인.

	메서드 개요:
	- compute_psd(samples): PSD(dB) 계산
	- build_freq_axis(Fs): 주파수 축 생성
	- find_topk_peaks(psd, k): 상위 k개 피크 인덱스/값
	"""

	def __init__(self, config: SpectrumConfig | None = None) -> None:
		self.config = config or SpectrumConfig()

	def compute_psd(self, samples: np.ndarray) -> np.ndarray:
		"""창 함수 적용 후 FFT하고 dB 스케일 PSD를 반환합니다."""
		win = np.hanning(len(samples))
		spec = np.fft.fftshift(np.fft.fft(samples * win))
		psd = 20 * np.log10(np.abs(spec) / np.sqrt(len(samples)) + 1e-12)
		return psd

	def build_freq_axis(self, sample_rate_hz: float) -> np.ndarray:
		"""샘플레이트에 맞는 대칭 주파수 축 생성."""
		return np.linspace(-sample_rate_hz/2, sample_rate_hz/2, self.config.fft_size)

	def find_topk_peaks(self, psd: np.ndarray, k: int = 3):
		"""상위 k개 피크 인덱스와 값 반환."""
		indices = np.argsort(psd)[-k:][::-1]
		return indices, psd[indices]


