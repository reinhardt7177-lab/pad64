"""
록 발라드 — 코드로 쓴 2분짜리 곡.  외부 라이브러리 없이 표준 라이브러리만 사용.

    python rock.py        ->  rock.wav

핵심은 기타다. 톱니파로는 절대 기타 소리가 안 난다.
Karplus-Strong 으로 "줄을 튕기는 물리 현상"을 먼저 만들고,
그걸 디스토션 -> 캐비닛 필터에 통과시켜야 비로소 일렉기타가 된다.

조성 : E minor
템포 : 80 BPM (벌스는 하프타임, 코러스에서 풀타임으로 터짐)
구성 : 인트로4 / 벌스8 / 프리4 / 코러스8 / 브레이크4 / 라스트코러스8 / 아웃트로4 = 40마디
"""

import array
import math
import random
import wave

# ══ 기본 설정 ══════════════════════════════════════════
SR = 44100
BPM = 80
BEAT = 60.0 / BPM          # 0.75초
BAR = BEAT * 4             # 3.0초
SLOT = BEAT / 4            # 16분음표 = 리듬 격자의 최소 단위
BARS = 40
TAIL = 5.0
DUR = BAR * BARS + TAIL
N = int(DUR * SR)

random.seed(1013)
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
    """저역을 빼서 소리를 정리한다. 기타의 웅웅거림 제거용."""
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


def distort(buf, drive, bias=0.12):
    """tanh 로 파형의 머리를 눌러 찌그러뜨린다 = 배음이 폭발적으로 늘어난다.
    bias 를 주면 위아래가 비대칭이 되어 짝수 배음이 생긴다(진공관 느낌)."""
    off = math.tanh(bias)
    for i, x in enumerate(buf):
        buf[i] = math.tanh(x * drive + bias) - off
    return buf


def cabinet(buf, presence=4200.0):
    """기타 앰프 스피커는 대역이 좁다. 그 좁음이 곧 기타 소리다."""
    highpass(buf, 110.0)
    lowpass(buf, presence, poles=2)
    return buf


# ══ 악기 ═══════════════════════════════════════════════
_CACHE = {}


def cached(key, build):
    if key not in _CACHE:
        _CACHE[key] = build()
    return _CACHE[key]


def pluck(midi, dur, bright=0.5, sustain=1.6):
    """Karplus-Strong: 노이즈를 줄 길이만큼의 링버퍼에 넣고
    돌 때마다 이웃 샘플과 평균내면 -> 고음부터 사라지는 진짜 현 소리가 된다."""
    f = hz(midi)
    L = max(2, int(round(SR / f)))
    buf = [random.uniform(-1.0, 1.0) for _ in range(L)]
    for _ in range(2):                      # 초기 노이즈를 살짝 뭉갬 = 픽 두께
        prev = buf[-1]
        for i in range(L):
            buf[i], prev = (buf[i] + prev) * 0.5, buf[i]
    n = int(dur * SR)
    out = [0.0] * n
    dec = math.exp(-sustain / SR)
    a = 0.52 + 0.46 * bright                # 클수록 밝게 오래 남는다
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


def _clean(notes, dur):
    """클린 기타 — 튕긴 소리 그대로, 살짝만 다듬는다."""
    rel = 0.5
    n = int((dur + rel) * SR)
    mix = [0.0] * n
    for k, m in enumerate(notes):
        s = pluck(m, dur + rel, bright=0.62, sustain=2.2)
        off = int(k * 0.011 * SR)           # 스트로크: 줄마다 살짝 시차
        for i in range(min(len(s), n - off)):
            mix[off + i] += s[i] * 0.55
    distort(mix, 1.5, bias=0.0)             # 아주 약간만 (앰프 예열 느낌)
    highpass(mix, 90.0)
    lowpass(mix, 6000.0)
    return fade_tail(mix, 0.12)


def clean(notes, dur):
    return cached(("cl", tuple(notes), round(dur, 2)),
                  lambda: _clean(notes, dur))


