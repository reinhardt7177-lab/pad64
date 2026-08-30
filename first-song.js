// ─────────────────────────────────────────────
//  Strudel 첫 곡 — https://strudel.cc 에 통째로 붙여넣고 Ctrl+Enter
//  A minor / 4마디 루프 / 120 BPM
// ─────────────────────────────────────────────

setcps(120 / 60 / 4); // 120 BPM (4/4 기준)

const PROG = "<Am7 Fmaj7 Cmaj7 G7>"; // 한 마디에 코드 하나씩

// 1) 드럼 ─ 킥/스네어/하이햇을 한 줄에 겹쳐서 (쉼표 = 동시에)
$: s("bd*2, ~ sd, hh*8")
  .bank("RolandTR909")
  .gain("1 .8")          // 강약을 번갈아
  .room(0.2);

// 2) 베이스 ─ 코드 근음을 옥타브 아래로
$: note("<a1 f1 c2 g1>")
  .s("gm_electric_bass_pick")
  .gain(0.7)
  .legato(0.9)
  .lpf(1200);

// 3) 코드 ─ 일렉피아노로 깔아주기
$: chord(PROG)
  .voicing()             // 코드 이름 → 실제 음 배치
  .s("gm_epiano1")
  .gain(0.45)
  .room(0.5)
  .delay(0.25);

// 4) 멜로디 ─ 스케일 위에서 자리번호로 연주
$: n("0 2 4 [6 5] ~ 4 2 ~")
  .scale("A:minor")
  .s("gm_lead_1_square")
  .gain(0.4)
  .cutoff(sine.range(600, 3000).slow(8)) // 필터가 8마디에 걸쳐 열렸다 닫힘
  .room(0.4)
  .pan(0.4);

// ─── 놀아볼 곳 ────────────────────────────────
//  • hh*8  →  hh*16 으로 바꿔보기
//  • .rev() 붙이면 거꾸로, .jux(rev) 붙이면 좌우 스테레오로 갈라짐
//  • .sometimesBy(0.3, x => x.speed(2)) 로 랜덤 변주
//  • 줄 맨 앞 $: 를 _$: 로 바꾸면 그 파트만 음소거
