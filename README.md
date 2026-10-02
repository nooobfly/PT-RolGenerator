# PT-RolGenerator

Portakal Network'teki rol tagları ve ikonlarını üreten küçük bir Python scripti. Roller `roles.json`'da duruyor (isim, renk, ikon), script her rol için ikonu, yazı rozetini ve ikisinin yan yana halini pixel-art tarzında çiziyor. Ayrıca ItemsAdder'a girecek `config.yml` font listesini de kendisi yazıyor, elle uğraşmıyoruz.

- `output/`: ikon ve rozet png'leri (oyunda kullanılanlar)
- `FullOutput/`: ikon + rozet yan yana, sadece göz atmak için
- `config.yml`: ItemsAdder font_images listesi

Yeni rol eklemek için `roles.json`'a bir satır eklemek yetiyor. Pillow lazım.
