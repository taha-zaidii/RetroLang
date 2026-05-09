/* ===================================================================
   Web Audio chiptune SFX. No audio files — every sound is synthesised
   from oscillators on demand. Browsers require a user gesture before
   AudioContext can play, so we lazy-init on first call.
   =================================================================== */

window.Retro = window.Retro || {};

Retro.SFX = (function () {
  let ctx = null;
  let enabled = true;
  let lastTick = 0;

  function ensure() {
    if (ctx) return ctx;
    try {
      const Ctor = window.AudioContext || window.webkitAudioContext;
      if (!Ctor) return null;
      ctx = new Ctor();
    } catch (e) { ctx = null; }
    return ctx;
  }

  function envelope(freq, durSec, type = 'square', vol = 0.06) {
    if (!enabled) return;
    const c = ensure();
    if (!c) return;
    if (c.state === 'suspended') c.resume();
    const t0 = c.currentTime;
    const osc = c.createOscillator();
    const gn  = c.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    gn.gain.setValueAtTime(0, t0);
    gn.gain.linearRampToValueAtTime(vol, t0 + 0.005);
    gn.gain.exponentialRampToValueAtTime(0.0001, t0 + Math.max(0.02, durSec));
    osc.connect(gn).connect(c.destination);
    osc.start(t0);
    osc.stop(t0 + durSec + 0.04);
  }

  return {
    set enabled(v) { enabled = !!v; },
    get enabled()  { return enabled; },
    /** Brief sub-perceptual click — throttled so holding a key doesn't drone. */
    tick() {
      const now = performance.now();
      if (now - lastTick < 35) return;
      lastTick = now;
      envelope(1200, 0.025, 'square', 0.025);
    },
    beep(freq, dur = 0.08, type = 'square', vol = 0.06) {
      envelope(freq, dur, type, vol);
    },
    chord(freqs, dur = 0.16) {
      freqs.forEach(f => envelope(f, dur, 'triangle', 0.04));
    },
    coin() {
      // Two-step coin-insert ding
      envelope(880,  0.06, 'square', 0.06);
      setTimeout(() => envelope(1320, 0.10, 'square', 0.06), 70);
    },
    boot() {
      // Power-on sweep
      const c = ensure();
      if (!c || !enabled) return;
      if (c.state === 'suspended') c.resume();
      const t0 = c.currentTime;
      const osc = c.createOscillator();
      const gn  = c.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(80, t0);
      osc.frequency.exponentialRampToValueAtTime(660, t0 + 0.45);
      gn.gain.setValueAtTime(0, t0);
      gn.gain.linearRampToValueAtTime(0.05, t0 + 0.05);
      gn.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.55);
      osc.connect(gn).connect(c.destination);
      osc.start(t0);
      osc.stop(t0 + 0.6);
    },
    gameOver() {
      const seq = [440, 392, 349, 294, 220];
      seq.forEach((f, i) => setTimeout(() => envelope(f, 0.18, 'triangle', 0.06), i * 130));
    },
  };
})();
