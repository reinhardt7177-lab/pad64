"""
스파이 액션 큐 — 코드로 쓴 5/4박자 곡.  표준 라이브러리만 사용.

    python spy.py        ->  spy.wav

이 장르를 만드는 건 멜로디가 아니라 네 가지 장치다.
  1) 5/4박자를 3+2 로 쪼갠 절뚝거리는 그루브  (쿵짝짝 쿵짝)
  2) 한 순간도 안 쉬는 8분음표 베이스 오스티나토
  3) 짧고 사납게 끊어치는 브라스 스탭
  4) 트레몰로 + 리버브 범벅의 스파이 기타

조성 : G minor (긴장 구간엔 프리지안 bII = Db 를 꽂는다)
템포 : 164 BPM, 5/4  ->  한 마디 = 8분음표 10칸
구성 : 인트로4 / 타악4 / A8 / A2-브라스8 / B-기타테마8 / 브레이크4 / C8 / D절정8 / 아웃트로4 = 56마디
"""

import array
import math
import random
import wave

# ══ 기본 설정 ══════════════════════════════════════════
SR = 44100
BPM = 164
BEAT = 60.0 / BPM            # 4분음표 0.366초
SLOT = BEAT / 2              # 8분음표 = 격자 최소 단위
BAR = BEAT * 5               # 5/4 !  한 마디 1.829초 = 8분음표 10칸
BARS = 56
TAIL = 4.0
DUR = BAR * BARS + TAIL
N = int(DUR * SR)

random.seed(66613)
TWO_PI = 2.0 * math.pi


