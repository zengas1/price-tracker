// Faiz Getiri Hesaplama — oranlar data/oranlar.json'dan, hesaplar hesap.js'ten.
(function () {
  "use strict";

  const H = window.Hesap;
  const YENILE_GUN = 32;
  const PENCERE_SIRASI = ["30", "91", "7"]; // seçili dönem yoksa denenecekler
  const PENCERE_ADI = { "7": "son 7 gün", "30": "son 30 gün", "91": "son 3 ay" };
  const PENCERE_ICINDE = { "7": "son 7 gündeki", "30": "son 30 gündeki", "91": "son 3 aydaki" };
  const ESKI_VERI_GUN = 4;
  const ANAHTAR = "faiz-hesaplama:v1";

  const $ = (id) => document.getElementById(id);

  function el(tag, attrs, ...cocuklar) {
    const d = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") d.className = v;
      else if (k.startsWith("on")) d.addEventListener(k.slice(2), v);
      else d.setAttribute(k, v === true ? "" : v);
    }
    for (const c of cocuklar) if (c != null && c !== false) d.append(c);
    return d;
  }

  // ---------------------------------------------------------------- Biçim

  const ikiHane = new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const tamSayi = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 0 });
  const oranBicim = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 });
  const fiyatBicim = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 6 });
  const tarihBicim = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long", year: "numeric" });

  const para = (n) => ikiHane.format(n) + " TL";
  const isaretli = (n) => (n >= 0 ? "+" : "−") + para(Math.abs(n));
  const yuzde = (n) => "%" + oranBicim.format(n);
  const tarih = (iso) => (iso ? tarihBicim.format(new Date(iso.length === 10 ? iso + "T12:00:00" : iso)) : "—");

  // "100.000" / "100000" / "1.250,50" → sayı
  function sayiOku(metin) {
    const s = String(metin).replace(/\s|TL|%/gi, "");
    const n = parseFloat(/,/.test(s) ? s.replace(/\./g, "").replace(",", ".") : s.replace(/\.(?=\d{3}(\D|$))/g, ""));
    return Number.isFinite(n) ? n : null;
  }

  // TEFAS fon adları büyük harfle gelir: "ATLAS PORTFÖY PARA PİYASASI FONU" → "Atlas Portföy Para Piyasası Fonu"
  function basHarf(s) {
    return s.toLocaleLowerCase("tr").replace(/(^|[\s(\-/])(\p{L})/gu, (_, a, b) => a + b.toLocaleUpperCase("tr"))
      .replace(/\b(Tl|Usd|Eur)\b/g, (m) => m.toUpperCase());
  }

  const gunFarki = (iso) => (Date.now() - new Date(iso.length === 10 ? iso + "T12:00:00" : iso)) / 864e5;

  // ---------------------------------------------------------------- Durum

  const durum = {
    tutar: 100000, gun: 32, tur: "mevduat", banka: null, fon: null,
    ozelOran: 40, ozelStopaj: null, oranElle: null,
    yenile: true, bankaOrani: "max", pencere: "30", stopaj: null, filtre: "hepsi",
  };
  const KALICI = ["tutar", "gun", "tur", "banka", "fon", "ozelOran", "ozelStopaj",
    "yenile", "bankaOrani", "pencere", "stopaj", "filtre"];

  function kaydet() {
    try {
      localStorage.setItem(ANAHTAR, JSON.stringify(Object.fromEntries(KALICI.map((k) => [k, durum[k]]))));
    } catch (_) { /* gizli pencere vb. */ }
  }

  function geriYukle() {
    try {
      const k = JSON.parse(localStorage.getItem(ANAHTAR) || "null");
      if (k) for (const a of KALICI) if (a in k) durum[a] = k[a];
    } catch (_) { /* yok say */ }
  }

  let veri = null, bankalar = [], fonlar = [];

  // ---------------------------------------------------------------- Veri

  async function jsonGetir(adres) {
    const r = await fetch(adres, { cache: "no-cache" });
    if (!r.ok) throw new Error(adres + " (" + r.status + ")");
    return r.json();
  }

  // GitHub Pages'te depo dalındaki dosya da denenir: zamanlanmış iş akışının
  // yazdığı veri raw.githubusercontent.com'da Pages'in yeniden derlenmesini
  // beklemeden görünür. Hangisi daha yeniyse o kullanılır.
  function depoAdresi() {
    const kullanici = location.hostname.match(/^([^.]+)\.github\.io$/);
    const depo = location.pathname.split("/")[1];
    return kullanici && depo
      ? `https://raw.githubusercontent.com/${kullanici[1]}/${depo}/main/faiz-hesaplama/data/oranlar.json`
      : null;
  }

  async function veriYukle() {
    const adresler = ["data/oranlar.json", depoAdresi()].filter(Boolean);
    const sonuclar = await Promise.allSettled(adresler.map(jsonGetir));
    const gelen = sonuclar.filter((s) => s.status === "fulfilled").map((s) => s.value);
    if (!gelen.length) throw new Error("Oran verisi yüklenemedi.");
    return gelen.sort((a, b) => String(b.son_kontrol || "").localeCompare(String(a.son_kontrol || "")))[0];
  }

  function hazirla(v) {
    bankalar = ((v.mevduat && v.mevduat.liste) || []).map((u) => ({
      id: u.banka + "|" + u.urun, ad: u.banka, alt: u.urun,
      oranMin: u.oran_min, oranMax: u.oran_max, tutarMin: u.tutar_min, tutarMax: u.tutar_max,
    }));
    fonlar = ((v.fonlar && v.fonlar.liste) || []).map((f) => ({
      id: f.kod, kod: f.kod, ad: basHarf(f.ad), getiri: f.getiri, fiyat: f.fiyat, fiyatTarihi: f.fiyat_tarihi,
    }));
  }

  // ---------------------------------------------------------------- Hesap

  function stopajlar() {
    return durum.stopaj || veri.stopaj;
  }

  const bankaOrani = (b) => (durum.bankaOrani === "min" ? b.oranMin : b.oranMax);
  const tutarUygun = (b) => (b.tutarMin == null || durum.tutar >= b.tutarMin) &&
    (b.tutarMax == null || durum.tutar <= b.tutarMax);

  function fonGetirisi(f) {
    const anahtar = [durum.pencere, ...PENCERE_SIRASI].find((p) => f.getiri[p]);
    return anahtar ? Object.assign({ anahtar }, f.getiri[anahtar]) : null;
  }

  function mevduatHesabi(yillikOran, stopajDilimleri) {
    return H.mevduat({
      anapara: durum.tutar, gun: durum.gun, yillikOran,
      stopajDilimleri: stopajDilimleri || stopajlar().mevduat,
      yenileGun: durum.yenile ? YENILE_GUN : null,
    });
  }

  function fonHesabi(f) {
    const g = fonGetirisi(f);
    return g && H.fon({ anapara: durum.tutar, gun: durum.gun, getiri: g, stopajOrani: stopajlar().fon });
  }

  // Sıralama listesindeki her seçenek: { tur, id, ad, alt, oran, sonuc }
  function secenekler() {
    const liste = [];
    for (const b of bankalar) {
      if (!tutarUygun(b)) continue;
      const oran = bankaOrani(b);
      liste.push({ tur: "mevduat", id: b.id, ad: b.ad, alt: b.alt, oran, sonuc: mevduatHesabi(oran) });
    }
    for (const f of fonlar) {
      const g = fonGetirisi(f);
      if (!g) continue;
      liste.push({ tur: "fon", id: f.id, ad: f.kod, alt: f.ad, oran: H.yillikBasit(g), sonuc: fonHesabi(f) });
    }
    return liste.sort((a, b) => b.sonuc.net - a.sonuc.net);
  }

  // ---------------------------------------------------------------- Çizim

  function veriDurumu() {
    const p = $("veri-durum");
    const parcalar = [];
    const uyarilar = [];
    const pf = veri.politika_faizi;
    if (pf) parcalar.push(el("span", { class: "rozet" }, "TCMB politika faizi " + yuzde(pf.oran)));
    const bolum = (ad, b, ne) => {
      const hata = veri.durum && veri.durum[ad] && veri.durum[ad].hata;
      if (b && b.tarih) {
        parcalar.push(el("span", {}, `${ne}: ${tarih(b.tarih)}`));
        if (gunFarki(b.tarih) > ESKI_VERI_GUN) uyarilar.push(`${ne} ${Math.floor(gunFarki(b.tarih))} gündür güncellenemedi.`);
        else if (hata) uyarilar.push(`${ne} son denemede alınamadı; önceki veri gösteriliyor.`);
      } else {
        uyarilar.push(`${ne} henüz alınamadı${hata ? " (kaynak yanıt vermedi)" : ""}; güncelleyici çalışınca burada görünecek.`);
      }
    };
    bolum("mevduat", veri.mevduat, "Banka oranları");
    bolum("fonlar", veri.fonlar, "Fon fiyatları");
    const st = veri.stopaj;
    if (st && st.gecerlilik && gunFarki(st.gecerlilik) > 0.5) { // geçerlilik günü dahil
      uyarilar.push(`Stopaj oranlarının geçerlilik süresi (${tarih(st.gecerlilik)}) doldu; güncel oranları kontrol edip ayarlardan girin.`);
    }
    p.replaceChildren(...parcalar.flatMap((x, i) => (i ? [" · ", x] : [x])));
    p.after(...uyarilar.map((u) => el("p", { class: "uyari" }, u)));
  }

  function secimleriCiz() {
    const banka = $("banka");
    if (bankalar.length) {
      banka.replaceChildren(...[...bankalar].sort((a, b) => b.oranMax - a.oranMax).map((b) =>
        el("option", { value: b.id, selected: b.id === durum.banka },
          `${b.ad} — ${b.oranMin === b.oranMax ? yuzde(b.oranMax) : yuzde(b.oranMin) + "–" + yuzde(b.oranMax)}`)));
      if (!bankalar.some((b) => b.id === durum.banka)) durum.banka = banka.value;
      banka.disabled = false;
    } else {
      banka.replaceChildren(el("option", {}, "Banka oranları henüz yüklenmedi"));
      banka.disabled = true;
    }

    const fon = $("fon");
    if (fonlar.length) {
      const yillik = (f) => (fonGetirisi(f) ? H.yillikBasit(fonGetirisi(f)) : null);
      fon.replaceChildren(...[...fonlar].sort((a, b) => (yillik(b) || 0) - (yillik(a) || 0)).map((f) =>
        el("option", { value: f.id, selected: f.id === durum.fon },
          `${f.kod} — ${f.ad}${yillik(f) != null ? " (yıllık " + yuzde(yillik(f)) + ")" : ""}`)));
      if (!fonlar.some((f) => f.id === durum.fon)) durum.fon = fon.value;
      fon.disabled = false;
    } else {
      fon.replaceChildren(el("option", {}, "Fon verisi henüz yüklenmedi"));
      fon.disabled = true;
    }
  }

  function sekmeleriCiz() {
    document.querySelectorAll("[role=tab]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tur === durum.tur)));
    document.querySelectorAll("[data-panel]").forEach((p) => { p.hidden = p.dataset.panel !== durum.tur; });
    const b = bankalar.find((x) => x.id === durum.banka);
    $("oran-elle").placeholder = b ? oranBicim.format(bankaOrani(b)) : "";
  }

  const satir = (ad, deger, sinif) => el("div", { class: sinif }, el("dt", {}, ad), el("dd", {}, deger));

  const girdiGecerli = () => durum.tutar > 0 && durum.gun >= 1;

  function sonucCiz() {
    const k = $("sonuc");
    if (!girdiGecerli()) {
      k.replaceChildren(el("p", { class: "bos" }, "Tutar ve gün sayısını girin."));
      return;
    }
    let baslik, alt, s, oranSatirlari = [], notlar = [];

    if (durum.tur === "mevduat") {
      const b = bankalar.find((x) => x.id === durum.banka);
      if (!b) return k.replaceChildren(el("p", { class: "bos" }, "Banka oranları henüz yüklenmedi. Şimdilik “Kendi oranım” sekmesiyle hesaplayabilirsiniz."));
      const oran = durum.oranElle != null ? durum.oranElle : bankaOrani(b);
      s = mevduatHesabi(oran);
      baslik = b.ad; alt = b.alt;
      oranSatirlari.push(satir("Yıllık faiz (brüt)", yuzde(oran) +
        (durum.oranElle == null && b.oranMin !== b.oranMax ? ` (aralık ${yuzde(b.oranMin)}–${yuzde(b.oranMax)})` : "")));
      if (durum.oranElle != null) notlar.push("Sizin girdiğiniz oranla hesaplandı.");
      if (!tutarUygun(b)) {
        notlar.push(`Bu ürün ${[b.tutarMin != null && "en az " + tamSayi.format(b.tutarMin) + " TL",
          b.tutarMax != null && "en çok " + tamSayi.format(b.tutarMax) + " TL"].filter(Boolean).join(", ")} için geçerli.`);
      }
      mevduatNotu(s, notlar);
    } else if (durum.tur === "fon") {
      const f = fonlar.find((x) => x.id === durum.fon);
      if (!f) return k.replaceChildren(el("p", { class: "bos" }, "Fon verisi henüz yüklenmedi. Şimdilik “Kendi oranım” sekmesiyle hesaplayabilirsiniz."));
      const g = fonGetirisi(f);
      if (!g) return k.replaceChildren(el("p", { class: "bos" }, "Bu fonun yakın dönem getirisi hesaplanamadı."));
      s = fonHesabi(f);
      baslik = f.kod; alt = f.ad;
      oranSatirlari.push(
        satir(`Fiyat artışı (son ${g.gun} günde)`, yuzde(g.oran * 100)),
        satir("Yıllık karşılığı", yuzde(H.yillikBasit(g))));
      notlar.push(`Tahmin, fonun ${PENCERE_ICINDE[g.anahtar]} getiri hızının ${durum.gun} gün boyunca süreceğini varsayar. ` +
        `Son fiyat ${fiyatBicim.format(f.fiyat)} TL (${tarih(f.fiyatTarihi)}).`);
      if (g.anahtar !== durum.pencere) notlar.push(`Bu fon için ${PENCERE_ADI[durum.pencere]} verisi yok; ${PENCERE_ADI[g.anahtar]} kullanıldı.`);
      notlar.push("Fonlarda alım genelde ertesi iş gününün fiyatından gerçekleşir; kazanç günlük olarak fiyata yansır ve stopaj satışta kesilir.");
    } else {
      const oran = durum.ozelOran;
      if (!(oran >= 0)) return k.replaceChildren(el("p", { class: "bos" }, "Yıllık faiz oranını girin."));
      const dilim = durum.ozelStopaj != null ? [{ gun_ust: null, oran: durum.ozelStopaj }] : null;
      s = mevduatHesabi(oran, dilim);
      baslik = "Kendi oranım"; alt = yuzde(oran) + " yıllık faiz";
      oranSatirlari.push(satir("Yıllık faiz (brüt)", yuzde(oran)));
      mevduatNotu(s, notlar);
    }

    k.replaceChildren(
      el("p", { class: "etiket" }, { mevduat: "Banka mevduatı", fon: "Para piyasası fonu", ozel: "Kendi oranım" }[durum.tur]),
      el("h2", {}, baslik),
      alt && el("p", { class: "alt" }, alt),
      el("p", { class: "buyuk" }, el("strong", { class: s.net >= 0 ? "arti" : "eksi" }, isaretli(s.net)), " net kazanç"),
      el("p", { class: "toplam" }, `${tamSayi.format(durum.gun)} gün sonunda toplam `, el("strong", {}, para(s.toplam))),
      el("dl", { class: "dokum" },
        ...oranSatirlari,
        satir("Brüt kazanç", para(s.brut)),
        satir(`Stopaj (${yuzde(s.stopajOrani)})`, "−" + para(s.stopaj)),
        satir("Net kazanç", para(s.net), "vurgu"),
        satir("Günlük ortalama", para(s.gunluk)),
        satir("Aylık ortalama (30 gün)", para(s.aylik)),
        satir("Net yıllık getiri", yuzde(s.netYillik))),
      ...notlar.map((n) => el("p", { class: "not" }, n)));
  }

  function mevduatNotu(s, notlar) {
    if (s.donemSayisi > 1) {
      notlar.push(`${YENILE_GUN} günlük vadelerle ${s.donemSayisi} dönem yenilenir; her vade sonunda net faiz ana paraya eklenir. ` +
        "Oranın bu süre boyunca değişmeyeceği varsayılır.");
    }
  }

  function siralamaCiz() {
    const liste = girdiGecerli()
      ? secenekler().filter((x) => durum.filtre === "hepsi" || x.tur === durum.filtre)
      : [];
    const ol = $("siralama");
    const disarida = bankalar.filter((b) => !tutarUygun(b)).length;
    $("karsilastir-ozet").textContent = !girdiGecerli()
      ? "Tutar ve gün sayısını girin."
      : liste.length
        ? `${para(durum.tutar)}, ${tamSayi.format(durum.gun)} gün için net kazanca göre sıralı.` +
          (disarida ? ` Bu tutara uygun olmayan ${disarida} banka ürünü gösterilmiyor.` : "")
        : "Gösterilecek seçenek yok; oranlar yüklendiğinde burada listelenecek.";
    ol.replaceChildren(...liste.map((x, i) => {
      const secili = durum.tur === x.tur && (x.tur === "mevduat" ? durum.banka : durum.fon) === x.id;
      return el("li", {},
        el("button", {
          type: "button", class: secili ? "secili" : null, "aria-current": secili ? "true" : null,
          onclick: () => {
            durum.tur = x.tur;
            if (x.tur === "mevduat") { durum.banka = x.id; durum.oranElle = null; $("oran-elle").value = ""; }
            else durum.fon = x.id;
            hepsiniCiz();
            $("sonuc").scrollIntoView({ behavior: "smooth", block: "nearest" });
          },
        },
        el("span", { class: "sira" }, String(i + 1)),
        el("span", { class: "ad" }, el("strong", {}, x.ad), el("small", {}, x.alt)),
        el("span", { class: "rozet " + x.tur }, x.tur === "fon" ? "Fon" : "Mevduat"),
        el("span", { class: "oran" }, yuzde(x.oran)),
        el("span", { class: "net" }, isaretli(x.sonuc.net))));
    }));
    document.querySelectorAll("[data-filtre]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.filtre === durum.filtre)));
  }

  function ayarlariCiz() {
    $("yenile").checked = durum.yenile;
    document.querySelectorAll("[name=banka-orani]").forEach((r) => { r.checked = r.value === durum.bankaOrani; });
    document.querySelectorAll("[name=pencere]").forEach((r) => { r.checked = r.value === durum.pencere; });
    const st = stopajlar();
    st.mevduat.forEach((d, i) => { if ($("stopaj-" + i)) $("stopaj-" + i).value = oranBicim.format(d.oran); });
    $("stopaj-fon").value = oranBicim.format(st.fon);
    $("stopaj-not").textContent = durum.stopaj
      ? "Kendi girdiğiniz stopaj oranları kullanılıyor."
      : (veri.stopaj.not || "");
  }

  function kaynaklariCiz() {
    const p = $("kaynaklar");
    const parca = [];
    const bag = (b, metin) => b && b.url ? el("a", { href: b.url, rel: "noopener" }, metin) : metin;
    if (veri.mevduat) parca.push("Banka oranları: ", bag(veri.mevduat, veri.mevduat.kaynak));
    if (veri.fonlar) parca.push(parca.length ? " · " : "", "Fon fiyatları: ", bag(veri.fonlar, "TEFAS"));
    if (veri.politika_faizi) parca.push(parca.length ? " · " : "", "Politika faizi: ", bag(veri.politika_faizi, "TCMB"));
    if (veri.son_kontrol) parca.push(` · Son kontrol: ${tarih(veri.son_kontrol)}`);
    p.replaceChildren(...parca);
  }

  function hepsiniCiz() {
    sekmeleriCiz();
    sonucCiz();
    siralamaCiz();
    kaydet();
  }

  // ---------------------------------------------------------------- Olaylar

  function baglaGirisler() {
    const tutar = $("tutar"), gun = $("gun");
    tutar.value = tamSayi.format(durum.tutar);
    gun.value = durum.gun;
    $("ozel-oran").value = durum.ozelOran != null ? oranBicim.format(durum.ozelOran) : "";
    $("ozel-stopaj").value = durum.ozelStopaj != null ? oranBicim.format(durum.ozelStopaj) : "";

    tutar.addEventListener("input", () => { durum.tutar = sayiOku(tutar.value) || 0; hepsiniCiz(); });
    tutar.addEventListener("change", () => { if (durum.tutar) tutar.value = tamSayi.format(durum.tutar); });
    gun.addEventListener("input", () => { durum.gun = Math.min(3650, Math.round(sayiOku(gun.value) || 0)); hepsiniCiz(); });

    document.querySelectorAll(".hizli button").forEach((b) => b.addEventListener("click", () => {
      const hedef = b.parentElement.dataset.hedef, deger = Number(b.dataset.deger);
      durum[hedef] = deger;
      $(hedef).value = hedef === "tutar" ? tamSayi.format(deger) : deger;
      hepsiniCiz();
    }));

    document.querySelectorAll("[role=tab]").forEach((b) => b.addEventListener("click", () => { durum.tur = b.dataset.tur; hepsiniCiz(); }));
    $("banka").addEventListener("change", (e) => { durum.banka = e.target.value; durum.oranElle = null; $("oran-elle").value = ""; hepsiniCiz(); });
    $("fon").addEventListener("change", (e) => { durum.fon = e.target.value; hepsiniCiz(); });
    $("oran-elle").addEventListener("input", (e) => { durum.oranElle = e.target.value.trim() ? sayiOku(e.target.value) : null; hepsiniCiz(); });
    $("ozel-oran").addEventListener("input", (e) => { durum.ozelOran = sayiOku(e.target.value); hepsiniCiz(); });
    $("ozel-stopaj").addEventListener("input", (e) => { durum.ozelStopaj = e.target.value.trim() ? sayiOku(e.target.value) : null; hepsiniCiz(); });
    document.querySelectorAll("[data-filtre]").forEach((b) => b.addEventListener("click", () => { durum.filtre = b.dataset.filtre; hepsiniCiz(); }));

    $("yenile").addEventListener("change", (e) => { durum.yenile = e.target.checked; hepsiniCiz(); });
    document.querySelectorAll("[name=banka-orani]").forEach((r) => r.addEventListener("change", () => {
      durum.bankaOrani = r.value; secimleriCiz(); hepsiniCiz();
    }));
    document.querySelectorAll("[name=pencere]").forEach((r) => r.addEventListener("change", () => {
      durum.pencere = r.value; secimleriCiz(); hepsiniCiz();
    }));

    const stopajGirdileri = ["stopaj-0", "stopaj-1", "stopaj-2", "stopaj-fon"].map($);
    stopajGirdileri.forEach((g) => g.addEventListener("input", () => {
      const [a, b, c, fon] = stopajGirdileri.map((x) => sayiOku(x.value));
      if ([a, b, c, fon].some((x) => x == null)) return;
      durum.stopaj = {
        mevduat: veri.stopaj.mevduat.map((d, i) => Object.assign({}, d, { oran: [a, b, c][i] })),
        fon,
      };
      $("stopaj-not").textContent = "Kendi girdiğiniz stopaj oranları kullanılıyor.";
      hepsiniCiz();
    }));
    $("stopaj-sifirla").addEventListener("click", () => { durum.stopaj = null; ayarlariCiz(); hepsiniCiz(); });
  }

  // ---------------------------------------------------------------- Başlat

  async function baslat() {
    geriYukle();
    try {
      veri = await veriYukle();
    } catch (e) {
      $("veri-durum").textContent = e.message + " Sayfayı yenileyin.";
      $("veri-durum").classList.add("uyari");
      return;
    }
    hazirla(veri);
    veriDurumu();
    secimleriCiz();
    ayarlariCiz();
    kaynaklariCiz();
    baglaGirisler();
    hepsiniCiz();
  }

  baslat();
})();
