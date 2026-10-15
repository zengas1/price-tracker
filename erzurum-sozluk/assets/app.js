// Erzurum Yaşayan Sözlük — tüm sayfalar data/sozluk.json'dan beslenir.
(function () {
  "use strict";

  function el(tag, attrs, ...cocuklar) {
    const d = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") d.className = v;
      else if (k.startsWith("on")) d.addEventListener(k.slice(2), v);
      else d.setAttribute(k, v);
    }
    for (const c of cocuklar) if (c != null) d.append(c);
    return d;
  }

  // Aksanları ve şive farklarını (ğış/kış, çoh/çok) yok sayarak arama
  function sadelestir(s) {
    return s.toLocaleLowerCase("tr").normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/ı/g, "i").replace(/[kh]/g, "g");
  }

  async function veriYukle() {
    const r = await fetch("data/sozluk.json", { cache: "no-cache" });
    if (!r.ok) throw new Error("Sözlük verisi yüklenemedi (" + r.status + ")");
    return r.json();
  }

  function liste(veri) {
    const ul = document.getElementById("liste");
    const ara = document.getElementById("ara");
    const sayac = document.getElementById("sayac");
    let tur = "hepsi";

    function ciz() {
      const q = sadelestir(ara.value.trim());
      const sonuc = veri.maddeler.filter((m) =>
        (tur === "hepsi" || m.tur === tur) &&
        (!q || sadelestir([m.soz_sive, m.soz_standart, m.anlam].join(" ")).includes(q)));
      ul.replaceChildren(...sonuc.map((m) => el("li", null,
        el("a", { href: "madde.html?id=" + m.id },
          el("span", { class: "no" }, m.id),
          el("span", { class: "soz" }, m.soz_sive),
          el("span", { class: "anlam" }, m.anlam)))));
      sayac.textContent = sonuc.length + " madde";
      if (!sonuc.length) ul.append(el("li", { class: "bos" }, "Aradığın söz bulunamadı."));
    }

    ara.addEventListener("input", ciz);
    document.querySelectorAll(".filtre button").forEach((b) => b.addEventListener("click", () => {
      tur = b.dataset.tur;
      document.querySelectorAll(".filtre button").forEach((x) => x.setAttribute("aria-pressed", x === b));
      ciz();
    }));
    ciz();
  }

  function sesKutusu(m, cinsiyet, etiket, ikon) {
    const yer = el("div");
    const audio = el("audio", { controls: "", preload: "metadata", src: "ses/" + m.id + "-" + cinsiyet + ".mp3" });
    audio.addEventListener("error", () => {
      yer.replaceChildren(el("p", { class: "bekliyor" }, "Ses kaydı henüz eklenmedi."));
    });
    // Biri çalınca diğerini durdur
    audio.addEventListener("play", () => {
      document.querySelectorAll("audio").forEach((a) => { if (a !== audio) a.pause(); });
    });
    yer.append(audio);
    return el("section", { class: "ses " + cinsiyet },
      el("div", { class: "ses-baslik" }, el("span", { class: "ses-ikon", "aria-hidden": "true" }, ikon), etiket),
      yer,
      el("details", null, el("summary", null, "Söylenenin metni"), el("p", null, m["metin_" + cinsiyet])));
  }

  function madde(veri) {
    const id = new URLSearchParams(location.search).get("id");
    const i = veri.maddeler.findIndex((m) => m.id === id);
    const hedef = document.getElementById("madde");
    if (i < 0) {
      hedef.replaceChildren(el("p", null, "Bu madde bulunamadı. ", el("a", { href: "index.html" }, "Tüm sözlere dön")));
      return;
    }
    const m = veri.maddeler[i];
    document.title = m.soz_sive + " · Erzurum Yaşayan Sözlük";
    const onceki = veri.maddeler[i - 1];
    const sonraki = veri.maddeler[i + 1];

    hedef.replaceChildren(
      el("article", { class: "kart" },
        el("span", { class: "etiket" }, m.id + " · " + m.tur),
        el("h1", null, m.soz_sive),
        el("p", { class: "standart" }, "Standart Türkçe: " + m.soz_standart),
        el("div", { class: "sesler" },
          sesKutusu(m, "kadin", "Kadın sesiyle dinle", "♀"),
          sesKutusu(m, "erkek", "Erkek sesiyle dinle", "♂")),
        el("h2", null, "Anlamı"),
        el("p", null, m.anlam),
        el("h2", null, "Örnek"),
        el("p", { class: "ornek" }, "“" + m.ornek + "”")),
      el("nav", { class: "gezinti" },
        onceki ? el("a", { class: "dugme", href: "madde.html?id=" + onceki.id }, "← Önceki") : el("span"),
        sonraki ? el("a", { class: "dugme", href: "madde.html?id=" + sonraki.id }, "Sonraki →") : el("span")));
  }

  function kitapcik(veri) {
    const kap = document.getElementById("kartlar");
    kap.append(el("div", { class: "qr-kart kapak" },
      el("div", null,
        el("div", { class: "no" }, "Yaşayan Sözlük"),
        el("div", { class: "soz" }, veri.baslik),
        el("p", { class: "anlam" }, veri.aciklama + " Kodu okut, tüm sözleri gör.")),
      el("img", { src: "qr/sozluk.svg", alt: "Sözlüğün ana sayfasına giden QR kodu" })));
    for (const m of veri.maddeler) {
      kap.append(el("div", { class: "qr-kart" },
        el("div", null,
          el("div", { class: "no" }, m.id + " · " + m.tur.toLocaleUpperCase("tr")),
          el("div", { class: "soz" }, m.soz_sive),
          el("p", { class: "anlam" }, m.anlam)),
        el("img", { src: "qr/" + m.id + ".svg", alt: m.soz_sive + " için QR kodu" })));
    }
  }

  const sayfalar = { liste, madde, kitapcik };
  veriYukle()
    .then((veri) => sayfalar[document.body.dataset.sayfa](veri))
    .catch((h) => {
      document.querySelector("main").prepend(el("p", { class: "bos" }, h.message));
    });
})();