def hz(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


# ══ 필터 ═══════════════════════════════════════════════
def lowpass(buf, cutoff, poles=1):
    k = 1.0 - math.exp(-TWO_PI * cutoff / SR)
    for _ in range(poles):
        y = 0.0
        for i, x in enumerate(buf):
            y += (x - y) * k
            buf[i] = y
    return buf


def highpass(buf, cutoff):
    k = 1.0 - math.exp(-TWO_PI * cutoff / SR)
    y = 0.0
    for i, x in enumerate(buf):
        y += (x - y) * k
        buf[i] = x - y
    return buf


def fade_tail(buf, sec=0.05):
    n = min(int(sec * SR), len(buf))
    for i in range(n):
        buf[len(buf) - n + i] *= 1.0 - i / n
    return buf


def distort(buf, drive, bias=0.0):
    off = math.tanh(bias)
    for i, x in enumerate(buf):
        buf[i] = math.tanh(x * drive + bias) - off
    return buf


_CACHE = {}


def cached(key, build):
    if key not in _CACHE:
        _CACHE[key] = build()
    return _CACHE[key]


# ══ 악기 ═══════════════════════════════════════════════
def _bass(midi, dur):
    """스타카토 베이스. 짧고 단단하게 끊어야 오스티나토가 굴러간다."""
    rel = 0.06
    n = int((dur + rel) * SR)
    out = [0.0] * n
    inc = hz(midi) / SR
    p = 0.0
    for i in range(n):
        t = i / SR
        p += inc
        x = p % 1.0
        v = math.sin(TWO_PI * p) * 0.8 + (2.0 * x - 1.0) * 0.55
        if t < 0.004:
            e = t / 0.004
        elif t < dur:
            e = 0.75 + 0.25 * math.exp(-(t - 0.004) * 22.0)
        else:
            e = 0.75 * max(0.0, 1.0 - (t - dur) / rel)
        out[i] = v * e
    for i in range(int(0.02 * SR)):      # 픽 어택
        out[i] += random.uniform(-1, 1) * 0.12 * math.exp(-i / SR * 260.0)
    distort(out, 2.6, bias=0.06)
    lowpass(out, 1100.0, poles=2)
    return fade_tail(out, 0.03)


def bass(midi, dur):
    return cached(("bs", midi, round(dur, 3)), lambda: _bass(midi, dur))


def _brass(midi, dur, bright=1.0):
    """브라스 = 톱니 여러 겹 + '확 열렸다 닫히는 필터'.
    이 필터 엔벨로프가 없으면 그냥 신스지 관악기가 아니다."""
    f = hz(midi)
    rel = 0.16
    n = int((dur + rel) * SR)
    out = [0.0] * n
    for det in (0.9935, 0.999, 1.0, 1.0065):
        inc = f * det / SR
        p = random.random()
        for i in range(n):
            p += inc
            out[i] += 2.0 * (p % 1.0) - 1.0
    for i in range(n):
        t = i / SR
        if t < 0.018:
            e = t / 0.018
        elif t < dur:
            e = 0.86 + 0.14 * math.exp(-(t - 0.018) * 10.0)
        else:
            e = 0.86 * max(0.0, 1.0 - (t - dur) / rel) ** 1.2
        out[i] *= e * 0.20
    y = 0.0                                # 시변 로우패스 = 입술이 열리는 순간
    for i in range(n):
        t = i / SR
        co = 320.0 + 3400.0 * bright * math.exp(-t * 11.0) + 700.0 * bright
        k = 1.0 - math.exp(-TWO_PI * min(co, 16000.0) / SR)
        y += (out[i] - y) * k
        out[i] = y
    distort(out, 2.0, bias=0.10)
    highpass(out, 130.0)
    return fade_tail(out, 0.05)


def brass(midi, dur, bright=1.0):
    return cached(("br", midi, round(dur, 3), bright),
                  lambda: _brass(midi, dur, bright))


def pluck(midi, dur, bright=0.6, sustain=1.6):
    """Karplus-Strong — 줄을 튕기는 물리 현상 그대로."""
    L = max(2, int(round(SR / hz(midi))))
    buf = [random.uniform(-1.0, 1.0) for _ in range(L)]
    for _ in range(2):
        prev = buf[-1]
        for i in range(L):
            buf[i], prev = (buf[i] + prev) * 0.5, buf[i]
    n = int(dur * SR)
    out = [0.0] * n
    dec = math.exp(-sustain / SR)
    a = 0.52 + 0.46 * bright
    prev = 0.0
    idx = 0
    for i in range(n):
        v = buf[idx]
        out[i] = v
        buf[idx] = (v * a + prev * (1.0 - a)) * dec
        prev = v
        idx += 1
        if idx == L:
            idx = 0
    return out


def _spy(midi, dur):
    """스파이 기타 — 트레몰로(음량을 빠르게 떨기)가 정체성이다."""
    s = pluck(midi, dur + 0.3, bright=0.74, sustain=1.5)
    for i in range(len(s)):
        t = i / SR
        s[i] *= 1.0 - 0.42 * (1.0 - math.cos(TWO_PI * 7.0 * t)) * 0.5
        if t > dur:
            s[i] *= max(0.0, 1.0 - (t - dur) / 0.3)
    distort(s, 2.4, bias=0.04)
    highpass(s, 190.0)
    lowpass(s, 5200.0)
    return fade_tail(s, 0.05)


def spy(midi, dur):
    return cached(("sp", midi, round(dur, 3)), lambda: _spy(midi, dur))


def _flute(midi, dur):
    """높은 목관 — 숨소리(노이즈)를 섞어야 사람이 부는 것처럼 들린다."""
    f = hz(midi)
    rel = 0.22
    n = int((dur + rel) * SR)
    out = [0.0] * n
    p = 0.0
    for i in range(n):
        t = i / SR
        vib = 1.0 + 0.006 * min(1.0, max(0.0, (t - 0.15) / 0.3)) \
            * math.sin(TWO_PI * 5.0 * t)
        p += f * vib / SR
        v = math.sin(TWO_PI * p) + 0.13 * math.sin(4.0 * math.pi * p)
        v += random.uniform(-1, 1) * (0.14 * math.exp(-t * 26.0) + 0.02)
        if t < 0.05:
            e = t / 0.05
        elif t < dur:
            e = 1.0
        else:
            e = max(0.0, 1.0 - (t - dur) / rel)
        out[i] = v * e * 0.32
    highpass(out, 250.0)
    return fade_tail(out, 0.06)


def flute(midi, dur):
    return cached(("fl", midi, round(dur, 3)), lambda: _flute(midi, dur))


# ── 타악 ────────────────────────────────────────────────
def _kick():
    n = int(0.4 * SR)
    out = [0.0] * n
    p = 0.0
    for i in range(n):
        t = i / SR
        f = 46.0 + 105.0 * math.exp(-t * 45.0)
        p += f / SR
        out[i] = (math.sin(TWO_PI * p) * math.exp(-t * 10.0)
                  + random.uniform(-1, 1) * 0.28 * math.exp(-t * 430.0))
    return fade_tail(out)


def _snare():
    n = int(0.26 * SR)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        out[i] = (0.40 * math.sin(TWO_PI * 205 * t) * math.exp(-t * 26.0)
                  + random.uniform(-1, 1) * math.exp(-t * 20.0)
                  + random.uniform(-1, 1) * 0.5 * math.exp(-t * 55.0))
    highpass(out, 190.0)
    return fade_tail(out)


def _bongo(f0):
    """봉고/콩가 — 이 장르의 숨은 주인공. 5/4를 굴러가게 만든다."""
    n = int(0.22 * SR)
    out = [0.0] * n
    p = 0.0
    for i in range(n):
        t = i / SR
        f = f0 * (1.0 + 0.55 * math.exp(-t * 60.0))
        p += f / SR
        out[i] = (math.sin(TWO_PI * p) * math.exp(-t * 17.0)
                  + random.uniform(-1, 1) * 0.30 * math.exp(-t * 120.0))
    highpass(out, 120.0)
    return fade_tail(out)


def _shaker():
    n = int(0.07 * SR)
    out = [0.0] * n
    prev = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        out[i] = (x - prev) * 0.5 * math.exp(-t * 48.0)
        prev = x
    return fade_tail(out)


def _hat(open_=False):
    n = int((0.24 if open_ else 0.05) * SR)
    out = [0.0] * n
    dk = 12.0 if open_ else 70.0
    prev = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        out[i] = (x - prev) * 0.5 * math.exp(-t * dk)
        prev = x
    return fade_tail(out)


def _crash():
    n = int(2.4 * SR)
    out = [0.0] * n
    prev = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        out[i] = (x - prev) * 0.5 * math.exp(-t * 1.8)
        prev = x
    return fade_tail(out, 0.3)


def _timp(midi):
    n = int(0.9 * SR)
    out = [0.0] * n
    f = hz(midi)
    p = 0.0
    for i in range(n):
        t = i / SR
        p += f * (1.0 + 0.06 * math.exp(-t * 20.0)) / SR
        out[i] = (math.sin(TWO_PI * p) + 0.3 * math.sin(4 * math.pi * p)) \
            * math.exp(-t * 3.2) * 0.8
        out[i] += random.uniform(-1, 1) * 0.10 * math.exp(-t * 60.0)
    return fade_tail(out, 0.15)


KICK = _kick()
SNARE = _snare()
BONGO_HI = _bongo(310)
BONGO_LO = _bongo(198)
CONGA = _bongo(146)
SHAKER = _shaker()
HAT = _hat()
HATO = _hat(True)
CRASH = _crash()
TIMP = _timp(31)          # G1

# ══ 믹서 ═══════════════════════════════════════════════
left = [0.0] * N
right = [0.0] * N


def place(samples, at, gain=1.0, pan=0.5):
    i0 = int(at * SR)
    if i0 >= N or i0 < 0:
        return
    gl = gain * math.sqrt(1.0 - pan)
    gr = gain * math.sqrt(pan)
    for i in range(min(len(samples), N - i0)):
        v = samples[i]
        left[i0 + i] += v * gl
        right[i0 + i] += v * gr


def stab(notes, at, dur, gain, bright=1.0, spread=0.5):
    """브라스 섹션 — 여러 음을 동시에, 아주 살짝 어긋나게."""
    for k, m in enumerate(notes):
        place(brass(m, dur, bright), at + k * 0.004, gain,
              spread + (k - len(notes) / 2) * 0.07)


# ══ 악보 ═══════════════════════════════════════════════
# G 마이너.  프리지안 bII(Db) 는 긴장 구간 전용.
SCALE = [0, 2, 3, 5, 7, 8, 10]


def deg(n):
    """자리번호 -> MIDI.  0 = G4(67)"""
    return 67 + 12 * (n // 7) + SCALE[n % 7]


G, EB, F, DB, C, D = 31, 27, 29, 25, 24, 26      # 베이스 근음 (옥타브 1)

INTRO, PERC, A, A2, B, BREAK, Cx, Dx, OUTRO = range(9)
SECTION = ([INTRO] * 4 + [PERC] * 4 + [A] * 8 + [A2] * 8 + [B] * 8
           + [BREAK] * 4 + [Cx] * 8 + [Dx] * 8 + [OUTRO] * 4)

# 마디 번호를 손으로 세면 반드시 틀린다. 구간 내 순번과 시작 마디는 계산으로 뽑는다.
IDX = []                       # IDX[bar] = 그 구간 안에서 몇 번째 마디인가
FIRST = {}                     # FIRST[구간] = 그 구간이 시작하는 마디
_seen = {}
for _i, _s in enumerate(SECTION):
    _seen[_s] = _seen.get(_s, -1) + 1
    IDX.append(_seen[_s])
    FIRST.setdefault(_s, _i)

# 마디별 근음
ROOTS = ([G] * 4 + [G] * 4
         + [G, G, G, G, G, G, EB, F]
         + [G, G, G, G, G, G, EB, F]
         + [G, G, EB, EB, F, F, G, G]
         + [DB, DB, C, C]
         + [G, G, DB, DB, EB, EB, F, F]
         + [G, G, DB, DB, EB, EB, F, D]
         + [G, G, EB, G])

# 8분음표 10칸짜리 베이스 오스티나토 (근음 대비 반음 오프셋)
OST_A = [0, 0, 0, 0, 0, 0, 0, 0, 3, 5]        # ... Bb C 로 밀어올림
OST_B = [0, 0, 0, 0, 0, 0, 0, 0, -2, -4]      # ... F Eb 로 떨어뜨림
OST_HI = [0, 0, 12, 0, 0, 0, 12, 0, 3, 5]     # 옥타브 튀기 (절정용)

# 5/4 를 3+2 로 쪼갠 그루브.  10칸 중 어디를 치는가.
KICK_SLOTS = [0, 6]
SNARE_SLOTS = [3, 8]
BONGO_HI_SLOTS = [2, 5, 7, 9]
BONGO_LO_SLOTS = [0, 4, 6]

# 기타 테마 (B구간 8마디) : (시작칸, 자리번호, 길이칸)
THEME = [
    [(0, 0, 2), (2, 2, 1), (3, 0, 1), (4, 4, 2), (6, 2, 2), (8, 0, 2)],
    [(0, 0, 2), (2, 2, 1), (3, 0, 1), (4, 5, 4), (8, 4, 2)],
    [(0, 4, 2), (2, 3, 1), (3, 2, 1), (4, 0, 2), (6, 2, 2), (8, 4, 2)],
    [(0, 5, 4), (4, 4, 2), (6, 2, 2), (8, 0, 2)],
    [(0, 0, 2), (2, 2, 1), (3, 0, 1), (4, 4, 2), (6, 2, 2), (8, 0, 2)],
    [(0, 0, 2), (2, 2, 1), (3, 0, 1), (4, 6, 4), (8, 5, 2)],
    [(0, 6, 2), (2, 5, 2), (4, 4, 2), (6, 2, 2), (8, 4, 2)],
    [(0, 7, 6), (6, 5, 4)],
]

# 절정부 멜로디 (D구간 8마디) — 플루트 + 브라스가 같이 간다
CLIMAX = [
    [(0, 7, 3), (3, 6, 1), (4, 5, 2), (6, 7, 4)],
    [(0, 6, 2), (2, 5, 2), (4, 4, 6)],
    [(0, 5, 3), (3, 4, 1), (4, 2, 2), (6, 5, 4)],
    [(0, 4, 4), (4, 2, 2), (6, 0, 4)],
    [(0, 7, 3), (3, 8, 1), (4, 9, 6)],
    [(0, 8, 2), (2, 7, 2), (4, 6, 6)],
    [(0, 7, 2), (2, 6, 2), (4, 5, 2), (6, 4, 2), (8, 2, 2)],
    [(0, 7, 10)],
]

# 브라스 스탭이 꽂히는 칸 (3+2 를 강조하는 자리)
STAB_SLOTS = [0, 6]

print(f"렌더링 시작 — {BARS}마디 / 5-4박자 / {DUR:.0f}초")

for bar in range(BARS):
    t0 = bar * BAR
    sec = SECTION[bar]
    root = ROOTS[bar]
    last = bar == BARS - 1

    # ── 베이스 오스티나토 : 이 곡의 엔진 ─────────────
    if sec == Dx or (sec == Cx and bar % 2 == 1):
        ost = OST_HI
    elif bar % 2 == 1:
        ost = OST_B
    else:
        ost = OST_A
    bgain = {INTRO: 0.62, PERC: 0.66, A: 0.72, A2: 0.72, B: 0.70,
             BREAK: 0.55, Cx: 0.78, Dx: 0.80, OUTRO: 0.66}[sec]
    if not last:
        for i, off in enumerate(ost):
            place(bass(root + 12 + off, SLOT * 0.72), t0 + i * SLOT,
                  bgain * (1.15 if i in (0, 6) else 1.0), 0.5)

    # ── 타악 ──────────────────────────────────────────
    if sec != INTRO and not last:
        soft = sec in (PERC, BREAK, OUTRO)
        for s_ in KICK_SLOTS:
            place(KICK, t0 + s_ * SLOT, 0.55 if soft else 0.85, 0.5)
        if sec not in (PERC, BREAK):
            for s_ in SNARE_SLOTS:
                place(SNARE, t0 + s_ * SLOT, 0.42, 0.5)
        for s_ in BONGO_HI_SLOTS:
            place(BONGO_HI, t0 + s_ * SLOT, 0.30 if soft else 0.38,
                  0.68)
        for s_ in BONGO_LO_SLOTS:
            place(BONGO_LO, t0 + s_ * SLOT, 0.32 if soft else 0.40, 0.32)
        if sec in (A, A2, B, Cx, Dx):
            for i in range(10):
                place(HATO if i == 9 else HAT, t0 + i * SLOT,
                      0.13 if i in (0, 6) else 0.08, 0.60)
        if sec in (Cx, Dx):
            for i in range(20):
                place(SHAKER, t0 + i * SLOT / 2, 0.10, 0.44)
            place(CONGA, t0 + 9 * SLOT, 0.30, 0.30)

    # ── 브라스 ────────────────────────────────────────
    triad = [root + 24, root + 31, root + 36]        # 근음+5도+옥타브
    if sec == A2:
        for s_ in STAB_SLOTS:
            stab(triad, t0 + s_ * SLOT, SLOT * 1.3, 0.50, 1.0)
        if bar % 4 == 3:
            stab(triad, t0 + 8 * SLOT, SLOT * 1.8, 0.44, 1.1)
    elif sec == Cx:
        for s_ in (0, 4, 6):
            stab(triad, t0 + s_ * SLOT, SLOT * 1.2, 0.52, 1.1)
    elif sec == Dx:
        for s_ in (0, 6):
            stab(triad, t0 + s_ * SLOT, SLOT * 1.5, 0.55, 1.25)
        for slot, d, length in CLIMAX[IDX[bar]]:      # 멜로디를 브라스로 겹침
            place(brass(deg(d) - 12, SLOT * length * 0.92, 1.15),
                  t0 + slot * SLOT, 0.30, 0.42)
    elif sec == BREAK and bar % 2 == 0:
        stab([root + 24, root + 31], t0, SLOT * 3.0, 0.34, 0.7)

    # ── 기타 테마 ─────────────────────────────────────
    if sec == B:
        for slot, d, length in THEME[IDX[bar]]:
            place(spy(deg(d), SLOT * length * 0.95), t0 + slot * SLOT,
                  0.46, 0.36)
            place(spy(deg(d) - 12, SLOT * length * 0.95),
                  t0 + slot * SLOT + 0.012, 0.20, 0.64)
    elif sec in (A, Cx):
        # 리프의 뼈대만 툭툭 던져둔다
        for slot, d in ((0, 0), (6, 2)):
            place(spy(deg(d) - 12, SLOT * 1.6), t0 + slot * SLOT,
                  0.24 if sec == A else 0.30, 0.34)

    # ── 플루트 (절정부 멜로디) ────────────────────────
    if sec == Dx:
        for slot, d, length in CLIMAX[IDX[bar]]:
            place(flute(deg(d) + 12, SLOT * length * 0.94),
                  t0 + slot * SLOT, 0.34, 0.60)
    elif sec == B and IDX[bar] >= 4:
        for slot, d, length in THEME[IDX[bar]]:
            place(flute(deg(d) + 12, SLOT * length * 0.9),
                  t0 + slot * SLOT, 0.16, 0.66)

    # ── 구간 전환 액센트 ──────────────────────────────
    if bar in (FIRST[A], FIRST[A2], FIRST[B], FIRST[Cx], FIRST[Dx]):
        place(CRASH, t0, 0.24, 0.46)
    if bar in (FIRST[A2], FIRST[Dx]):
        place(TIMP, t0, 0.40, 0.5)
    if bar == FIRST[Dx] - 1:            # 절정 직전 팀파니 밀어넣기
        for i in range(6):
            place(TIMP, t0 + 4 * SLOT + i * SLOT * 0.5,
                  0.16 + 0.05 * i, 0.5)
    if last:
        place(CRASH, t0, 0.30, 0.5)
        place(TIMP, t0, 0.50, 0.5)
        stab([root + 12, root + 24, root + 31, root + 36], t0, 2.2, 0.55, 1.2)
        place(bass(root + 12, 2.2), t0, 0.8, 0.5)

    print(f"  {bar + 1:2d}/{BARS}", end="\r")

print("\n리버브 처리 중...")


# ══ 리버브 ═════════════════════════════════════════════
def reverb(buf, mix=0.26, predelay=0.025):
    combs = [(1571, 0.838), (1867, 0.822), (2251, 0.800)]
    pre = int(predelay * SR)
    wet = [0.0] * N
    for delay, fb in combs:
        line = [0.0] * delay
        idx = 0
        for i in range(N):
            v = line[idx]
            wet[i] += v * 0.33
            line[idx] = (buf[i - pre] if i >= pre else 0.0) + v * fb
            idx += 1
            if idx == delay:
                idx = 0
    for i in range(N):
        buf[i] = buf[i] * (1.0 - mix * 0.5) + wet[i] * mix
    return buf


reverb(left)
reverb(right)

# ══ 마스터링 ═══════════════════════════════════════════
print("마무리 중...")

fade = int(2.5 * SR)
for i in range(fade):
    g = (1.0 - i / fade) ** 1.3
    left[N - fade + i] *= g
    right[N - fade + i] *= g

peak = max(max(abs(v) for v in left), max(abs(v) for v in right)) or 1.0
norm = 1.5 / peak

frames = array.array("h")
for i in range(N):
    for v in (left[i], right[i]):
        frames.append(int(math.tanh(v * norm) * 31800))

OUT = "spy.wav"
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(frames.tobytes())

print(f"완성: {OUT}   {int(DUR // 60)}분 {DUR % 60:.0f}초 / {BPM} BPM / 5-4 / G minor")