def _power(root, dur, drive=11.0, mute=False):
    """파워코드 = 근음 + 5도 + 옥타브. 세 줄을 먼저 '합친 뒤' 찌그러뜨려야 한다.
    (따로 찌그러뜨려 합치면 그건 기타 세 대지 파워코드가 아니다)"""
    rel = 0.35 if mute else 0.6
    n = int((dur + rel) * SR)
    mix = [0.0] * n
    for k, m in enumerate((root, root + 7, root + 12)):
        s = pluck(m, dur + rel,
                  bright=0.30 if mute else 0.55,
                  sustain=9.0 if mute else 1.1)
        off = int(k * 0.006 * SR)
        for i in range(min(len(s), n - off)):
            mix[off + i] += s[i] * 0.6
    if mute:                                # 팜뮤트: 손날로 눌러 짧게 끊기
        for i in range(n):
            mix[i] *= math.exp(-i / SR * 13.0)
    distort(mix, drive)
    cabinet(mix, 3800.0 if mute else 4400.0)
    return fade_tail(mix, 0.08)


def power(root, dur, drive=11.0, mute=False):
    return cached(("pw", root, round(dur, 2), drive, mute),
                  lambda: _power(root, dur, drive, mute))


def _solo(midi, dur, drive=14.0, octave_up=False):
    """리드 기타 — 비브라토와 긴 서스테인이 생명."""
    m = midi + (12 if octave_up else 0)
    rel = 0.7
    n = int((dur + rel) * SR)
    base = hz(m)
    out = [0.0] * n
    p = 0.0
    for i in range(n):
        t = i / SR
        vib = 1.0 + 0.010 * min(1.0, max(0.0, (t - 0.22) / 0.35)) \
            * math.sin(TWO_PI * 5.6 * t)
        p += base * vib / SR
        x = p % 1.0
        # 톱니 + 사각을 섞어 두께를 만든 뒤 디스토션에 넣는다
        v = (2.0 * x - 1.0) * 0.6 + (1.0 if x < 0.5 else -1.0) * 0.4
        if t < 0.012:
            e = t / 0.012
        elif t < dur:
            e = 0.80 + 0.20 * math.exp(-(t - 0.012) * 2.2)
        else:
            e = 0.80 * max(0.0, 1.0 - (t - dur) / rel) ** 1.4
        out[i] = v * e * 0.5
    distort(out, drive, bias=0.18)
    cabinet(out, 3600.0)
    return fade_tail(out, 0.1)


def solo(midi, dur, drive=14.0, octave_up=False):
    return cached(("so", midi, round(dur, 2), drive, octave_up),
                  lambda: _solo(midi, dur, drive, octave_up))


def _bassnote(midi, dur):
    """피크로 긁은 베이스 — 살짝 찌그러뜨려야 디스토션 기타 속에서 안 묻힌다."""
    rel = 0.25
    n = int((dur + rel) * SR)
    out = [0.0] * n
    inc = hz(midi) / SR
    p = 0.0
    for i in range(n):
        t = i / SR
        p += inc
        x = p % 1.0
        v = math.sin(TWO_PI * p) * 0.75 + (2.0 * x - 1.0) * 0.45
        if t < 0.006:
            e = t / 0.006
        elif t < dur:
            e = 0.85 + 0.15 * math.exp(-(t - 0.006) * 6.0)
        else:
            e = 0.85 * max(0.0, 1.0 - (t - dur) / rel)
        out[i] = v * e
    for i in range(int(0.03 * SR)):         # 피크가 줄을 긁는 소리
        out[i] += random.uniform(-1, 1) * 0.10 * math.exp(-i / SR * 200.0)
    distort(out, 2.2, bias=0.05)
    lowpass(out, 900.0, poles=2)
    return fade_tail(out, 0.06)


def bassnote(midi, dur):
    return cached(("bs", midi, round(dur, 2)), lambda: _bassnote(midi, dur))


