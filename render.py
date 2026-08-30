"""
코드로 만드는 음악 — 외부 라이브러리 0개, 표준 라이브러리만 사용.
사인파부터 직접 쌓아서 드럼/베이스/코드/멜로디를 합성하고 WAV로 저장한다.

    python render.py

A minor / 120 BPM / 8마디 (Am7 - Fmaj7 - Cmaj7 - G7 x2)
"""

import array
import math
import random
import wave

SR = 44100          # 샘플레이트
BPM = 120
BEAT = 60.0 / BPM   # 4분음표 길이(초) = 0.5
BAR = BEAT * 4      # 한 마디 = 2초
BARS = 8
TAIL = 2.0          # 잔향이 자연스럽게 사라질 여유
DUR = BAR * BARS + TAIL
N = int(DUR * SR)

random.seed(7)      # 매번 같은 결과가 나오도록

# ── 파형 ────────────────────────────────────────────────
def shape(kind, p):
    """p = 위상(0~1이 한 주기)"""
    x = p % 1.0
    if kind == "sine":
        return math.sin(2 * math.pi * x)
    if kind == "saw":
        return 2.0 * x - 1.0
    if kind == "square":
        return 1.0 if x < 0.5 else -1.0
    if kind == "tri":
        return 4.0 * abs(x - 0.5) - 1.0
    if kind == "ep":  # 일렉피아노 느낌: 배음을 섞은 사인
        return (math.sin(2 * math.pi * x)
                + 0.35 * math.sin(4 * math.pi * x)
                + 0.12 * math.sin(6 * math.pi * x)) / 1.47
    raise ValueError(kind)


def midi_to_hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def lowpass(buf, hz):
    """1차 로우패스 — 톱니파의 거친 고음을 깎아준다."""
    k = 1.0 - math.exp(-2.0 * math.pi * hz / SR)
    y = 0.0
    for i, x in enumerate(buf):
        y += (x - y) * k
        buf[i] = y
    return buf


# ── 악기 ────────────────────────────────────────────────
def tone(midi, dur, kind="saw", a=0.005, d=0.12, s=0.7, r=0.25,
         detune=0.0, lpf=None):
    """ADSR 엔벨로프를 씌운 한 음."""
    inc1 = midi_to_hz(midi) / SR
    inc2 = midi_to_hz(midi) * (1.0 + detune) / SR
    n = int((dur + r) * SR)
    out = [0.0] * n
    p1 = p2 = 0.0
    for i in range(n):
        t = i / SR
        if t < a:
            e = t / a                          # attack
        elif t < a + d:
            e = 1.0 + (s - 1.0) * (t - a) / d  # decay
        elif t < dur:
            e = s                              # sustain
        else:
            e = s * max(0.0, 1.0 - (t - dur) / r)  # release
        v = shape(kind, p1)
        if detune:
            v = 0.5 * (v + shape(kind, p2))
        out[i] = v * e
        p1 += inc1
        p2 += inc2
    return lowpass(out, lpf) if lpf else out


def kick(dur=0.45):
    n = int(dur * SR)
    out = [0.0] * n
    p = 0.0
    for i in range(n):
        t = i / SR
        f = 45.0 + 95.0 * math.exp(-t * 38.0)      # 피치가 뚝 떨어지는 것이 킥의 정체
        p += f / SR
        out[i] = (math.sin(2 * math.pi * p) * math.exp(-t * 7.0)
                  + random.uniform(-1, 1) * 0.35 * math.exp(-t * 400.0))
    return out


def snare(dur=0.28):
    n = int(dur * SR)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        out[i] = (random.uniform(-1, 1) * math.exp(-t * 19.0)
                  + 0.45 * math.sin(2 * math.pi * 185 * t) * math.exp(-t * 24.0))
    return out


def hat(dur=0.07):
    n = int(dur * SR)
    out = [0.0] * n
    prev = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        out[i] = (x - prev) * 0.5 * math.exp(-t * 55.0)  # 차분 = 하이패스
        prev = x
    return out


# ── 믹서 ────────────────────────────────────────────────
left = [0.0] * N
right = [0.0] * N


