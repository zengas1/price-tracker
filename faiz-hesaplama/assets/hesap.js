// Faiz getiri hesapları — arayüzden bağımsız saf fonksiyonlar.
// Tarayıcıda window.Hesap olarak, Node'da require() ile kullanılır.
(function (kok, kur) {
  if (typeof module === "object" && module.exports) module.exports = kur();
  else kok.Hesap = kur();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const YIL_GUN = 365; // TL mevduatta bankalar faizi 365 gün üzerinden işletir

  // Vadeye göre mevduat stopaj oranı (%). `dilimler` gün üst sınırına göre
  // sıralıdır; üst sınırı null olan son dilim "1 yıldan uzun" vadelerdir.
  function mevduatStopaji(vadeGun, dilimler) {
    for (const d of dilimler) {
      if (d.gun_ust == null || vadeGun <= d.gun_ust) return d.oran;
    }
    return dilimler[dilimler.length - 1].oran;
  }

  // Vadeli mevduat. `yenileGun` verilirse para bu vadelerle yenilenir ve her
  // vade sonunda net faiz ana paraya eklenir (bileşik); verilmezse tek vade.
  function mevduat({ anapara, gun, yillikOran, stopajDilimleri, yenileGun }) {
    const donemler = [];
    if (yenileGun && gun > yenileGun) {
      for (let i = 0; i < Math.floor(gun / yenileGun); i++) donemler.push(yenileGun);
      if (gun % yenileGun) donemler.push(gun % yenileGun);
    } else {
      donemler.push(gun);
    }

    let bakiye = anapara, brut = 0, stopaj = 0;
    for (const g of donemler) {
      const faiz = bakiye * (yillikOran / 100) * (g / YIL_GUN);
      const kesinti = faiz * mevduatStopaji(g, stopajDilimleri) / 100;
      brut += faiz;
      stopaj += kesinti;
      bakiye += faiz - kesinti;
    }
    return sonuc(anapara, gun, brut, stopaj, {
      stopajOrani: mevduatStopaji(donemler[0], stopajDilimleri),
      donemSayisi: donemler.length,
    });
  }

  // Para piyasası fonu. Fonun son `getiri.gun` günde sağladığı `getiri.oran`
  // (ör. 0.03 = %3) aynı hızla sürerse `gun` günde fiyat ne kadar artar?
  // Fon getirisi günlük bileşiktir; stopaj satışta kazanç üzerinden kesilir.
  function fon({ anapara, gun, getiri, stopajOrani }) {
    const buyume = Math.pow(1 + getiri.oran, gun / getiri.gun) - 1;
    const brut = anapara * buyume;
    const stopaj = brut > 0 ? brut * stopajOrani / 100 : 0;
    return sonuc(anapara, gun, brut, stopaj, { stopajOrani, donemSayisi: 1 });
  }

  // Fonun dönem getirisini mevduat oranıyla karşılaştırılabilir yıllık
  // basit orana (%) çevirir.
  function yillikBasit(getiri) {
    return getiri.oran * YIL_GUN / getiri.gun * 100;
  }

  function sonuc(anapara, gun, brut, stopaj, ek) {
    const net = brut - stopaj;
    return Object.assign({
      anapara, gun, brut, stopaj, net,
      toplam: anapara + net,
      gunluk: net / gun,
      aylik: net / gun * 30,
      // Elde edilen net kazancın yıllık basit karşılığı (%)
      netYillik: anapara > 0 ? net / anapara * YIL_GUN / gun * 100 : 0,
    }, ek);
  }

  return { YIL_GUN, mevduatStopaji, mevduat, fon, yillikBasit };
});
