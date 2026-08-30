// =====================================================================
//  Spy Action Cue  --  164 BPM in 5/4  --  G minor
//  56 bars : intro4 / perc4 / A8 / A2-brass8 / B-theme8 / break4 / C8 / D8 / outro4
//
//  5/4 means one cycle = 10 eighth-note slots, grouped 3+2.
//  Ctrl+Enter = play/update     Ctrl+. = stop
// =====================================================================

setcps(164 / 60 / 5); // 5 beats per bar, not 4

// --- the engine : a bass ostinato that never rests --------------------
// ROOT walks over 8 bars; OST is the 10-slot shape added on top of it.
const ROOT = "<31 31 31 31 31 31 27 29>"; // G G G G G G Eb F  (MIDI numbers)
const ROOT_DARK = "<31 31 25 25 27 27 29 26>"; // with the phrygian bII (Db)

const OST = "<[0!8 3 5] [0!8 -2 -4]>"; // 8 x root, then push up / fall away
const OST_HI = "<[0!2 12 0!3 12 0 3 5] [0!8 -2 -4]>"; // octave jumps for the climax

const mkBass = (root, shape, g) =>
  note(shape)
    .add(note(root))
    .s("sawtooth")
    .lpf(1100)
    .decay(0.09)
    .sustain(0)
    .gain(g)
    .distort(1.6);

const bassLow = mkBass(ROOT, OST, 0.8);
const bassDark = mkBass(ROOT_DARK, OST, 0.85);
const bassHi = mkBass(ROOT_DARK, OST_HI, 0.9);

// --- percussion : 3+2 is what makes it limp forward -------------------
//     slot:      0 1 2 3 4 5 6 7 8 9
const KICK = "bd ~ ~ ~ ~ ~ bd ~ ~ ~";
const SNAR = "~ ~ ~ sd ~ ~ ~ ~ sd ~";
const BGHI = "~ ~ ht ~ ~ ht ~ ht ~ ht"; // bongo-ish high tom
const BGLO = "mt ~ ~ ~ mt ~ mt ~ ~ ~";

const percSoft = stack(
  s(KICK).gain(0.6),
  s(BGHI).gain(0.32),
  s(BGLO).gain(0.34),
)
  .bank("RolandTR808")
  .room(0.3);

const percFull = stack(
  s(KICK).gain(0.9),
  s(SNAR).gain(0.5),
  s(BGHI).gain(0.4),
  s(BGLO).gain(0.42),
  s("hh*10").gain("[0.14 0.08 0.08]*3 0.08"),
)
  .bank("RolandTR808")
  .room(0.3);

const percBig = stack(
  s(KICK).gain(1),
  s(SNAR).gain(0.55),
  s(BGHI).gain(0.45),
  s(BGLO).gain(0.46),
  s("hh*10").gain("[0.16 0.09 0.09]*3 0.09"),
  s("ma*20").gain(0.1),
  s("~ ~ ~ ~ ~ ~ ~ ~ ~ cb").gain(0.22),
)
  .bank("RolandTR808")
  .room(0.35);

// --- brass stabs : short, loud, on the 3+2 accents --------------------
const stabs = note("<[g2,d3,g3] [g2,d3,g3] [g2,d3,g3] [g2,d3,g3]>")
  .struct("x ~ ~ ~ ~ ~ x ~ ~ ~")
  .s("gm_brass_section")
  .attack(0.01)
  .decay(0.12)
  .sustain(0.3)
  .release(0.1)
  .lpf(3400)
  .gain(0.7)
  .room(0.4);

const stabsHard = stabs.struct("x ~ ~ ~ x ~ x ~ ~ ~").gain(0.78);

// --- spy guitar -------------------------------------------------------
// numbers = scale degrees in G minor.  @n = hold n slots (10 per bar).
const gtr = (pat, g) =>
  n(pat)
    .scale("G4:minor")
    .s("gm_electric_guitar_clean")
    .lpf(5000)
    .gain(g)
    .room(0.7)
    .delay(0.25)
    .delaytime(0.2)
    .delayfeedback(0.3)
    .pan(0.36);

const THEME = `<[0@2 2 0 4@2 2@2 0@2] [0@2 2 0 5@4 4@2]
   [4@2 3 2 0@2 2@2 4@2] [5@4 4@2 2@2 0@2]
   [0@2 2 0 4@2 2@2 0@2] [0@2 2 0 6@4 5@2]
   [6@2 5@2 4@2 2@2 4@2] [7@6 5@4]>`;

const theme = gtr(THEME, 0.7);
const riff = gtr("<[0@6 2@4]>", 0.42).sub(note(12)); // skeletal, an octave down

// --- climax : flute doubles the brass an octave up --------------------
const CLIMAX = `<[7@3 6 5@2 7@4] [6@2 5@2 4@6] [5@3 4 2@2 5@4] [4@4 2@2 0@4]
   [7@3 8 9@6] [8@2 7@2 6@6] [7@2 6@2 5@2 4@2 2@2] [7]>`;

const climaxFlute = n(CLIMAX)
  .scale("G4:minor")
  .add(note(12))
  .s("gm_flute")
  .gain(0.6)
  .room(0.6)
  .pan(0.62);

const climaxBrass = n(CLIMAX)
  .scale("G4:minor")
  .sub(note(12))
  .s("gm_brass_section")
  .lpf(3200)
  .gain(0.5)
  .room(0.45)
  .pan(0.42);

// --- arrangement ------------------------------------------------------
$: arrange(
  [4, bassLow],
  [4, stack(bassLow, percSoft)],
  [8, stack(bassLow, percFull, riff)],
  [8, stack(bassLow, percFull, stabs)],
  [8, stack(bassLow, percFull, theme)],
  [4, stack(bassDark, percSoft)],
  [8, stack(bassDark, percBig, stabsHard, riff)],
  [8, stack(bassHi, percBig, stabsHard, climaxBrass, climaxFlute)],
  [4, stack(bassLow, percSoft)],
);

// --- things to try ----------------------------------------------------
//  * setcps(164/60/5) -> setcps(164/60/4)   : same notes, now in 4/4.
//    the whole spy feeling evaporates. that is how much the 5 is doing.
//  * "G4:minor" -> "G4:phrygian"            : bII everywhere, much nastier
//  * theme : add .jux(rev)                  : stereo chase
//  * percBig : add .sometimesBy(.15, x => x.speed(2))
//  * comment out a line in arrange() to hear one section alone
