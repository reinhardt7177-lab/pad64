// =====================================================================
//  Ballad in B minor  --  74 BPM  --  Bm / G / D / A
//  28 bars : intro 4 / verse 8 / pre-chorus 4 / chorus 8 / outro 4
//
//  Ctrl+Enter = play/update     Ctrl+. = stop
// =====================================================================

setcps(74 / 60 / 4); // 74 BPM, 4 beats per bar

// --- harmony ---------------------------------------------------------
// one chord per bar, looping:  Bm  ->  G  ->  D/A  ->  A
const PROG = "<[b3,d4,f#4,a4] [g3,b3,d4,f#4] [a3,d4,f#4,a4] [a3,c#4,e4,a4]>";
const ROOT = "<b1 g1 d2 a1>";

// --- instruments -----------------------------------------------------

// warm pad : the blanket everything else sits on
const pad = note(PROG)
  .s("gm_pad_2_warm")
  .attack(0.9)
  .release(1.6)
  .lpf(900)
  .room(0.8)
  .gain(0.42);

// piano arpeggio, quarter notes -- sparse, for intro / outro
const arpSoft = note(PROG)
  .arp("up")
  .s("gm_acoustic_grand_piano")
  .gain("0.62 0.4 0.5 0.4")
  .room(0.55);

// piano arpeggio, busier -- verse / pre-chorus
const arpFull = note(PROG)
  .arp("updown")
  .s("gm_acoustic_grand_piano")
  .gain("0.6 0.38 0.44 0.38 0.5 0.38")
  .room(0.5);

// block chords on beats 1 and 3 -- the chorus lift
const keys = note(PROG)
  .struct("x ~ x ~")
  .s("gm_acoustic_grand_piano")
  .gain(0.6)
  .room(0.45)
  .legato(0.95);

const bassVerse = note(ROOT)
  .struct("x ~ ~ [~ x]")
  .s("gm_acoustic_bass")
  .lpf(700)
  .legato(0.9)
  .gain(0.8);

const bassBig = note(ROOT)
  .struct("x ~ x x")
  .s("gm_acoustic_bass")
  .lpf(800)
  .legato(0.85)
  .gain(0.9);

// --- drums -----------------------------------------------------------
const drumsVerse = stack(
  s("bd ~ [~ bd] ~").gain(0.75),
  s("~ rim ~ rim").gain(0.3),
  s("hh*8").gain("[0.26 0.15]*4"),
)
  .bank("RolandTR808")
  .room(0.25);

const drumsPre = stack(
  s("bd ~ [~ bd] ~").gain(0.8),
  s("~ sd ~ sd").gain(0.34),
  s("hh*16").gain("[0.2 0.09 0.13 0.09]*4"),
)
  .bank("RolandTR808")
  .room(0.25);

const drumsChorus = stack(
  s("bd ~ [~ bd] ~").gain(0.95),
  s("~ sd ~ sd").gain(0.55),
  s("hh*8").gain("[0.3 0.18]*4"),
  s("~ ~ ~ ~ ~ ~ ~ oh").gain(0.22),
)
  .bank("RolandTR808")
  .room(0.3);

// --- melody ----------------------------------------------------------
// numbers = scale degrees in B minor.  @n = hold for n eighth-notes.

const leadPre = n("<[~@2 0@2 1@2 2@2] [3@2 2@2 1@3 ~] [2@2 3@2 4@4] [4@2 5@2 4@3 ~]>")
  .scale("B4:minor")
  .s("gm_lead_2_sawtooth")
  .lpf(2000)
  .gain(0.34)
  .room(0.6)
  .delay(0.3)
  .delaytime(0.375)
  .delayfeedback(0.35);

const leadChorus = n(
  `<[2@3 4 5@4] [4@2 3@2 2@4] [1 2 3@2 4@4] [2@4 0@4]
    [2@3 4 6@4] [5@2 4@2 3@4] [4 3 2@2 1@4] [0]>`,
)
  .scale("B4:minor")
  .s("gm_lead_2_sawtooth")
  .lpf(2400)
  .gain(0.46)
  .room(0.6)
  .delay(0.35)
  .delaytime(0.375)
  .delayfeedback(0.35);

// --- arrangement -----------------------------------------------------
$: arrange(
  [4, stack(pad, arpSoft)],
  [8, stack(pad, arpFull, bassVerse, drumsVerse)],
  [4, stack(pad, arpFull, bassBig, drumsPre, leadPre)],
  [8, stack(pad, keys, arpFull, bassBig, drumsChorus, leadChorus)],
  [4, stack(pad, arpSoft)],
);

// --- things to try ---------------------------------------------------
//  * change 74 to 90  ->  whole song speeds up
//  * "B4:minor"  ->  "B4:dorian"  or  "B4:phrygian"   (mood swap)
//  * add .jux(rev) to leadChorus  ->  stereo split
//  * add .sometimesBy(.25, x => x.speed(2)) to drumsChorus
//  * comment out a line in arrange() to solo a section