def _pad(notes, dur):
    """뒤에서 공간을 채우는 스트링 패드."""
    atk, rel = 1.0, 2.0
    n = int((dur + rel) * SR)
    out = [0.0] * n
    for m in notes:
        for det in (0.9968, 1.0, 1.0034):
            inc = hz(m) * det / SR
            p = random.random()
            for i in range(n):
                p += inc
                out[i] += 2.0 * (p % 1.0) - 1.0
    for i in range(n):
        t = i / SR
        if t < atk:
            e = (t / atk) ** 1.7
        elif t < dur:
            e = 1.0
        else:
            e = max(0.0, 1.0 - (t - dur) / rel) ** 1.3
        out[i] *= e * 0.055
    lowpass(out, 1100.0, poles=2)
    return fade_tail(out, 0.2)


def pad(notes, dur):
    return cached(("pd", tuple(notes), round(dur, 2)),
                  lambda: _pad(notes, dur))


# ── 드럼 ────────────────────────────────────────────────
def _kick():
    n = int(0.5 * SR)
    out = [0.0] * n
    p = 0.0
    for i in range(n):
        t = i / SR
        f = 48.0 + 110.0 * math.exp(-t * 42.0)
        p += f / SR
        out[i] = (math.sin(TWO_PI * p) * math.exp(-t * 8.0)
                  + random.uniform(-1, 1) * 0.30 * math.exp(-t * 420.0))
    return fade_tail(out)


def _snare(big=True):
    """록 발라드의 스네어는 크고 길다. 몸통 두 개 + 노이즈 두 겹."""
    n = int((0.45 if big else 0.22) * SR)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        body = (0.45 * math.sin(TWO_PI * 180 * t) * math.exp(-t * 20.0)
                + 0.28 * math.sin(TWO_PI * 331 * t) * math.exp(-t * 26.0))
        wire = (random.uniform(-1, 1) * math.exp(-t * (11.0 if big else 26.0))
                + random.uniform(-1, 1) * 0.5 * math.exp(-t * 45.0))
        out[i] = body + wire
    highpass(out, 160.0)
    return fade_tail(out)


def _rim():
    n = int(0.09 * SR)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        out[i] = (math.sin(TWO_PI * 1750 * t) * math.exp(-t * 130.0)
                  + random.uniform(-1, 1) * 0.6 * math.exp(-t * 260.0))
    return fade_tail(out)


def _hat(open_=False):
    n = int((0.30 if open_ else 0.055) * SR)
    out = [0.0] * n
    dk = 10.0 if open_ else 65.0
    prev = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        out[i] = (x - prev) * 0.5 * math.exp(-t * dk)
        prev = x
    return fade_tail(out)


def _crash():
    n = int(2.8 * SR)
    out = [0.0] * n
    prev = 0.0
    for i in range(n):
        t = i / SR
        x = random.uniform(-1, 1)
        out[i] = (x - prev) * 0.5 * math.exp(-t * 1.5)
        prev = x
    return fade_tail(out, 0.4)


def _tom(f0):
    n = int(0.42 * SR)
    out = [0.0] * n
    p = 0.0
    for i in range(n):
        t = i / SR
        f = f0 * (1.0 + 0.35 * math.exp(-t * 14.0))
        p += f / SR
        out[i] = (math.sin(TWO_PI * p) * math.exp(-t * 8.0)
                  + random.uniform(-1, 1) * 0.20 * math.exp(-t * 30.0))
    return fade_tail(out)


KICK = _kick()
SNARE = _snare(True)
SNARE_S = _snare(False)
RIM = _rim()
HAT = _hat()
HATO = _hat(True)
CRASH = _crash()
TOMS = [_tom(180), _tom(140), _tom(105)]

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


def double(samples, at, gain, spread=0.018):
    """같은 기타를 좌우로 살짝 어긋나게 두 번 = 벽처럼 두꺼운 소리."""
    place(samples, at, gain, 0.12)
    place(samples, at + spread, gain * 0.92, 0.88)