def place(samples, at, gain=1.0, pan=0.5):
    """at(초) 위치에 samples를 좌우로 나눠 더한다. pan 0=왼쪽 1=오른쪽"""
    i0 = int(at * SR)
    gl = gain * math.sqrt(1.0 - pan)
    gr = gain * math.sqrt(pan)
    for i, v in enumerate(samples):
        j = i0 + i
        if j >= N:
            break
        left[j] += v * gl
        right[j] += v * gr


# ── 악보 ────────────────────────────────────────────────
BASS = [33, 29, 36, 31]                       # A1  F1  C2  G1
CHORDS = [[57, 60, 64, 67],                   # Am7
          [53, 57, 60, 64],                   # Fmaj7
          [52, 55, 59, 64],                   # Cmaj7
          [50, 55, 59, 65]]                   # G7

MINOR = [0, 2, 3, 5, 7, 8, 10]                # A 내추럴 마이너


def deg(nth):
    """스케일 자리번호 -> MIDI 번호 (0 = A4)"""
    return 69 + 12 * (nth // 7) + MINOR[nth % 7]


#  8분음표 8개 = 한 마디. None은 쉼표.
MELODY = [
    [None] * 8,
    [None] * 8,
    [4, 2, 4, 7, None, 6, 4, None],
    [2, 4, 2, 0, None, None, 1, 2],
    [4, 6, 7, 9, None, 7, 6, None],
    [7, 6, 4, 2, None, None, None, None],
    [4, 2, 4, 7, None, 9, 7, None],
    [6, 4, 2, 0, None, None, None, None],
]

for bar in range(BARS):
    t0 = bar * BAR
    ch = bar % 4

    # 드럼 — 킥은 1·3박, 스네어는 2·4박, 하이햇은 8분음표
    for b in (0, 2):
        place(kick(), t0 + b * BEAT, 0.85, 0.5)
    if bar >= 1:
        for b in (1, 3):
            place(snare(), t0 + b * BEAT, 0.42, 0.5)
    for i in range(8):
        place(hat(), t0 + i * BEAT / 2, 0.30 if i % 2 == 0 else 0.20, 0.58)

    # 베이스 — 근음을 8분음표로 통통 튀게
    for i, hold in enumerate([0.45, 0.20, 0.45, 0.20]):
        place(tone(BASS[ch], hold * BEAT * 2, "saw", a=0.004, d=0.10,
                   s=0.55, r=0.08, lpf=1100),
              t0 + i * BEAT, 0.55, 0.5)

    # 코드 — 한 마디 내내 깔아둔다 (살짝 아르페지오로 흩뿌려서)
    for i, m in enumerate(CHORDS[ch]):
        place(tone(m, BAR * 0.85, "ep", a=0.01, d=0.9, s=0.25, r=0.6),
              t0 + i * 0.012, 0.16, 0.35 + 0.1 * i)

    # 멜로디
    for i, nth in enumerate(MELODY[bar]):
        if nth is None:
            continue
        place(tone(deg(nth), BEAT * 0.42, "square", a=0.006, d=0.09,
                   s=0.55, r=0.22, detune=0.006, lpf=2600),
              t0 + i * BEAT / 2, 0.20, 0.62)


# ── 리버브 (간이 Schroeder) ─────────────────────────────
def reverb(buf, mix=0.22):
    combs = [(1531, 0.80), (1789, 0.77), (2003, 0.74), (2251, 0.71)]
    wet = [0.0] * N
    for delay, fb in combs:
        line = [0.0] * delay
        idx = 0
        for i in range(N):
            v = line[idx]
            wet[i] += v * 0.25
            line[idx] = buf[i] + v * fb
            idx = (idx + 1) % delay
    for i in range(N):
        buf[i] = buf[i] * (1.0 - mix) + wet[i] * mix
    return buf


print("리버브 처리 중...")
reverb(left)
reverb(right)

# ── 노멀라이즈 + 소프트 클리핑 → WAV ────────────────────
peak = max(max(abs(v) for v in left), max(abs(v) for v in right)) or 1.0
norm = 0.89 / peak

frames = array.array("h")
for i in range(N):
    for v in (left[i], right[i]):
        frames.append(int(math.tanh(v * norm) * 32000))

OUT = "song.wav"
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(frames.tobytes())

print(f"완성: {OUT}  ({DUR:.1f}초, {BPM} BPM)")
