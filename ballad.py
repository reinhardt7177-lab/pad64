"""
감성 팝 발라드 — 코드로 쓴 1분 30초짜리 곡.
외부 라이브러리 없이 표준 라이브러리만으로 신디사이저부터 직접 만든다.

    python ballad.py        ->  ballad.wav

조성   : B minor
진행   : Bm - G - D - A  (감성 발라드의 그 진행)
템포   : 74 BPM
구성   : 인트로 4 / 벌스 8 / 프리코러스 4 / 코러스 8 / 아웃트로 4 = 28마디
"""

import array
import math
import random
import wave

# ══ 기본 설정 ══════════════════════════════════════════
SR = 44100
BPM = 74
BEAT = 60.0 / BPM          # 4분음표 = 0.811초
BAR = BEAT * 4             # 한 마디 = 3.243초
SLOT = BEAT / 2            # 8분음표 = 악보의 최소 단위
BARS = 28
TAIL = 4.5                 # 마지막 잔향이 사라질 시간
DUR = BAR * BARS + TAIL
N = int(DUR * SR)

random.seed(20260813)

TWO_PI = 2.0 * math.pi


def hz(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def lowpass(buf, cutoff, poles=2):
    """1차 로우패스를 여러 번 걸어 기울기를 급하게 만든다."""
    k = 1.0 - math.exp(-TWO_PI * cutoff / SR)
    for _ in range(poles):
        y = 0.0
        for i, x in enumerate(buf):
            y += (x - y) * k
            buf[i] = y
    return buf


def fade_tail(buf, sec=0.06):
    """뚝 끊기는 소리(클릭)를 막기 위해 끝을 짧게 줄인다."""
    n = min(int(sec * SR), len(buf))
    for i in range(n):
        buf[len(buf) - n + i] *= 1.0 - i / n
    return buf


# ══ 악기 ═══════════════════════════════════════════════
# 같은 음/길이를 매번 다시 계산하면 느리므로 한 번 만든 건 캐싱해서 재사용한다.
_CACHE = {}


def cached(key, build):
    if key not in _CACHE:
        _CACHE[key] = build()
    return _CACHE[key]


# 피아노: 배음마다 세기와 사라지는 속도가 다르다. 이게 피아노 소리의 정체.
#         (배음 번호, 세기, 감쇠 배속)
PARTIALS = [(1, 1.00, 1.00), (2, 0.46, 1.7), (3, 0.24, 2.4),
            (4, 0.12, 3.2), (5, 0.07, 3.9), (7, 0.04, 5.0)]


def _piano(midi, dur):
    f = hz(midi)
    n = int((min(dur, 5.0) + 0.6) * SR)
    out = [0.0] * n
    # 높은 음일수록 빨리 사라진다
    base = 0.85 + max(0, midi - 40) * 0.028
    for k, amp, dk in PARTIALS:
        fk = f * k * (1.0 + 0.0004 * k * k)   # 현의 뻣뻣함(인하모니시티)
        if fk > SR * 0.45:
            continue
        inc = fk / SR
        env = amp
        dmul = math.exp(-base * dk / SR)
        p = 0.0
        for i in range(n):
            out[i] += math.sin(TWO_PI * p) * env
            p += inc
            env *= dmul
    # 해머가 현을 때리는 순간의 잡음
    for i in range(int(0.025 * SR)):
        out[i] += random.uniform(-1, 1) * 0.06 * math.exp(-i / SR * 150.0)
    for i in range(n):
        out[i] *= 0.55
    return fade_tail(out, 0.15)


def piano(midi, dur):
    return cached(("pf", midi, round(dur, 2)), lambda: _piano(midi, dur))


def _pad(midi, dur):
    """디튠한 톱니 세 겹 + 느린 어택 = 뒤를 받쳐주는 패드."""
    f = hz(midi)
    atk, rel = 0.8, 1.6
    n = int((dur + rel) * SR)
    out = [0.0] * n
    for det, w in ((0.9965, 0.9), (1.0, 1.0), (1.0037, 0.9)):
        inc = f * det / SR
        p = random.random()
        for i in range(n):
            p += inc
            out[i] += (2.0 * (p % 1.0) - 1.0) * w
    for i in range(n):
        t = i / SR
        if t < atk:
            e = (t / atk) ** 1.6
        elif t < dur:
            e = 1.0
        else:
            e = max(0.0, 1.0 - (t - dur) / rel) ** 1.4
        out[i] *= e * 0.33
    return fade_tail(lowpass(out, 850))


def pad(midi, dur):
    return cached(("pd", midi, round(dur, 2)), lambda: _pad(midi, dur))


def _bass(midi, dur):
    """사인(무게) + 톱니(윤곽)을 섞은 서브 베이스."""
    f = hz(midi)
    atk, rel = 0.02, 0.30
    n = int((dur + rel) * SR)
    out = [0.0] * n
    inc = f / SR
    p = 0.0
    for i in range(n):
        t = i / SR
        p += inc
        v = math.sin(TWO_PI * p) + 0.30 * (2.0 * (p % 1.0) - 1.0)
        if t < atk:
            e = t / atk
        elif t < dur:
            e = 0.75 + 0.25 * math.exp(-(t - atk) * 3.0)
        else:
            e = 0.75 * max(0.0, 1.0 - (t - dur) / rel)
        out[i] = v * e * 0.6
    return fade_tail(lowpass(out, 380))


def bass(midi, dur):
    return cached(("bs", midi, round(dur, 2)), lambda: _bass(midi, dur))


def _lead(midi, dur):
    """삼각파에 사각파를 섞고 비브라토를 얹은 리드."""
    f = hz(midi)
    atk, dec, sus, rel = 0.06, 0.30, 0.74, 0.55
    n = int((dur + rel) * SR)
    out = [0.0] * n
    p = 0.0
    for i in range(n):
        t = i / SR
        # 소리가 난 뒤 0.3초쯤부터 비브라토가 서서히 들어온다
        depth = 0.0045 * min(1.0, max(0.0, (t - 0.3) / 0.4))
        p += f * (1.0 + depth * math.sin(TWO_PI * 5.3 * t)) / SR
        x = p % 1.0
        v = (4.0 * abs(x - 0.5) - 1.0) * 0.7 + (1.0 if x < 0.5 else -1.0) * 0.3
        if t < atk:
            e = t / atk
        elif t < atk + dec:
            e = 1.0 + (sus - 1.0) * (t - atk) / dec
        elif t < dur:
            e = sus
        else:
            e = sus * max(0.0, 1.0 - (t - dur) / rel) ** 1.5
        out[i] = v * e * 0.5
    return fade_tail(lowpass(out, 2300))


def lead(midi, dur):
    return cached(("ld", midi, round(dur, 2)), lambda: _lead(midi, dur))


# ── 드럼 ────────────────────────────────────────────────
def _kick():
    n = int(0.55 * SR)
    out = [0.0] * n
    p = 0.0
    for i in range(n):
        t = i / SR
        f = 42.0 + 80.0 * math.exp(-t * 30.0)   # 피치 급강하 = 킥의 정체
        p += f / SR
        out[i] = (math.sin(TWO_PI * p) * math.exp(-t * 5.5)
                  + random.uniform(-1, 1) * 0.18 * math.exp(-t * 320.0))
    return fade_tail(out)


def _snare(soft=False):
    n = int((0.45 if soft else 0.30) * SR)
    out = [0.0] * n
    dk = 9.0 if soft else 17.0
    for i in range(n):
        t = i / SR
        out[i] = (random.uniform(-1, 1) * math.exp(-t * dk)
                  + 0.35 * math.sin(TWO_PI * 190 * t) * math.exp(-t * 22.0))
    if soft:                                     # 브러시 느낌으로 고음을 죽인다
        lowpass(out, 3500, poles=1)
    return fade_tail(out)


def _hat(open_=False):
    n = int((0.28 if open_ else 0.06) * SR)
    out = [0.0] * n
    dk = 11.0 if open_ else 60.0
    prev = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        out[i] = (x - prev) * 0.5 * math.exp(-t * dk)   # 차분 = 하이패스
        prev = x
    return fade_tail(out)


def _crash():
    n = int(2.2 * SR)
    out = [0.0] * n
    prev = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        out[i] = (x - prev) * 0.5 * math.exp(-t * 1.7)
        prev = x
    return fade_tail(out, 0.3)


def _riser():
    """코러스 직전에 차오르는 노이즈 스웰."""
    n = int(BAR * SR)
    out = [0.0] * n
    prev = 0.0
    for i in range(n):
        r = i / n
        x = random.uniform(-1, 1)
        out[i] = (x - prev) * 0.5 * (r ** 3)
        prev = x
    lowpass(out, 4000, poles=1)
    return fade_tail(out, 0.05)


KICK = _kick()
SNARE = _snare()
BRUSH = _snare(soft=True)
HAT = _hat()
HATO = _hat(open_=True)
CRASH = _crash()
RISER = _riser()

# ══ 믹서 ═══════════════════════════════════════════════
left = [0.0] * N
right = [0.0] * N


def place(samples, at, gain=1.0, pan=0.5):
    """at(초) 위치에 samples를 좌우로 나눠서 더한다. pan 0=왼쪽 1=오른쪽"""
    i0 = int(at * SR)
    if i0 >= N:
        return
    gl = gain * math.sqrt(1.0 - pan)
    gr = gain * math.sqrt(pan)
    room = N - i0
    for i in range(min(len(samples), room)):
        v = samples[i]
        left[i0 + i] += v * gl
        right[i0 + i] += v * gr


def echo(samples, at, gain, pan, times=2, delay=None, decay=0.42):
    """원음 + 좌우로 튀는 딜레이. 리드를 넓게 들리게 한다."""
    delay = delay or BEAT * 0.75
    place(samples, at, gain, pan)
    g = gain
    for k in range(1, times + 1):
        g *= decay
        place(samples, at + delay * k, g, 1.0 - pan if k % 2 else pan)


# ══ 악보 ═══════════════════════════════════════════════
# 코드: (베이스 근음, 화음 4성부)
CHORD = {
    "Bm":   (35, [59, 62, 66, 69]),   # B  D  F# A
    "G":    (31, [55, 59, 62, 66]),   # G  B  D  F#
    "D":    (38, [57, 62, 66, 69]),   # D/A
    "A":    (33, [57, 61, 64, 69]),   # A  C# E  A
    "Asus": (33, [57, 62, 64, 69]),   # Asus4 — 해결되기 직전의 그 소리
}

#            0     1    2    3  | 인트로
SONG = (["Bm", "G", "D", "A"]
        # 4 ~ 11 | 벌스
        + ["Bm", "G", "D", "A", "Bm", "G", "D", "A"]
        # 12 ~ 15 | 프리코러스
        + ["G", "D", "A", "Asus"]
        # 16 ~ 23 | 코러스
        + ["G", "D", "A", "Bm", "G", "D", "A", "A"]
        # 24 ~ 27 | 아웃트로
        + ["Bm", "G", "D", "Bm"])

INTRO, VERSE, PRE, CHORUS, OUTRO = range(5)
SECTION = ([INTRO] * 4 + [VERSE] * 8 + [PRE] * 4 + [CHORUS] * 8 + [OUTRO] * 4)

# B 내추럴 마이너 스케일
SCALE = [0, 2, 3, 5, 7, 8, 10]


def deg(n):
    """스케일 자리번호 -> MIDI. 0 = B4, 음수도 된다."""
    return 71 + 12 * (n // 7) + SCALE[n % 7]


# 멜로디: {마디: [(시작 8분음표 칸, 자리번호, 길이 칸수), ...]}
MELODY = {
    # 프리코러스 — 조심스럽게 올라간다
    12: [(2, 0, 2), (4, 1, 2), (6, 2, 2)],
    13: [(0, 3, 2), (2, 2, 2), (4, 1, 3)],
    14: [(0, 2, 2), (2, 3, 2), (4, 4, 4)],
    15: [(0, 4, 2), (2, 5, 2), (4, 4, 3)],
    # 코러스 — 여기가 곡의 정점
    16: [(0, 2, 3), (3, 4, 1), (4, 5, 4)],
    17: [(0, 4, 2), (2, 3, 2), (4, 2, 4)],
    18: [(0, 1, 1), (1, 2, 1), (2, 3, 2), (4, 4, 4)],
    19: [(0, 2, 4), (4, 0, 4)],
    20: [(0, 2, 3), (3, 4, 1), (4, 6, 4)],      # 최고음 A5
    21: [(0, 5, 2), (2, 4, 2), (4, 3, 4)],
    22: [(0, 4, 1), (1, 3, 1), (2, 2, 2), (4, 1, 4)],
    23: [(0, 0, 8)],
}

# 피아노 아르페지오 — 화음 4성부 중 몇 번을 칠지, 8분음표 칸마다
ARP_SOFT = [0, 2, 1, 3, 2, 1, 3, 2]
ARP_FULL = [0, 2, 3, 2, 1, 2, 3, 2]

print(f"렌더링 시작 — {BARS}마디 / {DUR:.1f}초")

for bar in range(BARS):
    t0 = bar * BAR
    sec = SECTION[bar]
    root, notes = CHORD[SONG[bar]]
    last = bar == BARS - 1

    # ── 패드 : 곡 전체를 감싸는 이불 ──────────────────
    pad_gain = {INTRO: 0.16, VERSE: 0.20, PRE: 0.26,
                CHORUS: 0.34, OUTRO: 0.22}[sec]
    for i, m in enumerate(notes):
        place(pad(m, BAR * 0.96), t0, pad_gain, 0.18 + 0.21 * i)

    # ── 피아노 ────────────────────────────────────────
    if sec in (CHORUS,) and not last:
        # 코러스에서는 화음을 통째로 짚는다
        for beat in (0, 2):
            for i, m in enumerate(notes):
                place(piano(m, BEAT * 1.9), t0 + beat * BEAT + i * 0.008,
                      0.30, 0.40 + 0.07 * i)
        for i, s in enumerate(ARP_FULL):
            if i % 2:
                place(piano(notes[s] + 12, SLOT * 1.6),
                      t0 + i * SLOT, 0.13, 0.62)
    else:
        arp = ARP_SOFT
        for i, s in enumerate(arp):
            vel = 0.30 if i == 0 else (0.24 if i % 2 == 0 else 0.17)
            place(piano(notes[s], SLOT * 2.2), t0 + i * SLOT, vel,
                  0.36 + 0.05 * (s % 3))
        if sec in (INTRO, OUTRO):
            place(piano(notes[3] + 12, BEAT * 2.4), t0, 0.16, 0.66)

    if last:   # 마지막 마디는 화음을 길게 눌러 마무리
        for i, m in enumerate(notes + [notes[0] - 12]):
            place(piano(m, 4.2), t0 + i * 0.02, 0.34, 0.5)

    # ── 베이스 ────────────────────────────────────────
    if sec == VERSE:
        place(bass(root, BEAT * 2.6), t0, 0.62, 0.5)
        place(bass(root + 12, BEAT * 0.8), t0 + BEAT * 3, 0.34, 0.5)
    elif sec in (PRE, CHORUS):
        for b, hold in ((0, 1.7), (2, 0.85), (3, 0.85)):
            place(bass(root, BEAT * hold), t0 + b * BEAT, 0.66, 0.5)
    elif sec == OUTRO and not last:
        place(bass(root, BEAT * 3.2), t0, 0.50, 0.5)

    # ── 드럼 ──────────────────────────────────────────
    if sec == VERSE:
        place(KICK, t0, 0.60, 0.5)
        place(KICK, t0 + BEAT * 2.5, 0.44, 0.5)
        place(BRUSH, t0 + BEAT * 2, 0.26, 0.5)
        if bar >= 8:                      # 벌스 후반부터 하이햇 등장
            for i in range(8):
                place(HAT, t0 + i * SLOT, 0.16 if i % 2 == 0 else 0.10, 0.60)

    elif sec == PRE:
        place(KICK, t0, 0.62, 0.5)
        place(KICK, t0 + BEAT * 2.5, 0.48, 0.5)
        place(SNARE, t0 + BEAT * 2, 0.30, 0.5)
        for i in range(16):               # 16분음표로 조밀하게 = 긴장 상승
            place(HAT, t0 + i * SLOT / 2, 0.13 if i % 4 == 0 else 0.07, 0.60)
        if bar == 15:                     # 코러스 직전 스네어 롤 + 스웰
            place(RISER, t0, 0.30, 0.5)
            for i in range(8):
                place(SNARE, t0 + BEAT * 2 + i * SLOT / 4,
                      0.10 + 0.05 * i, 0.5)

    elif sec == CHORUS:
        place(KICK, t0, 0.78, 0.5)
        place(KICK, t0 + BEAT * 2.5, 0.56, 0.5)
        place(SNARE, t0 + BEAT, 0.42, 0.5)
        place(SNARE, t0 + BEAT * 3, 0.42, 0.5)
        for i in range(8):
            if i == 7:
                place(HATO, t0 + i * SLOT, 0.14, 0.62)
            else:
                place(HAT, t0 + i * SLOT, 0.19 if i % 2 == 0 else 0.12, 0.62)
        if bar in (16, 20):
            place(CRASH, t0, 0.22, 0.5)

    elif sec == OUTRO and bar == 24:
        place(CRASH, t0, 0.16, 0.5)
        place(KICK, t0, 0.45, 0.5)

    # ── 멜로디 ────────────────────────────────────────
    for slot, d, length in MELODY.get(bar, []):
        g = 0.26 if sec == PRE else 0.36
        echo(lead(deg(d), SLOT * length * 0.94), t0 + slot * SLOT,
             g, 0.55, times=2)

    print(f"  {bar + 1:2d}/{BARS}마디  {SONG[bar]:<4}", end="\r")

print("\n리버브 처리 중...")


# ══ 리버브 ═════════════════════════════════════════════
def reverb(buf, mix=0.30, predelay=0.03):
    """빗살 지연 세 개를 겹친 간이 홀 리버브."""
    combs = [(1637, 0.855), (1913, 0.837), (2311, 0.815)]
    pre = int(predelay * SR)
    wet = [0.0] * N
    for delay, fb in combs:
        line = [0.0] * delay
        idx = 0
        for i in range(N):
            v = line[idx]
            wet[i] += v * 0.33
            src = buf[i - pre] if i >= pre else 0.0
            line[idx] = src + v * fb
            idx += 1
            if idx == delay:
                idx = 0
    for i in range(N):
        buf[i] = buf[i] * (1.0 - mix * 0.55) + wet[i] * mix
    return buf


reverb(left)
reverb(right)

# ══ 마스터링 ═══════════════════════════════════════════
print("마무리 중...")

# 끝부분 페이드아웃
fade = int(3.0 * SR)
for i in range(fade):
    g = (1.0 - i / fade) ** 1.5
    left[N - fade + i] *= g
    right[N - fade + i] *= g

peak = max(max(abs(v) for v in left), max(abs(v) for v in right)) or 1.0
norm = 1.25 / peak                       # 살짝 세게 밀어 넣고 소프트 클리핑으로 눌러준다

frames = array.array("h")
for i in range(N):
    for v in (left[i], right[i]):
        frames.append(int(math.tanh(v * norm) * 31500))

OUT = "ballad.wav"
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(frames.tobytes())

print(f"완성: {OUT}   {int(DUR // 60)}분 {DUR % 60:.0f}초 / {BPM} BPM / B minor")