# ══ 악보 ═══════════════════════════════════════════════
# 코드: 파워코드 근음 / 베이스 근음 / 클린기타 보이싱 / 패드 보이싱
CHORD = {
    "Em": (40, 28, [52, 55, 59, 64], [52, 59, 64]),
    "C":  (48, 36, [48, 52, 55, 60], [48, 55, 64]),
    "G":  (43, 31, [50, 55, 59, 62], [50, 55, 62]),
    "D":  (50, 38, [50, 54, 57, 62], [50, 57, 62]),
    "Am": (45, 33, [45, 52, 57, 60], [45, 52, 60]),
    "B":  (47, 35, [47, 51, 54, 59], [47, 54, 59]),
}

INTRO, VERSE, PRE, CHORUS, BREAK, LAST, OUTRO = range(7)

SONG = (["Em", "C", "G", "D"]                                  # 인트로 0-3
        + ["Em", "C", "G", "D", "Em", "C", "G", "D"]           # 벌스  4-11
        + ["C", "G", "Am", "B"]                                # 프리  12-15
        + ["C", "G", "D", "Em", "C", "G", "D", "D"]            # 코러스 16-23
        + ["Em", "C", "G", "B"]                                # 브레이크 24-27
        + ["C", "G", "D", "Em", "C", "G", "D", "B"]            # 라스트 28-35
        + ["Em", "C", "G", "Em"])                              # 아웃트로 36-39

SECTION = ([INTRO] * 4 + [VERSE] * 8 + [PRE] * 4 + [CHORUS] * 8
           + [BREAK] * 4 + [LAST] * 8 + [OUTRO] * 4)

SCALE = [0, 2, 3, 5, 7, 8, 10]          # E 내추럴 마이너


