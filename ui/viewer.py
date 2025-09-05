from __future__ import annotations

"""
시각화(UI) 모듈: Figure/Axes 생성, 위젯, 화면 갱신 담당.

이 레이어는 화면 표시만 책임지며, 하드웨어/연산 로직은 알지 않습니다.
컨트롤러가 전달해주는 psd/텍스트만 받아 그립니다.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import TextBox, Button


class SpectrumViewer:
	"""Figure/Axes/위젯 생성과 화면 업데이트를 담당.

	핵심 역할:
	- 초기 Figure/Axes 구성
	- Center MHz 입력 TextBox + Apply 버튼 제공
	- update(psd, info_text)로 화면 갱신
	"""

	def __init__(self, sample_rate_hz: float, center_freq_hz: float, fft_size: int) -> None:
		self.sample_rate_hz = sample_rate_hz
		self.center_freq_hz = center_freq_hz
		self.fft_size = fft_size

		plt.rcParams['font.family'] = 'Malgun Gothic'
		plt.rcParams['axes.unicode_minus'] = False
		plt.rcParams['font.size'] = 10

		self.fig, (self.ax_spectrum, self.ax_info) = plt.subplots(
			2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]}
		)
		self.fig.subplots_adjust(bottom=0.18)
		# 스펙트럼 표시 관련 상수/상태는 사용 전에 먼저 정의
		self.LINE_WIDTH = 0.2                        # 스펙트럼 선 굵기
		self.DEFAULT_YLIM = (-80, 0)                 # 기본 Y축 범위(dB)
		self.DEFAULT_LINE_OFFSET_DB = 0.0            # Reset 시 복원 오프셋(dB)
		self.CURRENT_LINE_OFFSET_DB = -5.0           # 표시용 오프셋(dB, 음수면 아래로)
		self._spectrum_y_offset_db = self.CURRENT_LINE_OFFSET_DB
		self._default_y_offset_db = self.DEFAULT_LINE_OFFSET_DB
		self._set_title()

		self.ax_spectrum.set_title('실시간 주파수 스펙트럼 (FFT)')
		self.ax_spectrum.set_xlabel('주파수 오프셋 (Hz)')
		self.ax_spectrum.set_ylabel('신호 세기 (dB)')
		self.ax_spectrum.grid(True, alpha=0.3)
		self.ax_spectrum.set_ylim(*self.DEFAULT_YLIM)
		self._default_ylim = self.DEFAULT_YLIM

		self.ax_info.axis('off')

		# 스펙트럼 X축 생성
		self.freq_axis = np.linspace(
			-self.sample_rate_hz / 2,
			self.sample_rate_hz / 2,
			self.fft_size,
		)

		# 스펙트럼 선 초기화 (선 굵기: self.LINE_WIDTH)
		self.line_spectrum, = self.ax_spectrum.plot(
			self.freq_axis,
			np.zeros(self.fft_size),
			"b-",
			linewidth=self.LINE_WIDTH,
		)


		self.text_info = self.ax_info.text(
			0.02, 0.8, '', transform=self.ax_info.transAxes,
			fontsize=10, verticalalignment='top',
			bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8)
		)

		plt.tight_layout()

		# 위젯 위치 상수(figure 좌표): 한 곳에서 관리하면 가독성과 유지보수가 쉬움
		self.UI_POS = {
			'res':   [0.40, 0.04, 0.25, 0.06],  # 해상도 입력칸 위치
			'center': [0.67, 0.04, 0.25, 0.06],  # Center MHz 입력칸 위치
			'apply': [0.94, 0.04, 0.08, 0.06],  # Apply 버튼 위치
			'reset': [0.85, 0.04, 0.07, 0.06],  # Reset 버튼 위치
		}

		# 입력 위젯: Target Resolution (WxH) - 오른쪽으로 이동
		ax_res = self.fig.add_axes(self.UI_POS['res'])
		self.res_box = TextBox(ax_res, 'Res WxH: ', initial="1920x1080")


		# 입력 위젯: Center MHz - 더 오른쪽으로 이동
		ax_box = self.fig.add_axes(self.UI_POS['center'])
		self.center_box = TextBox(ax_box, 'Center MHz: ', initial=f"{self.center_freq_hz/1e6:.3f}")
		ax_btn = self.fig.add_axes(self.UI_POS['apply'])
		self.apply_button = Button(ax_btn, 'Apply')


		# Reset 버튼: 뷰 복원 - 위치 조정
		ax_reset = self.fig.add_axes(self.UI_POS['reset'])
		self.reset_button = Button(ax_reset, 'Reset')

		self._on_apply_center: callable | None = None
		self.center_box.on_submit(self._submit_center)
		self.apply_button.on_clicked(lambda _evt: self._submit_center(self.center_box.text))
		self.res_box.on_submit(self._submit_resolution)
		self.reset_button.on_clicked(self._on_reset_view)

	def _set_title(self) -> None:
		"""윈도우 제목을 현재 중심 주파수로 갱신."""
		self.fig.suptitle(
			f'SDR 실시간 스펙트럼 분석기\n중심 주파수: {self.center_freq_hz/1e6:.3f} MHz',
			fontsize=14, fontweight='bold'
		)

	def set_on_apply_center(self, handler: callable) -> None:
		"""외부(컨트롤러)에서 전달된 콜백을 저장."""
		self._on_apply_center = handler

	def set_on_apply_resolution(self, handler: callable) -> None:
		"""해상도 변경 콜백 저장 (WxH)."""
		self._on_apply_resolution = handler

	def _submit_center(self, text: str) -> None:
		"""입력값(MHz)을 검증/반영하고 콜백으로 알려줌."""
		try:
			mhz = float(text)
			self.center_freq_hz = mhz * 1e6
			if self._on_apply_center:
				self._on_apply_center(self.center_freq_hz)
			self._set_title()
			self.fig.canvas.draw_idle()
		except Exception:
			self.center_box.set_val(f"{self.center_freq_hz/1e6:.3f}")


	def _submit_resolution(self, text: str) -> None:
		"""'1920x1080' 또는 '1920 1080' 형태를 파싱하여 콜백에 전달."""
		try:
			clean = text.lower().replace(' ', 'x').replace('*', 'x')
			w_str, h_str = [t for t in clean.split('x') if t][:2]
			w, h = int(w_str), int(h_str)
			if self._on_apply_resolution:
				self._on_apply_resolution((w, h))
		except Exception:
			# 형식 오류 시 기본값으로 되돌림
			self.res_box.set_val("1920x1080")

	def _on_reset_view(self, _evt) -> None:
		"""축 범위와 선 오프셋을 기본 상태로 복원."""
		self.ax_spectrum.set_ylim(*self.DEFAULT_YLIM)
		self._spectrum_y_offset_db = self._default_y_offset_db
		self.fig.canvas.draw_idle()

	def update(self, psd: np.ndarray, info_text: str) -> None:
		"""스펙트럼 선과 정보 텍스트를 최신 값으로 갱신."""
		# 그래프 박스는 그대로 두고, 선만 dB 오프셋을 적용해 하향 이동
		self.line_spectrum.set_ydata(psd + self._spectrum_y_offset_db)
		self.text_info.set_text(info_text)
		self.fig.canvas.draw_idle()

	def show(self) -> None:
		plt.show()


