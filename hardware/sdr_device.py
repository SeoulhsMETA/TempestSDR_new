"""
RTL-SDR 하드웨어 액세스를 담당하는 얇은 래퍼 모듈.

역할 분리 개요:
- 이 레이어는 '하드웨어 의존' 코드만 포함합니다.
- 상위 레이어(DSP, UI)는 이 모듈의 인터페이스만 사용하여
  실제 장치 종류가 바뀌어도 변경 영향을 최소화합니다.
"""

import typing as _t

try:
	from rtlsdr import RtlSdr  # type: ignore
except Exception as _e:  # pragma: no cover - 런타임 환경에 따라 달라질 수 있음
	RtlSdr = None  # 지연 로딩/에러 메시지는 실제 사용 시 처리


class RtlSdrDevice:
	"""
	RTL-SDR 장치에 대한 얇은 래퍼.

	- 수명주기: open()으로 연결하고 close()로 해제
	- 설정 값: sample_rate, center_freq, gain 속성으로 접근/설정
	- 데이터 획득: read_samples(n)으로 n개 샘플 읽기

	상위 레이어는 이 클래스의 공용 API만 사용합니다.
	"""

	def __init__(self) -> None:
		self._dev = None


		

	def open(self) -> None:
		"""장치를 초기화하여 연결합니다."""
		if RtlSdr is None:
			raise RuntimeError("pyrtlsdr가 설치되어 있는지 확인하세요 (pip install pyrtlsdr)")
		self._dev = RtlSdr()

	@property
	def is_open(self) -> bool:
		"""장치가 열려 있는지 여부."""
		return self._dev is not None





	@property
	def sample_rate(self) -> float:
		"""현재 샘플링 레이트(Hz)."""
		return float(self._dev.sample_rate)  # type: ignore[union-attr]

	@sample_rate.setter
	def sample_rate(self, value: float) -> None:
		"""샘플링 레이트(Hz)를 설정."""
		self._dev.sample_rate = float(value)  # type: ignore[union-attr]





	@property
	def center_freq(self) -> float:
		"""현재 중심 주파수(Hz)."""
		return float(self._dev.center_freq)  # type: ignore[union-attr]

	@center_freq.setter
	def center_freq(self, value: float) -> None:
		"""중심 주파수(Hz)를 설정."""
		self._dev.center_freq = float(value)  # type: ignore[union-attr]





	@property
	def gain(self) -> _t.Union[float, str]:
		"""이득(dB) 또는 'auto'."""
		return self._dev.gain  # type: ignore[union-attr]

	@gain.setter
	def gain(self, value: _t.Union[float, str]) -> None:
		"""이득을 설정."""
		self._dev.gain = value  # type: ignore[union-attr]






	def read_samples(self, n: int):
		"""n개 샘플을 복소수 배열로 반환합니다."""
		if self._dev is None:
			raise RuntimeError("장치가 열려있지 않습니다. open()을 먼저 호출하세요.")
		return self._dev.read_samples(n)




	def close(self) -> None:
		"""장치 연결을 해제합니다."""
		if self._dev is not None:
			self._dev.close()
			self._dev = None


