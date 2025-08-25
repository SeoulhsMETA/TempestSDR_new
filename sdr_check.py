import sys
import time
import numpy as np

try:
	from rtlsdr import RtlSdr
except Exception as e:
	print("pyrtlsdr가 설치되어 있는지 확인하세요: pip install -r requirements.txt", file=sys.stderr)
	raise


def main():
	# 기본 설정: FM 라디오 대역 (예: 99.9 MHz)
	center_freq_hz = float(sys.argv[1]) if len(sys.argv) > 1 else 99.9e6
	sample_rate_hz = float(sys.argv[2]) if len(sys.argv) > 2 else 2.4e6
	gain_db = sys.argv[3] if len(sys.argv) > 3 else "auto"  # "auto" 또는 숫자(dB)
	num_samples = int(sys.argv[4]) if len(sys.argv) > 4 else 256*1024

	print(f"Center: {center_freq_hz/1e6:.3f} MHz, Fs: {sample_rate_hz/1e6:.2f} Msps, Gain: {gain_db}")

	sdr = RtlSdr()
	try:
		# 하드웨어 초기화 및 설정
		sdr.sample_rate = sample_rate_hz
		sdr.center_freq = center_freq_hz
		if isinstance(gain_db, str) and gain_db.lower() == "auto":
			sdr.gain = 'auto'
		else:
			sdr.gain = float(gain_db)

		# V3: 다이렉트 샘플링(AM/HF) 모드 테스트를 원하면 주석 해제
		# sdr.set_direct_sampling(2)  # 0: off, 1: I-branch, 2: Q-branch(HF)
		# sdr.set_offset_tuning(True)  # LO 누설 저감

		# 캡처
		print("캡처 중...", flush=True)
		start = time.time()
		samples = sdr.read_samples(num_samples)
		dur = time.time() - start

		# 통계
		power = np.mean(np.abs(samples)**2)
		mean_i = np.mean(np.real(samples))
		mean_q = np.mean(np.imag(samples))
		std_i = np.std(np.real(samples))
		std_q = np.std(np.imag(samples))

		print(f"수신 샘플: {len(samples)}개, 소요: {dur*1000:.1f} ms (~{len(samples)/dur/1e6:.2f} MSa/s 실효)")
		print(f"평균 전력: {10*np.log10(power+1e-12):.2f} dBFS")
		print(f"I(mean/std): {mean_i:.4f}/{std_i:.4f}, Q(mean/std): {mean_q:.4f}/{std_q:.4f}")

		# 간단한 스펙트럼 프린트(상위 N bin)
		N = 8192 if len(samples) >= 8192 else int(2 ** np.floor(np.log2(len(samples))))
		if N >= 1024:
			win = np.hanning(N)
			spec = np.fft.fftshift(np.fft.fft(samples[:N] * win))
			psd = 20*np.log10(np.abs(spec)/np.sqrt(N) + 1e-12)
			psd_db = psd - np.max(psd)
			# 상위 피크 5개
			peaks_idx = np.argsort(psd_db)[-5:][::-1]
			bin_hz = sample_rate_hz / N
			print("상위 피크 (상대 dB, 주파수 오프셋 Hz):")
			for idx in peaks_idx:
				offset_hz = (idx - N/2) * bin_hz
				print(f"  {psd_db[idx]:6.1f} dB @ {offset_hz:,.0f} Hz")
		else:
			print("샘플 수가 적어 스펙트럼 생략")

	finally:
		sdr.close()


if __name__ == "__main__":
	main()


	
