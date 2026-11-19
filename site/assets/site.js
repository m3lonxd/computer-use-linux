/* Computer Use Linux — site davranışı.
   Tek rAF kaydırma döngüsü (oku → yaz), IntersectionObserver ile görünme,
   ekran dışındaki animasyonlar durur. prefers-reduced-motion: son durum, hareket yok. */
(function () {
  "use strict";

  var D = document, H = D.documentElement;
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* özel pencere */ } }
  };
  var mm = function (q) { return !!(window.matchMedia && window.matchMedia(q).matches); };
  var reduced = mm("(prefers-reduced-motion: reduce)");
  var fine = mm("(hover: hover) and (pointer: fine)");
  var hasIO = "IntersectionObserver" in window;
  function $(s, r) { return (r || D).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || D).querySelectorAll(s)); }
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  function ss(a, b, x) { var t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  // ------------------------------------------------------------------ dil
  // İlk ziyarette Türkçe tarayıcıyı /tr/'ye yönlendir; seçim yapıldıysa ona uy.
  var lang = H.lang;
  if (!store.get("nr-lang") && lang === "en" &&
      /^tr\b/i.test((navigator.languages && navigator.languages[0]) || navigator.language || "")) {
    location.replace("/tr/" + location.hash);
    return;
  }
  $$("[data-lang]").forEach(function (a) {
    a.addEventListener("click", function () { store.set("nr-lang", a.dataset.lang); });
  });

  // ----------------------------------------------------------------- tema
  var themeBtn = $(".theme");
  if (themeBtn) themeBtn.addEventListener("click", function () {
    var cur = H.dataset.theme || "dark"; // koyu varsayılan; açık tema yalnızca seçilince
    var next = cur === "dark" ? "light" : "dark";
    H.dataset.theme = next;
    store.set("nr-theme", next);
  });

  // -------------------------------------------------------------- kopyala
  $$("[data-copy]").forEach(function (btn) {
    var lab = $("[data-label]", btn), label = lab.textContent, timer;
    btn.addEventListener("click", function () {
      var el = $(btn.dataset.copy);
      if (!el) return;
      var text = el.dataset.full || el.textContent;
      var done = function () {
        btn.classList.add("done"); lab.textContent = btn.dataset.done || label;
        clearTimeout(timer);
        timer = setTimeout(function () { btn.classList.remove("done"); lab.textContent = label; }, 1700);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { selectText(el); });
      } else selectText(el);
    });
  });
  function selectText(el) {
    var r = D.createRange(); r.selectNodeContents(el);
    var s = getSelection(); s.removeAllRanges(); s.addRange(r);
  }

  // ------------------------------------------------------------- sekmeler
  function visitorOS() {
    var p = ((navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || navigator.userAgent || "").toLowerCase();
    return /win/.test(p) ? "windows" : /mac|iphone|ipad/.test(p) ? "macos" : "linux";
  }
  $$("[data-tabs]").forEach(function (root) {
    var list = $('[role="tablist"]', root), ind = $(".tab-ind", root);
    var tabs = $$('[role="tab"]', root);
    function place(tab) {
      if (!ind) return;
      list.classList.add("has-ind");
      ind.style.transform = "translateX(" + tab.offsetLeft + "px) scaleX(" + (tab.offsetWidth / 100) + ")";
    }
    function select(tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab, panel = D.getElementById(t.getAttribute("aria-controls"));
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.tabIndex = on ? 0 : -1;
        panel.hidden = !on;
        if (on && !reduced) { panel.classList.remove("show"); void panel.offsetWidth; panel.classList.add("show"); }
      });
      place(tab);
      if (focus) tab.focus();
    }
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function () { select(t); });
      t.addEventListener("keydown", function (e) {
        var j = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 :
                e.key === "Home" ? 0 : e.key === "End" ? tabs.length - 1 : null;
        if (j === null) return;
        e.preventDefault();
        select(tabs[(j + tabs.length) % tabs.length], true);
      });
    });
    var cur = function () { return tabs.filter(function (t) { return t.getAttribute("aria-selected") === "true"; })[0] || tabs[0]; };
    // Kurulum sekmeleri ziyaretçinin işletim sistemiyle açılır. Paneller HTML'de
    // gizli değildir (JS yoksa hepsi görünür); gizleme burada yapılır.
    var first = cur();
    if (root.hasAttribute("data-os-tabs")) first = tabs.filter(function (t) { return t.dataset.os === visitorOS(); })[0] || first;
    tabs.forEach(function (t) {
      var on = t === first;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
      D.getElementById(t.getAttribute("aria-controls")).hidden = !on;
    });
    place(cur());
    if (D.fonts && D.fonts.ready) D.fonts.ready.then(function () { place(cur()); });
    addEventListener("resize", function () { place(cur()); });
  });

  // -------------------------------------------------------------- görünme
  // Her öğe bir kez görünür; "reveal" olayı bileşenlere haber verir.
  $$("[data-stagger]").forEach(function (p) {
    var i = 0;
    Array.prototype.forEach.call(p.children, function (c) {
      if (c.hasAttribute("data-reveal")) c.style.setProperty("--i", i++);
    });
  });
  function revealed(el) {
    el.classList.add("in");
    el.dispatchEvent(new CustomEvent("reveal"));
  }
  var revealEls = $$("[data-reveal]");
  if (reduced || !hasIO) {
    revealEls.forEach(revealed);
  } else {
    var rio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { rio.unobserve(e.target); revealed(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0 });
    revealEls.forEach(function (el) { rio.observe(el); });
  }
  function onReveal(el, fn) {
    if (!el) return;
    if (el.classList.contains("in")) fn(); else el.addEventListener("reveal", fn, { once: true });
  }
  // Görünürlük takibi (animasyonları ekran dışında durdurmak için)
  function watch(el, fn, margin) {
    if (!el) return;
    if (!hasIO) { fn(true); return; }
    new IntersectionObserver(function (es) { fn(es[es.length - 1].isIntersecting); },
                             { rootMargin: margin || "0px" }).observe(el);
  }

  // ---------------------------------------------- tek kaydırma döngüsü
  var tasks = [], ticking = false;
  function schedule() { if (!ticking) { ticking = true; requestAnimationFrame(frame); } }
  function frame() {
    ticking = false;
    var vh = innerHeight, i, writes = [];
    for (i = 0; i < tasks.length; i++) writes.push(tasks[i](vh));       // önce okumalar
    for (i = 0; i < writes.length; i++) if (writes[i]) writes[i]();       // sonra yazmalar
  }
  addEventListener("scroll", schedule, { passive: true });
  addEventListener("resize", schedule);

  // ilerleme çubuğu + üst barın koyu bantlar üstündeki rengi
  var bar = $("[data-progress-bar]"), top = $(".top"), bands = $$(".band");
  tasks.push(function () {
    var max = H.scrollHeight - innerHeight, p = max > 0 ? scrollY / max : 0;
    var over = bands.some(function (b) { var r = b.getBoundingClientRect(); return r.top <= 70 && r.bottom > 70; });
    return function () {
      if (bar) bar.style.transform = "scaleX(" + p.toFixed(4) + ")";
      if (top) top.classList.toggle("tk-band", over);
    };
  });

  // gezinme: geçerli bölüm
  var navLinks = $$(".nav a");
  var navSecs = navLinks.map(function (a) { return D.getElementById(a.getAttribute("href").slice(1)); });
  tasks.push(function (vh) {
    var cur = -1;
    navSecs.forEach(function (s, i) {
      if (!s) return;
      var r = s.getBoundingClientRect();
      if (r.top <= vh * 0.4 && r.bottom > vh * 0.4) cur = i;
    });
    return function () { navLinks.forEach(function (a, i) { a.classList.toggle("on", i === cur); }); };
  });

  if (!reduced) {
    // koyu bantlar: içeri girerken kenarlardan açılır (clip-path)
    $$("[data-wipe]").forEach(function (el) {
      tasks.push(function (vh) {
        var r = el.getBoundingClientRect();
        if (r.top > vh || r.bottom < 0) return null;
        var p = ss(0, 1, (vh - r.top) / (vh * 0.65)), inset = (1 - p) * Math.min(innerWidth * 0.035, 56), rad = (1 - p) * 28;
        return function () { el.style.clipPath = p >= 1 ? "none" : "inset(0 " + inset.toFixed(1) + "px round " + rad.toFixed(1) + "px)"; };
      });
    });

    // ızgara ve büyük numaralar: hafif paralaks
    $$("[data-parallax]").forEach(function (el) {
      var big = el.classList.contains("bignum");
      var host = big ? el.parentNode : (el.closest("section") || el.parentNode);
      var k = big ? -0.1 : 0.1, lim = big ? (innerWidth < 760 ? 12 : 40) : 1e4;
      tasks.push(function (vh) {
        var r = host.getBoundingClientRect();
        if (r.top > vh || r.bottom < 0) return null;
        var y = clamp((r.top + r.height / 2 - vh / 2) * k, -lim, lim);
        return function () { el.style.transform = "translate3d(0," + y.toFixed(1) + "px,0)"; };
      });
    });
  }

  // ================================================== döngü videoları
  // Hero ve "terminaller" bölümünün arka planı. Fotoğraf (poster) hep altta durur;
  // video yalnızca oynatılabiliyorsa üstüne biner. Veri tasarrufu ve azaltılmış
  // hareket tercihinde video hiç indirilmez; ekran dışındaki video durur; ikinci
  // video (data-gec) görünür olana dek yüklenmez.
  (function () {
    var videos = $$("video.dongu");
    if (!videos.length) return;
    var saveData = false;
    try { saveData = !!(navigator.connection && navigator.connection.saveData); } catch (e) {}
    if (saveData || reduced) {
      videos.forEach(function (v) { v.removeAttribute("autoplay"); v.pause(); v.remove(); });
      return;
    }
    function play(v) {
      if (v.hasAttribute("data-gec")) { v.removeAttribute("data-gec"); v.preload = "auto"; v.load(); }
      var p = v.play();
      // Otomatik oynatma engellenirse alttaki fotoğraf görünür kalır. pause() ile
      // kesilen play() (AbortError) bir sonraki görünüşte yeniden denenir.
      if (p && p.catch) p.catch(function (err) { if (err && err.name === "NotAllowedError") v.remove(); });
    }
    if (hasIO) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { if (en.isIntersecting) play(en.target); else en.target.pause(); });
      }, { rootMargin: "200px 0px" });
      videos.forEach(function (v) { io.observe(v); });
    } else {
      videos.forEach(play);
    }
  })();

  // ============================================ etkileşimli klavye (hero)
  // Hero fotoğrafındaki her tuş kapağının üst yüzeyi (1920x1072 görsel uzayında bir dörtgen).
  // Fare bir kapağın üstüne gelince o kapak yumuşakça iner, hafif kararır, üstünde koyu
  // aralık açılır; fare çıkınca geri kalkar. Yama, videonun üstünde ama koyu gradyanın altında durur.
  // Hit-test elementFromPoint ile değil, fare konumunun görsel uzayına çevrilip dörtgende
  // nokta testi yapılmasıyla; metin ve düğmeler olduğu gibi tıklanır. Dokunmatikte kapalı.
  if (fine) (function () {
    var hero = $(".hero"), bg = hero && $(".v-bg", hero), img = bg && $("img.v-media", bg);
    if (!img) return;
    var IW = 1920, IH = 1072, NS = "http://www.w3.org/2000/svg";
    var KEYS = [
      ["Esc",[710,717,793,683,860,728,767,764]],
      ["~",[810,805,903,773,970,820,872,861]],
      ["1",[970,757,1053,716,1125,765,1040,811]],
      ["Tab",[909,915,1066,852,1154,905,968,957]],
      ["F1",[1000,605,1083,579,1147,628,1057,654]],
      ["F2",[1138,562,1223,529,1282,573,1200,609]],
      ["F3",[1268,510,1348,479,1417,530,1337,556]],
      ["2",[1123,700,1205,664,1270,713,1197,759]],
      ["3",[1268,642,1348,611,1402,647,1320,691]],
      ["E",[1433,727,1515,689,1597,743,1505,776]],
      ["W",[1288,787,1365,751,1450,803,1352,849]],
      ["S",[1402,885,1488,848,1567,900,1488,941]],
      ["Z",[1435,1015,1528,980,1600,1028,1515,1066]],
      ["X",[1583,957,1670,919,1750,965,1660,1001]],
      ["D",[1555,810,1638,776,1722,833,1635,874]],
      ["C",[1728,890,1802,860,1892,900,1813,936]],
      ["G",[1713,737,1795,706,1870,763,1798,796]],
      ["F5",[1508,420,1583,390,1650,438,1577,466]],
      ["F6",[1628,375,1695,352,1767,398,1703,418]],
      ["F7",[1746,335,1800,309,1880,358,1815,378]],
      ["4",[1400,600,1480,559,1555,610,1470,646]],
      ["6",[1540,540,1615,509,1687,563,1615,586]],
      ["7",[1665,497,1743,461,1812,510,1732,544]],
      ["8",[1795,445,1868,413,1937,460,1870,491]],
      ["Y",[1711,613,1797,579,1865,626,1776,658]],
      ["A",[1251,942,1337,906,1415,952,1329,985]],
      ["T",[1577,668,1655,632,1734,686,1642,714]],
      ["Q",[1137,874,1198,839,1299,898,1214,928]],
      ["Caps",[1008,1041,1189,962,1263,1016,1099,1073]]
    ];
    var svg = D.createElementNS(NS, "svg"), defs = D.createElementNS(NS, "defs"), g = D.createElementNS(NS, "g");
    svg.setAttribute("class", "keys"); svg.setAttribute("aria-hidden", "true");
    svg.appendChild(defs); svg.appendChild(g);
    var polys = [], pics = [];
    function mk(tag, attrs, parent) {
      var el = D.createElementNS(NS, tag);
      Object.keys(attrs).forEach(function (k) { el.setAttribute(k, attrs[k]); });
      parent.appendChild(el); return el;
    }
    var WALL = 34;   // ön duvarın görünen yüksekliği (1920x1072 uzayı)
    var SKIP = { Q: 1 };   // fotoğrafta zaten basılı
    function hull(P) {
      P = P.slice().sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
      function cr(o, a, b) { return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); }
      var lo = [], up = [], i;
      for (i = 0; i < P.length; i++) { while (lo.length > 1 && cr(lo[lo.length - 2], lo[lo.length - 1], P[i]) <= 0) lo.pop(); lo.push(P[i]); }
      for (i = P.length - 1; i >= 0; i--) { while (up.length > 1 && cr(up[up.length - 2], up[up.length - 1], P[i]) <= 0) up.pop(); up.push(P[i]); }
      return lo.slice(0, -1).concat(up.slice(0, -1));
    }
    function sweep(pts, cx, cy, f) {
      var b = pts.map(function (q) { return [cx + (q[0] - cx) * f, cy + (q[1] - cy) * f]; });
      return hull(b.concat(b.map(function (q) { return [q[0], q[1] + WALL]; })))
        .map(function (q) { return q[0].toFixed(1) + "," + q[1].toFixed(1); }).join(" ");
    }
    // Her tuş iki katman: sabit "yuva" (kapak silüetiyle aynı, koyu; basınca belirir)
    // ve kendi silüetine kırpılmış fotoğraf kapağı. Kırpma kapakla birlikte kayar, yuvanın
    // kırpması sabit kalır: kapak inerken üstünde koyu aralık açılır, ön duvarı yuvanın alt
    // kenarında kesilip kısalır. Fotoğrafın başka hiçbir parçası yer değiştirmez.
    KEYS.forEach(function (k, i) {
      if (SKIP[k[0]]) return;
      var c = k[1], pts = [], j, cx = 0, cy = 0;
      for (j = 0; j < 8; j += 2) pts.push([c[j], c[j + 1]]);
      pts.forEach(function (q) { cx += q[0] / 4; cy += q[1] / 4; });
      var sil = sweep(pts, cx, cy, 1.03), well = sil;
      mk("polygon", { points: well }, mk("clipPath", { id: "kw" + i }, defs));
      mk("polygon", { points: sil }, mk("clipPath", { id: "ks" + i }, defs));
      var kp = mk("g", { "class": "kp", "data-key": k[0], "clip-path": "url(#kw" + i + ")" }, g);
      mk("polygon", { "class": "kp-sh", points: well }, kp);
      var cap = mk("g", { "class": "kp-cap" }, kp);
      pics.push(mk("image", { width: IW, height: IH, preserveAspectRatio: "none", "clip-path": "url(#ks" + i + ")" }, cap));
      polys.push({ el: kp, pts: pts, name: k[0] });
    });
    bg.insertBefore(svg, null);

    function src() {
      var u = img.currentSrc || img.src;
      if (u) pics.forEach(function (p) { p.setAttribute("href", u); });
    }
    if (img.complete) src(); else img.addEventListener("load", src, { once: true });

    // object-fit: cover + object-position (CSS'teki değer) dönüşümü
    var sc = 1, ox = 0, oy = 0;
    function layout() {
      var w = bg.clientWidth, h = bg.clientHeight;
      sc = Math.max(w / IW, h / IH);
      var pos = (getComputedStyle(img).objectPosition || "50% 50%").split(" ");
      function off(v, free) { return /%$/.test(v) ? free * parseFloat(v) / 100 : parseFloat(v) || 0; }
      ox = off(pos[0], w - IW * sc); oy = off(pos[1] || "50%", h - IH * sc);
      g.setAttribute("transform", "translate(" + ox.toFixed(2) + " " + oy.toFixed(2) + ") scale(" + sc.toFixed(5) + ")");
    }
    layout();
    addEventListener("resize", layout);

    function inside(x, y, p) {
      var c = false, n = p.length, i, j = n - 1;
      for (i = 0; i < n; i++) {
        var xi = p[i][0], yi = p[i][1], xj = p[j][0], yj = p[j][1];
        if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) c = !c;
        j = i;
      }
      return c;
    }
    var cur = null, lx = -1, ly = -1, blocked = false;
    function press(k) {
      if (k === cur) return;
      if (cur) cur.el.classList.remove("on");
      cur = k;
      if (cur) cur.el.classList.add("on");
    }
    function test() {
      if (blocked || lx < 0) { press(null); return; }
      var r = bg.getBoundingClientRect();
      var x = (lx - r.left - ox) / sc, y = (ly - r.top - oy) / sc, i;
      if (cur && inside(x, y, cur.pts)) return;
      for (i = 0; i < polys.length; i++) if (inside(x, y, polys[i].pts)) { press(polys[i]); return; }
      press(null);
    }
    hero.addEventListener("pointermove", function (e) {
      if (e.pointerType && e.pointerType !== "mouse" && e.pointerType !== "pen") return;
      lx = e.clientX; ly = e.clientY;
      blocked = !!(e.target.closest && e.target.closest("a, button, .copyline"));
      test();
    });
    hero.addEventListener("pointerleave", function () { lx = -1; press(null); });
    addEventListener("scroll", function () { if (lx >= 0) test(); }, { passive: true });
    addEventListener("blur", function () { lx = -1; press(null); });
  })();

  // ====================================================== kayan şerit
  var marquee = $("[data-marquee]");
  if (marquee && !reduced) watch(marquee, function (v) { marquee.classList.toggle("on", v); });

  // ======================================= "Nasıl çalışır": sabit sahne
  // Tek parça sinematik sahne: oda, monitördeki şema, Tux ve kamera hareketi önceden render edilmiş
  // bir kare dizisidir (media/story-seq/<dil>/NNNN.webp). Kaydırma ilerlemesi p kareyi seçer, kare
  // tek bir <canvas>'a cover ölçekle çizilir. Kareler aşamalı yüklenir: önce her 8. kare, sonra
  // kalanlar; yüklenmemiş kare için en yakın yüklenmiş kare gösterilir. Dar ekranda ve azaltılmış
  // harekette sahne kurulmaz (adımlar düz liste kalır).
  var story = $("[data-story]");
  if (story) (function () {
    var pinMQ = window.matchMedia ? matchMedia("(min-width: 1000px)") : null;
    var rungs = $$("[data-rung]", story);
    var cv = $("canvas.sb-cv", story), card = $("[data-sc-in]", story);
    var ctx = cv && cv.getContext ? cv.getContext("2d", { alpha: false }) : null;
    var N = cv ? +cv.dataset.frames || 0 : 0, base = cv ? cv.dataset.seq : "";
    var saveData = false;
    try { saveData = !!(navigator.connection && navigator.connection.saveData); } catch (e) {}
    var frames = [], ready = [], loading = false, last = -1, drawn = -1, cw = 0, ch = 0;

    function pinned() { return !reduced && !!ctx && N > 0 && !!pinMQ && pinMQ.matches; }
    function pad(n) { return ("000" + n).slice(-4); }
    // yüklenmiş en yakın kare
    function nearest(i) {
      if (!ready.length) return -1;
      var best = ready[0], bd = Math.abs(best - i);
      for (var k = 1; k < ready.length; k++) { var d = Math.abs(ready[k] - i); if (d < bd) { bd = d; best = ready[k]; } }
      return best;
    }
    function startLoading() {
      if (loading || !ctx) return;
      loading = true;
      var order = [], i;
      for (i = 0; i < N; i += 8) order.push(i);
      if (order[order.length - 1] !== N - 1) order.push(N - 1);
      if (!saveData) { for (i = 0; i < N; i++) if (order.indexOf(i) < 0) order.push(i); }
      var pos = 0, active = 0;
      function one(idx) {
        var im = new Image(); frames[idx] = im; active++;
        im.onload = function () { active--; ready.push(idx); ready.sort(function (a, b) { return a - b; }); drawn = -1; schedule(); pump(); };
        im.onerror = function () { active--; frames[idx] = null; pump(); };
        im.decoding = "async";
        im.src = base + pad(idx + 1) + ".webp";
      }
      function pump() { while (active < 4 && pos < order.length) one(order[pos++]); }
      pump();
    }
    function sizeCanvas() {
      var w = cv.clientWidth, h = cv.clientHeight;
      if (!w || !h) return;
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      var pw = Math.min(Math.round(w * dpr), 1920), ph = Math.round(h * pw / w);
      if (pw !== cv.width || ph !== cv.height) { cv.width = pw; cv.height = ph; }
      cw = cv.width; ch = cv.height; drawn = -1;
    }
    function draw(i) {
      var k = nearest(i);
      if (k < 0 || !cw || k === drawn) return;
      var im = frames[k], iw = im.naturalWidth, ih = im.naturalHeight;
      if (!iw) return;
      var sc = Math.max(cw / iw, ch / ih), dw = iw * sc, dh = ih * sc;
      ctx.drawImage(im, (cw - dw) / 2, 0, dw, dh);
      drawn = k;
    }
    // adım kartı: aktif adımın başlık + metni, değişirken yumuşak geçiş
    var cardTimer = 0;
    function setCard(idx) {
      if (!card) return;
      var src = rungs[idx], n = $(".rung-n", src), h = $("h3", src), p = $("p", src);
      var fill = function () {
        card.innerHTML = "";
        var a = document.createElement("span"); a.className = "rung-n"; a.textContent = n ? n.textContent : String(idx + 1);
        var b = document.createElement("h3"); b.textContent = h ? h.textContent : "";
        var c = document.createElement("p"); c.textContent = p ? p.textContent : "";
        card.appendChild(a); card.appendChild(b); card.appendChild(c);
        card.classList.remove("out");
      };
      clearTimeout(cardTimer);
      if (!card.firstChild) { fill(); return; }
      card.classList.add("out");
      cardTimer = setTimeout(fill, 180);
    }

    function setPin() {
      var on = pinned();
      H.classList.toggle("story-pin", on);
      if (on) { sizeCanvas(); startLoading(); }
      schedule();
    }
    // sahneye yaklaşınca kareler yüklenmeye başlar
    if (hasIO && ctx) {
      var pre = new IntersectionObserver(function (en) {
        if (en[0].isIntersecting) { if (pinned()) startLoading(); pre.disconnect(); }
      }, { rootMargin: "1200px 0px" });
      pre.observe(story);
    }
    addEventListener("resize", function () { if (pinned()) { sizeCanvas(); schedule(); } });
    setPin();
    if (pinMQ && pinMQ.addEventListener) pinMQ.addEventListener("change", setPin);

    tasks.push(function (vh) {
      if (!pinned()) return null;
      var r = $(".rungs", story).getBoundingClientRect();
      if (r.top > vh || r.bottom < 0) return null;
      var p = clamp((vh / 2 - r.top) / r.height, 0, 1);
      return function () {
        if (!cw) sizeCanvas();
        draw(Math.round(p * (N - 1)));
        var idx = clamp(Math.floor(p * 4), 0, 3);
        if (idx !== last) {
          last = idx;
          rungs.forEach(function (rg, i) { rg.classList.toggle("on", i === idx); });
          setCard(idx);
        }
      };
    });
  })();

  // ===================================================== mimari diyagram
  var archWrap = $("[data-arch]");
  if (archWrap) (function () {
    var svgs = $$(".arch-svg", archWrap), cur = null, paths = {}, nodes = {}, lens = {};
    function pick() {
      cur = svgs.filter(function (s) { return getComputedStyle(s).display !== "none"; })[0] || svgs[0];
      paths = {}; nodes = {}; lens = {};
      $$(".ap", cur).forEach(function (p) { paths[p.dataset.ap] = p; lens[p.dataset.ap] = p.getTotalLength(); });
      $$(".an", cur).forEach(function (n) { nodes[n.dataset.an] = n; });
    }
    pick();
    addEventListener("resize", function () { var old = cur; pick(); if (old !== cur) drawn = -1; schedule(); });
    if (reduced) {
      svgs.forEach(function (s) { $$(".an", s).forEach(function (n) { n.classList.add("lit"); }); });
      return;
    }
    var drawn = -1, live = false;
    tasks.push(function (vh) {
      var r = cur.getBoundingClientRect();
      if (r.top > vh || r.bottom < 0) return null;
      var p = clamp((vh - r.top) / (vh * 0.45 + r.height * 0.55), 0, 1);
      if (p === drawn) return null;
      return function () {
        drawn = p;
        var st = [0, 1, 2, 3].map(function (s) { return ss(s * 0.2, s * 0.2 + 0.32, p); });
        Object.keys(paths).forEach(function (k) { paths[k].style.strokeDashoffset = (1 - st[+paths[k].dataset.stage]).toFixed(4); });
        Object.keys(nodes).forEach(function (k) {
          var need = k === "A" ? p > 0.01 : k.indexOf("ad") === 0 ? st[0] > 0.9 : k === "C" ? st[1] > 0.9 : k.indexOf("ch") === 0 ? st[2] > 0.9 : st[3] > 0.9;
          nodes[k].classList.toggle("lit", need);
        });
        live = st[3] >= 1;
        if (live) startPackets();
      };
    });

    // veri paketleri: ajan → adaptör → çekirdek → kanal → masaüstü
    var inView = false, running = false, trips = [], nextLaunch = 0, tripN = 0;
    watch(archWrap, function (v) { inView = v; if (v && live) startPackets(); }, "40px");
    var NS = "http://www.w3.org/2000/svg";
    function hit(id) {
      var n = nodes[id]; if (!n) return;
      n.classList.add("hit"); clearTimeout(n._t);
      n._t = setTimeout(function () { n.classList.remove("hit"); }, 260);
    }
    function startPackets() { if (!running && inView) { running = true; nextLaunch = 0; requestAnimationFrame(tick); } }
    function tick(now) {
      if (!inView || D.hidden) { running = false; return; }
      if (now >= nextLaunch && trips.length < 4) {
        var k = tripN % 4, j = (tripN * 5 + 1) % 6; tripN++;
        var g = $(".pk-g", cur), halo = D.createElementNS(NS, "circle"), dot = D.createElementNS(NS, "circle");
        halo.setAttribute("r", 9); halo.setAttribute("class", "pk-h");
        dot.setAttribute("r", 4.5); dot.setAttribute("class", "pk");
        g.appendChild(halo); g.appendChild(dot);
        trips.push({ segs: ["a" + k, "b" + k, "c" + j, "d" + j], dest: ["ad" + k, "C", "ch" + j, "D"], i: 0, t0: now, els: [halo, dot] });
        hit("A");
        nextLaunch = now + 820;
      }
      trips = trips.filter(function (tr) {
        var dur = 620, f = (now - tr.t0) / dur;
        while (f >= 1 && tr.i < 4) { hit(tr.dest[tr.i]); tr.i++; tr.t0 += dur; f = (now - tr.t0) / dur; }
        if (tr.i >= 4) { tr.els.forEach(function (e) { e.remove(); }); return false; }
        var id = tr.segs[tr.i], path = paths[id];
        if (!path) { tr.els.forEach(function (e) { e.remove(); }); return false; }
        var e = f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2;
        var pt = path.getPointAtLength(lens[id] * e);
        var tf = "translate(" + pt.x.toFixed(1) + "px," + pt.y.toFixed(1) + "px)";
        tr.els[0].style.transform = tf; tr.els[1].style.transform = tf;
        return true;
      });
      requestAnimationFrame(tick);
    }
  })();

  // ================================================== sayaçlar (odometre)
  $$(".stat dd[data-count]").forEach(function (dd) {
    if (reduced) return;
    var text = dd.textContent.trim();
    var wrap = D.createElement("span"); wrap.className = "odo"; wrap.setAttribute("aria-hidden", "true");
    var strips = [];
    Array.prototype.forEach.call(text, function (ch) {
      if (/\d/.test(ch)) {
        var d = D.createElement("span"); d.className = "odo-d";
        var s = D.createElement("span"); s.className = "odo-s";
        for (var i = 0; i < 20; i++) { var n = D.createElement("span"); n.textContent = i % 10; s.appendChild(n); }
        d.appendChild(s); wrap.appendChild(d); strips.push([s, +ch]);
      } else {
        var sep = D.createElement("span"); sep.className = "odo-sep"; sep.textContent = ch; wrap.appendChild(sep);
      }
    });
    var sr = D.createElement("span"); sr.className = "sr"; sr.textContent = text;
    dd.textContent = ""; dd.appendChild(sr); dd.appendChild(wrap);
    onReveal(dd.closest("[data-reveal]"), function () {
      requestAnimationFrame(function () { requestAnimationFrame(function () {
        strips.forEach(function (p, i) {
          p[0].style.transition = "transform " + (1.3 + i * 0.18).toFixed(2) + "s cubic-bezier(.2,.7,.2,1)";
          p[0].style.transform = "translate3d(0," + -(10 + p[1]) + "em,0)";
        });
      }); });
    });
  });

  // ============================================== yazma efektleri (görününce)
  var typeon = $("[data-typeon]");
  if (typeon && !reduced) (function () {
    var src = typeon.innerHTML, lines = src.split("\n");
    var PS = '<span class="c">$</span>';
    typeon.innerHTML = "";
    onReveal(typeon.closest("[data-reveal]"), async function () {
      var caret = D.createElement("span"); caret.className = "typing-caret";
      for (var i = 0; i < lines.length; i++) {
        var ln = lines[i];
        if (ln.indexOf(PS) === 0) {
          typeon.insertAdjacentHTML("beforeend", PS);
          var span = D.createElement("span"); typeon.appendChild(span); typeon.appendChild(caret);
          var tmp = D.createElement("div"); tmp.innerHTML = ln.slice(PS.length);
          var txt = tmp.textContent;
          for (var c = 1; c <= txt.length; c++) { span.textContent = txt.slice(0, c); await sleep(20); }
          await sleep(260);
        } else {
          typeon.insertAdjacentHTML("beforeend", ln);
          typeon.appendChild(caret);
          await sleep(70);
        }
        if (i < lines.length - 1) typeon.insertBefore(D.createTextNode("\n"), caret);
      }
      caret.remove();
      typeon.innerHTML = src;
    });
  })();
  $$("[data-typeline]").forEach(function (el) {
    var full = el.textContent;
    el.dataset.full = full;
    if (reduced) return;
    el.textContent = "";
    onReveal(el.closest("[data-reveal]"), async function () {
      await sleep(300);
      for (var i = 1; i <= full.length; i++) { el.textContent = full.slice(0, i); await sleep(38); }
    });
  });

  // ============================================== karşılaştırma: tarama çerçevesi
  var cmp = $("[data-cmp]");
  if (cmp) (function () {
    var scan = $("[data-scan]", cmp), table = $("table", cmp), th = $("thead th.us", cmp);
    var rects = $$("rect", scan);
    function place() {
      var x = table.offsetLeft + th.offsetLeft, y = table.offsetTop + th.offsetTop;
      var w = th.offsetWidth, h = table.offsetHeight - th.offsetTop;
      scan.style.left = x + "px"; scan.style.top = y + "px";
      scan.style.width = w + "px"; scan.style.height = h + "px";
      rects.forEach(function (r) { r.setAttribute("width", Math.max(0, w - 2)); r.setAttribute("height", Math.max(0, h - 2)); });
    }
    place();
    if (D.fonts && D.fonts.ready) D.fonts.ready.then(place);
    addEventListener("resize", place);
    if (!reduced) watch(cmp, function (v) { scan.style.animationPlayState = v ? "running" : "paused"; $$(".cs-run", scan).forEach(function (r) { r.style.animationPlayState = v ? "running" : "paused"; }); });
  })();

  // ================================================ mikro etkileşimler
  if (fine && !reduced) {
    $$("[data-magnet]").forEach(function (el) {
      el.addEventListener("pointermove", function (e) {
        var r = el.getBoundingClientRect();
        var dx = (e.clientX - r.left - r.width / 2) / r.width, dy = (e.clientY - r.top - r.height / 2) / r.height;
        el.style.transform = "translate(" + (dx * 10).toFixed(1) + "px," + (dy * 8).toFixed(1) + "px)";
      });
      el.addEventListener("pointerleave", function () { el.style.transform = ""; });
    });
    $$("[data-tilt]").forEach(function (el) {
      el.addEventListener("pointermove", function (e) {
        if (!el.classList.contains("in")) return;
        var r = el.getBoundingClientRect();
        var dx = (e.clientX - r.left) / r.width - 0.5, dy = (e.clientY - r.top) / r.height - 0.5;
        el.style.transition = "transform .15s ease-out, border-color .3s";
        el.style.transform = "perspective(900px) rotateX(" + (-dy * 6).toFixed(2) + "deg) rotateY(" + (dx * 7).toFixed(2) + "deg) translateY(-3px)";
      });
      el.addEventListener("pointerleave", function () { el.style.transition = ""; el.style.transform = ""; });
    });

    // ---------------------------------------------- imleç eşlikçisi
    // Sistemin imleci hiç gizlenmez; yeşil artı yanında yürür, düğme ve bağlantılara kilitlenir.
    var cc = D.createElement("div");
    cc.className = "cc"; cc.setAttribute("aria-hidden", "true");
    cc.innerHTML = '<div class="cc-x"><svg viewBox="-13 -13 26 26"><circle class="a" r="6"/><path class="a" d="M0 -12v4M0 8v4M-12 0h4M8 0h4"/><circle class="d" r="1.5"/></svg></div>' +
      '<span class="cc-c tl"></span><span class="cc-c tr"></span><span class="cc-c bl"></span><span class="cc-c br"></span><span class="cc-l"></span>';
    D.body.appendChild(cc);
    var X = $(".cc-x", cc), L = $(".cc-l", cc), C = $$(".cc-c", cc);
    var parts = [X, C[0], C[1], C[2], C[3], L].map(function (el) { return { el: el, x: -100, y: -100, vx: 0, vy: 0, tx: -100, ty: -100 }; });
    var mx = -100, my = -100, lock = null, ccRun = false, shown = false;
    function label(el) {
      var role = el.getAttribute("role") === "tab" ? "page tab" : el.tagName === "A" ? "link" : "push button";
      var name = (el.getAttribute("aria-label") || el.textContent || "").replace(/\s+/g, " ").trim();
      if (name.length > 22) name = name.slice(0, 21) + "…";
      return "[" + role + "] " + name;
    }
    function targets() {
      if (lock) {
        var r = lock.getBoundingClientRect(), g = 5;
        parts[0].tx = r.left + r.width / 2; parts[0].ty = r.top + r.height / 2;
        parts[1].tx = r.left - g; parts[1].ty = r.top - g;
        parts[2].tx = r.right + g; parts[2].ty = r.top - g;
        parts[3].tx = r.left - g; parts[3].ty = r.bottom + g;
        parts[4].tx = r.right + g; parts[4].ty = r.bottom + g;
        parts[5].tx = r.left - g; parts[5].ty = r.top - g - 4;
      } else {
        var x = mx + 22, y = my + 24;
        parts[0].tx = x; parts[0].ty = y;
        parts[1].tx = x - 10; parts[1].ty = y - 10; parts[2].tx = x + 10; parts[2].ty = y - 10;
        parts[3].tx = x - 10; parts[3].ty = y + 10; parts[4].tx = x + 10; parts[4].ty = y + 10;
        parts[5].tx = x - 10; parts[5].ty = y - 14;
      }
    }
    function ccTick() {
      targets();
      var moving = false;
      parts.forEach(function (p, i) {
        var k = i === 0 ? 0.16 : 0.2, d = 0.68;
        p.vx = p.vx * d + (p.tx - p.x) * k; p.vy = p.vy * d + (p.ty - p.y) * k;
        p.x += p.vx; p.y += p.vy;
        if (Math.abs(p.vx) + Math.abs(p.vy) + Math.abs(p.tx - p.x) + Math.abs(p.ty - p.y) > 0.2) moving = true;
        p.el.style.transform = "translate3d(" + p.x.toFixed(1) + "px," + p.y.toFixed(1) + "px,0)";
      });
      if (moving) requestAnimationFrame(ccTick); else ccRun = false;
    }
    function kick() { if (!ccRun) { ccRun = true; requestAnimationFrame(ccTick); } }
    D.addEventListener("pointermove", function (e) {
      if (e.pointerType && e.pointerType !== "mouse") return;
      mx = e.clientX; my = e.clientY;
      if (!shown) { shown = true; parts.forEach(function (p) { p.x = mx + 22; p.y = my + 24; }); cc.classList.add("shown"); }
      var t = e.target.closest ? e.target.closest('a[href], button, [role="tab"]') : null;
      if (t !== lock) {
        lock = t;
        cc.classList.toggle("lock", !!t);
        if (t) L.textContent = label(t);
      }
      kick();
    }, { passive: true });
    D.documentElement.addEventListener("mouseleave", function () { cc.classList.remove("shown"); shown = false; });
    addEventListener("scroll", function () { if (lock) kick(); }, { passive: true });
  }

  // ============================================================= replay
  var stage = $("[data-replay]");
  if (stage) (function () {
    var i18n = JSON.parse($("#replay-i18n").textContent);
    var desk = $(".desk", stage), log = $("[data-log]", stage), caption = $("[data-caption]", stage);
    var toggle = $("[data-toggle]", stage), chButtons = $$("[data-ch]", stage), agent = $("[data-agent]", desk);
    var win = function (n) { return $('[data-win="' + n + '"]', desk); };

    // Çıktılar CLI'ın gerçek biçimindedir; ref'lerdeki "…" kırpmadır.
    var CH = [
      [
        { cmd: "computer-use-linux windows" },
        { fx: function () { tag("term"); tag("set"); tag("web"); } },
        { out: "* win:{c31f…}  org.kde.konsole  1100x780+0+0      api : claude — Konsole\n" +
               "  win:{8c1e…}  systemsettings   760x540+1180+60   Appearance — System Settings\n" +
               "  win:{a41f…}  firefox          880x560+1060+520  Player — Mozilla Firefox" },
        { cmd: "computer-use-linux terms" },
        { out: "konsole:7891:2       claude         ~/projects/api           api : claude" }
      ],
      [
        { fx: function () { untagAll(); lit("term", true); } },
        { cmd: "computer-use-linux term-read konsole:7891:2" },
        { fx: function () { $$(".hl-target", desk).forEach(function (p) { p.classList.add("read"); }); } },
        { out: "● Running test suite…\n  tests/test_api.py ........F.F\n✗ 2 failed · test_login, test_refresh\nShould I fix them? (y/n, or tell me)\n›" }
      ],
      [
        { fx: function () { lit("term", true); } },
        { cmd: function () { return 'computer-use-linux term-send konsole:7891:2 "' + i18n.termMsg + '" --enter --json'; } },
        { typeTerm: true },
        { out: '{\n  "ok": true,\n  "ref": "konsole:7891:2"\n}' },
        { fx: function () { $("[data-reply]", desk).classList.add("on"); } }
      ],
      [
        { fx: function () { lit("term", false); lit("set", true); tag("set"); } },
        { cmd: 'computer-use-linux find "Dark" --window win:{8c1e…}' },
        { fx: function () { win("set").classList.add("tagged-el"); $("[data-dark-row]", desk).classList.add("found"); } },
        { out: "atspi:4:0/2/7\t[checkbox] Dark  <toggle,click>" },
        { cmd: "computer-use-linux click atspi:4:0/2/7 --json" },
        { fx: function () { $("[data-switch]", desk).classList.add("on"); win("set").classList.add("dark"); } },
        { out: '{\n  "ok": true,\n  "ref": "atspi:4:0/2/7"\n}' }
      ],
      [
        { fx: function () { untagAll(); lit("set", false); lit("web", true); tag("web"); } },
        { cmd: "computer-use-linux screenshot --window win:{a41f…} --max-width 1568 --json" },
        { fx: function () { flash($("[data-shutter]", desk)); } },
        { out: '{\n  "path": "/run/user/1000/nexremote-shot.png",\n  "width": 880,\n  "height": 560,\n  …\n  "scale": 1.0,\n  "origin": [1060, 520]\n}' },
        { cmd: "computer-use-linux click 440 190 --from-shot --json" },
        { cursorTo: "[data-play]" },
        { fx: function () { $("[data-play]", desk).classList.add("on"); $("[data-progress]", desk).classList.add("run"); } },
        { out: '{\n  "ok": true,\n  "x": 1500,\n  "y": 710,\n  "button": "left"\n}' },
        { cursorHome: true }
      ]
    ];

    function tag(n) { win(n).classList.add("tagged"); }
    function untagAll() { $$(".win", desk).forEach(function (w) { w.classList.remove("tagged", "tagged-el"); }); }
    function lit(n, on) { win(n).classList.toggle("lit", on); }
    function flash(el) { el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); }

    function resetDesk() {
      $$(".win", desk).forEach(function (w) { w.classList.remove("lit", "tagged", "tagged-el", "dark"); });
      $$(".read, .found, .on, .run", desk).forEach(function (el) {
        if (el !== agent) el.classList.remove("read", "found", "on", "run");
      });
      $("[data-typed]", desk).textContent = "";
      agent.classList.remove("on", "click");
      placeAgent(0.5, 0.92, true);
      log.textContent = "";
    }
    function placeAgent(fx, fy, instant) {
      var r = desk.getBoundingClientRect();
      agent.style.transition = instant ? "none" : "transform .7s cubic-bezier(.45,.05,.25,1), opacity .2s";
      agent.style.transform = "translate(" + (fx * r.width) + "px," + (fy * r.height) + "px)";
    }
    function agentTo(sel, instant) {
      var r = desk.getBoundingClientRect(), t = $(sel, desk).getBoundingClientRect();
      placeAgent((t.left + t.width / 2 - r.left) / r.width, (t.top + t.height / 2 - r.top) / r.height, instant);
    }

    // her çalıştırmanın kimliği var; yenisi başlayınca eskisi durur
    var run = 0, playing = false, current = 0, userPaused = false, ended = false;
    function wait(ms, id) {
      return new Promise(function (res, rej) { setTimeout(function () { id === run ? res() : rej("cancel"); }, ms); });
    }
    function line(cls, text) {
      var el = D.createElement("div");
      el.className = cls; el.textContent = text;
      log.appendChild(el); log.scrollTop = log.scrollHeight;
      return el;
    }
    async function typeInto(el, text, id, speed) {
      if (!speed) { el.textContent = text; return; }
      for (var i = 1; i <= text.length; i++) {
        el.textContent = text.slice(0, i);
        log.scrollTop = log.scrollHeight;
        await wait(speed, id);
      }
    }
    async function playChapter(n, id, animate) {
      var ops = CH[n];
      for (var k = 0; k < ops.length; k++) {
        var op = ops[k];
        if (op.cmd) {
          var text = typeof op.cmd === "function" ? op.cmd() : op.cmd;
          await typeInto(line("cmd", ""), text, id, animate ? 22 : 0);
          if (animate) await wait(380, id);
        } else if (op.out) {
          line("out", op.out);
          if (animate) await wait(900, id);
        } else if (op.fx) {
          op.fx();
          if (animate) await wait(450, id);
        } else if (op.typeTerm) {
          await typeInto($("[data-typed]", desk), i18n.termMsg, id, animate ? 30 : 0);
          if (animate) await wait(300, id);
        } else if (op.cursorTo) {
          agent.classList.add("on");
          agentTo(op.cursorTo, !animate);
          if (animate) await wait(800, id);
          agent.classList.remove("click"); void agent.offsetWidth; agent.classList.add("click");
          if (animate) await wait(350, id);
        } else if (op.cursorHome) {
          if (animate) { await wait(500, id); placeAgent(0.5, 0.92); await wait(700, id); }
          agent.classList.remove("on");
        }
      }
    }
    function select(n) {
      current = n;
      chButtons.forEach(function (b, i) { b.setAttribute("aria-selected", i === n ? "true" : "false"); });
      caption.textContent = i18n.captions[n];
    }
    // Bölüm n'e git: öncekiler anında uygulanır, n oynatılır (veya anında gösterilir).
    async function goTo(n, animate) {
      var id = ++run;
      resetDesk();
      select(n);
      try {
        for (var i = 0; i < n; i++) await playChapter(i, id, false);
        await playChapter(n, id, animate);
        if (!animate) return;
        for (var j = n + 1; j < CH.length && playing; j++) {
          await wait(1400, id);
          select(j);
          await playChapter(j, id, true);
        }
        await wait(400, id);
        ended = true;
        setPlaying(false, true);
      } catch (e) { if (e !== "cancel") throw e; }
    }
    function setPlaying(on, end) {
      playing = on;
      toggle.textContent = on ? toggle.dataset.pauseLabel : end ? toggle.dataset.againLabel : toggle.dataset.playLabel;
    }
    toggle.addEventListener("click", function () {
      if (playing) { run++; userPaused = true; setPlaying(false); return; }
      var restart = ended;
      ended = false; userPaused = false;
      setPlaying(true);
      goTo(restart ? 0 : current, true);
    });
    chButtons.forEach(function (b, i) {
      b.addEventListener("click", function () {
        ended = false;
        if (reduced) { run++; setPlaying(false); goTo(i, false); return; }
        userPaused = false;
        setPlaying(true);
        goTo(i, true);
      });
    });
    addEventListener("resize", function () { if (!playing) agent.classList.remove("on"); });

    // İlk durum: 1. bölüm hazır. Hareket isteyenlerde görününce oynar, ekrandan çıkınca durur.
    goTo(0, false);
    if (!reduced && hasIO) {
      new IntersectionObserver(function (entries) {
        var v = entries[entries.length - 1].isIntersecting;
        if (v && !playing && !userPaused && !ended) { setPlaying(true); goTo(current, true); }
        else if (!v && playing) { run++; setPlaying(false); }
      }, { threshold: 0.35 }).observe(stage);
    }
  })();

  schedule();
})();
