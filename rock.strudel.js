// =====================================================================
//  Rock Ballad in E minor  --  80 BPM  --  Em / C / G / D
//  40 bars : intro 4 / verse 8 / pre 4 / chorus 8 / break 4 / last 8 / outro 4
//
//  Ctrl+Enter = play/update     Ctrl+. = stop
// =====================================================================

setcps(80 / 60 / 4); // 80 BPM

// --- harmony ---------------------------------------------------------
const POWER = "<[e2,b2,e3] [c3,g3,c4] [g2,d3,g3] [d3,a3,d4]>"; // power chords
const CLEAN = "<[e3,g3,b3,e4] [c3,e3,g3,c4] [d3,g3,b3,d4] [d3,f#3,a3,d4]>";
const ROOT = "<e1 c2 g1 d2>";

// --- guitars ---------------------------------------------------------

// clean arpeggio -- intro / verse / break / outro
const gtrClean = note(CLEAN)
  .arp("updown")
  .s("gm_electric_guitar_clean")
  .gain("0.55 0.36 0.42 0.36 0.48 0.36")
  .room(0.45)
  .pan(0.38);

// palm-muted chugs -- pre-chorus tension
const gtrMute = note(POWER)
  .struct("x ~ x ~ x ~ x ~")
  .s("gm_electric_guitar_muted")
  .gain(0.55)
  .lpf(3200)
  .room(0.2);

// the wall : power chords, doubled hard left + hard right
const gtrHeavy = stack(
  note(POWER).struct("x@2 x x").pan(0.12),
  note(POWER).struct("x@2 x x").pan(0.88).late(0.006),
)
  .s("gm_distortion_guitar")
  .gain(0.6)
  .lpf(4400)
  .room(0.3);

const gtrLastAdd = note(POWER)
  .struct("~ ~ ~ ~ ~ x ~ x")
  .s("gm_distortion_guitar")
  .gain(0.4)
  .lpf(4400)
  .jux(rev);

// --- bass ------------------------------------------------------------
const bassSlow = note(ROOT)
  .struct("x ~ x ~")
  .s("gm_electric_bass_pick")
  .lpf(900)
  .legato(0.9)
  .gain(0.85);

const bassDrive = note(ROOT)
  .struct("x ~ x [x x]")
  .s("gm_electric_bass_pick")
  .lpf(1000)
  .legato(0.85)
  .gain(0.95);

// --- drums -----------------------------------------------------------
// verse is HALF-TIME : kick on 1, snare on 3.  that is what makes it drag.
const drVerse = stack(
  s("bd ~ ~ ~ ~ ~ [~ bd] ~").gain(0.8),
  s("~ ~ ~ ~ sd ~ ~ ~").gain(0.5),
  s("hh*8").gain("[0.24 0.14]*4"),
)
  .bank("RolandTR909")
  .room(0.3);

const drPre = stack(
  s("bd ~ ~ ~ ~ bd ~ ~").gain(0.85),
  s("~ ~ ~ ~ sd ~ ~ ~").gain(0.5),
  s("hh*16").gain("[0.2 0.08 0.12 0.08]*4"),
)
  .bank("RolandTR909")
  .room(0.3);

const drBig = stack(
  s("bd ~ ~ bd ~ bd ~ ~").gain(1),
  s("~ ~ sd ~ ~ ~ sd ~").gain(0.85),
  s("hh*8").gain("[0.26 0.16]*4"),
  s("~ ~ ~ ~ ~ ~ ~ oh").gain(0.2),
)
  .bank("RolandTR909")
  .room(0.35);

const drBreak = stack(
  s("bd ~ ~ ~ ~ ~ ~ ~").gain(0.6),
  s("~ ~ ~ ~ rim ~ ~ ~").gain(0.4),
)
  .bank("RolandTR909")
  .room(0.4);

// --- pad -------------------------------------------------------------
const pad = note(CLEAN)
  .s("gm_string_ensemble_1")
  .attack(1)
  .release(2)
  .lpf(1100)
  .room(0.8)
  .gain(0.3);

// --- lead guitar -----------------------------------------------------
// numbers = scale degrees in E minor.  @n = hold n eighth-notes.
const solo = (pat, g) =>
  n(pat)
    .scale("E4:minor")
    .s("gm_distortion_guitar")
    .lpf(3600)
    .gain(g)
    .room(0.6)
    .delay(0.3)
    .delaytime(0.375)
    .delayfeedback(0.3)
    .pan(0.58);

const leadPre = solo(
  "<[0@2 1@2 2@3 1] [2@3 3 2@4] [3@2 4@2 5@4] [4@2 5@2 6@4]>",
  0.4,
);

const leadChorus = solo(
  `<[4@4 2@4] [3@2 4@2 5@4] [4@3 3 2@4] [0@4 2@4]
    [4@4 5@4] [6@2 5@2 4@4] [5@3 4 3@4] [4]>`,
  0.62,
);

// last chorus climbs higher and peaks on degree 9
const leadLast = solo(
  `<[4@4 5@4] [6@2 7@2 6@4] [7@3 6 5@4] [7@4 4@4]
    [8@4 9@4] [9@2 8@2 7@4] [7@3 6 5@4] [4]>`,
  0.66,
);

// --- arrangement -----------------------------------------------------
$: arrange(
  [4, stack(pad, gtrClean)],
  [8, stack(pad, gtrClean, bassSlow, drVerse)],
  [4, stack(pad, gtrMute, bassDrive, drPre, leadPre)],
  [8, stack(pad, gtrHeavy, bassDrive, drBig, leadChorus)],
  [4, stack(pad, gtrClean, bassSlow, drBreak)],
  [8, stack(pad, gtrHeavy, gtrLastAdd, bassDrive, drBig, leadLast)],
  [4, stack(pad, gtrClean)],
);

// --- things to try ---------------------------------------------------
//  * gtrHeavy : add .distort(1.4)          -> even more saturation
//  * "E4:minor" -> "E4:harmonicMinor"      -> instant power-ballad drama
//  * drBig : add .sometimesBy(.2, x => x.speed(1.5))
//  * swap gm_distortion_guitar for gm_overdriven_guitar  -> lighter crunch
//  * comment out a line in arrange() to hear one section alone