def deg(n):
    """스케일 자리번호 -> MIDI.  0 = E4"""
    return 64 + 12 * (n // 7) + SCALE[n % 7]


# 멜로디: {마디: [(시작 8분음표 칸, 자리번호, 길이 칸수)]}  한 마디 = 8칸
MELODY = {
    # 프리코러스 — 조여 올라간다
    12: [(0, 0, 2), (2, 1, 2), (4, 2, 3), (7, 1, 1)],
    13: [(0, 2, 3), (3, 3, 1), (4, 2, 4)],
    14: [(0, 3, 2), (2, 4, 2), (4, 5, 4)],
    15: [(0, 4, 2), (2, 5, 2), (4, 6, 4)],
    # 코러스
    16: [(0, 4, 4), (4, 2, 4)],
    17: [(0, 3, 2), (2, 4, 2), (4, 5, 4)],
    18: [(0, 4, 3), (3, 3, 1), (4, 2, 4)],
    19: [(0, 0, 4), (4, 2, 4)],
    20: [(0, 4, 4), (4, 5, 4)],
    21: [(0, 6, 2), (2, 5, 2), (4, 4, 4)],
    22: [(0, 5, 3), (3, 4, 1), (4, 3, 4)],
    23: [(0, 4, 8)],
    # 라스트 코러스 — 한 옥타브 위, 최고음까지
    28: [(0, 4, 4), (4, 5, 4)],
    29: [(0, 6, 2), (2, 7, 2), (4, 6, 4)],
    30: [(0, 7, 3), (3, 6, 1), (4, 5, 4)],
    31: [(0, 7, 4), (4, 4, 4)],
    32: [(0, 8, 4), (4, 9, 4)],                # 정점
    33: [(0, 9, 2), (2, 8, 2), (4, 7, 4)],
    34: [(0, 7, 3), (3, 6, 1), (4, 5, 4)],
    35: [(0, 4, 8)],
}

# 클린 기타 아르페지오 — 16분 격자 위 어디를 튕길지
ARP = [0, 2, 1, 3, 0, 2, 1, 3]

print(f"렌더링 시작 — {BARS}마디 / {DUR:.0f}초")

for bar in range(BARS):
    t0 = bar * BAR
    sec = SECTION[bar]
    proot, broot, cvoice, pvoice = CHORD[SONG[bar]]
    heavy = sec in (CHORUS, LAST)
    last = bar == BARS - 1

    # ── 패드 ──────────────────────────────────────────
    pg = {INTRO: 0.55, VERSE: 0.6, PRE: 0.7, CHORUS: 0.85,
          BREAK: 0.7, LAST: 0.9, OUTRO: 0.7}[sec]
    place(pad(pvoice, BAR * 0.97), t0, pg, 0.5)

    # ── 기타 ──────────────────────────────────────────
    if sec in (INTRO, VERSE, BREAK, OUTRO):
        # 클린 아르페지오
        for i, k in enumerate(ARP):
            place(clean([cvoice[k]], SLOT * 3.5), t0 + i * SLOT * 2,
                  0.42 if i % 4 == 0 else 0.30, 0.30 + 0.06 * k)
        if sec in (INTRO, OUTRO) or bar % 4 == 0:
            place(clean(cvoice, BEAT * 3.6), t0, 0.34, 0.62)

    elif sec == PRE:
        # 팜뮤트로 잘게 썰며 긴장 축적
        for i in range(8):
            double(power(proot, SLOT * 1.6, drive=9.0, mute=True),
                   t0 + i * SLOT * 2, 0.34)
        place(clean(cvoice, BEAT * 3.6), t0, 0.20, 0.5)
        if bar == 15:      # 코러스 직전 — 뮤트 풀고 열어젖힌다
            double(power(proot, BEAT * 1.9, drive=12.0), t0 + BEAT * 2, 0.42)

    else:
        # 코러스 — 파워코드를 길게 눌러 벽을 세운다
        double(power(proot, BEAT * 2.05, drive=12.0), t0, 0.46)
        double(power(proot, BEAT * 1.05, drive=12.0), t0 + BEAT * 2, 0.42)
        double(power(proot, BEAT * 0.95, drive=12.0), t0 + BEAT * 3, 0.40)
        if sec == LAST:    # 라스트에는 8분으로 더 몰아친다
            for i in (5, 7):
                double(power(proot, SLOT * 1.8, drive=12.0), t0 + i * SLOT * 2,
                       0.26)

    if last:               # 마지막 마디 — 길게 울려서 끝
        double(power(proot, 4.5, drive=12.0), t0, 0.5)
        place(clean(cvoice, 4.5), t0, 0.34, 0.5)

    # ── 베이스 ────────────────────────────────────────
    if sec == INTRO:
        pass
    elif sec in (VERSE, BREAK):
        place(bassnote(broot, BEAT * 1.9), t0, 0.62, 0.5)
        place(bassnote(broot, BEAT * 1.4), t0 + BEAT * 2, 0.52, 0.5)
    elif sec == OUTRO:
        place(bassnote(broot, BEAT * 3.6), t0, 0.55, 0.5)
    else:
        for b, hold in ((0, 1.9), (2, 0.9), (3, 0.45), (3.5, 0.45)):
            place(bassnote(broot, BEAT * hold), t0 + b * BEAT, 0.66, 0.5)

    # ── 드럼 ──────────────────────────────────────────
    if sec == VERSE:
        # 하프타임: 킥 1박, 스네어 3박 — 느리고 무겁게 들린다
        place(KICK, t0, 0.72, 0.5)
        place(KICK, t0 + BEAT * 2.75, 0.42, 0.5)
        place(RIM if bar < 8 else SNARE_S, t0 + BEAT * 2,
              0.34 if bar < 8 else 0.30, 0.5)
        if bar >= 8:
            for i in range(8):
                place(HAT, t0 + i * SLOT * 2,
                      0.20 if i % 2 == 0 else 0.12, 0.60)

    elif sec == PRE:
        place(KICK, t0, 0.78, 0.5)
        place(KICK, t0 + BEAT * 2.5, 0.50, 0.5)
        place(SNARE_S, t0 + BEAT * 2, 0.38, 0.5)
        for i in range(16):
            place(HAT, t0 + i * SLOT, 0.16 if i % 4 == 0 else 0.09, 0.60)
        if bar == 15:      # 톰 필로 코러스에 꽂아넣기
            for i, tm in enumerate([0, 0, 1, 1, 2, 2]):
                place(TOMS[tm], t0 + BEAT * 2.5 + i * SLOT,
                      0.34 + 0.05 * i, 0.30 + 0.14 * tm)

    elif heavy:
        place(KICK, t0, 0.88, 0.5)
        place(KICK, t0 + BEAT * 1.5, 0.60, 0.5)
        place(KICK, t0 + BEAT * 2.5, 0.66, 0.5)
        place(SNARE, t0 + BEAT, 0.60, 0.5)
        place(SNARE, t0 + BEAT * 3, 0.60, 0.5)
        for i in range(8):
            place(HATO if i == 7 else HAT, t0 + i * SLOT * 2,
                  0.16 if i == 7 else (0.22 if i % 2 == 0 else 0.14), 0.62)
        if bar in (16, 20, 28, 32):
            place(CRASH, t0, 0.26, 0.42)
        if bar in (23, 35):        # 섹션 끝 필
            for i, tm in enumerate([2, 1, 0]):
                place(TOMS[tm], t0 + BEAT * 3 + i * SLOT * 1.33,
                      0.38, 0.62 - 0.14 * tm)

    elif sec == BREAK:
        if bar == 24:
            place(CRASH, t0, 0.20, 0.5)
        place(KICK, t0, 0.50, 0.5)
        place(RIM, t0 + BEAT * 2, 0.26, 0.5)
        if bar == 27:              # 라스트 코러스로 다시 밀어넣기
            for i in range(8):
                place(SNARE_S, t0 + BEAT * 2 + i * SLOT,
                      0.16 + 0.045 * i, 0.5)

    elif sec == OUTRO and bar == 36:
        place(CRASH, t0, 0.20, 0.5)
        place(KICK, t0, 0.55, 0.5)

    # ── 리드 기타 ─────────────────────────────────────
    for slot, d, length in MELODY.get(bar, []):
        up = sec == LAST
        g = 0.26 if sec == PRE else (0.40 if sec == CHORUS else 0.44)
        s = solo(deg(d), SLOT * 2 * length * 0.96,
                 drive=13.0 if sec == PRE else 15.0, octave_up=False)
        place(s, t0 + slot * SLOT * 2, g, 0.56)
        if up:                     # 라스트에서는 옥타브 위를 겹쳐 화려하게
            place(solo(deg(d), SLOT * 2 * length * 0.96, 15.0, True),
                  t0 + slot * SLOT * 2 + 0.014, g * 0.5, 0.40)

    print(f"  {bar + 1:2d}/{BARS}  {SONG[bar]:<3}", end="\r")

print("\n리버브 처리 중...")


# ══ 리버브 ═════════════════════════════════════════════
def reverb(buf, mix=0.24, predelay=0.028):
    combs = [(1609, 0.845), (1949, 0.828), (2311, 0.806)]
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

fade = int(3.5 * SR)
for i in range(fade):
    g = (1.0 - i / fade) ** 1.4
    left[N - fade + i] *= g
    right[N - fade + i] *= g

peak = max(max(abs(v) for v in left), max(abs(v) for v in right)) or 1.0
norm = 1.45 / peak                  # 세게 밀어 넣고 tanh 로 눌러 = 록다운 압축감

frames = array.array("h")
for i in range(N):
    for v in (left[i], right[i]):
        frames.append(int(math.tanh(v * norm) * 31800))

OUT = "rock.wav"
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(frames.tobytes())

print(f"완성: {OUT}   {int(DUR // 60)}분 {DUR % 60:.0f}초 / {BPM} BPM / E minor")
