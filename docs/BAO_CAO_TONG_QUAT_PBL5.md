# BĂO CĂO Tá»”NG QUĂT PBL5

## Trang bĂ¬a gá»£i Ă½

TRÆ¯á»œNG Äáº I Há»ŒC BĂCH KHOA
KHOA CĂ”NG NGHá»† THĂ”NG TIN

**BĂO CĂO**
**PBL5 - Dá»° ĂN Ká»¸ THUáº¬T MĂY TĂNH**

**Há»† THá»NG QUáº¢N LĂ BĂƒI XE THĂ”NG MINH TĂCH Há»¢P RFID, NHáº¬N DIá»†N BIá»‚N Sá» VĂ€ Cáº¢NH BĂO QUĂ Táº¢I**

Giáº£ng viĂªn hÆ°á»›ng dáº«n: Cao VÄƒn C

| NhĂ³m sinh viĂªn thá»±c hiá»‡n | Lá»›p há»c pháº§n |
| --- | --- |
| [Há» tĂªn SV 1] | [Lá»›p] |
| [Há» tĂªn SV 2] | [Lá»›p] |
| [Há» tĂªn SV 3] | [Lá»›p] |
| [Há» tĂªn SV 4] | [Lá»›p] |

ÄĂ  Náºµng, 06/2025

---

## TĂ³m táº¯t Ä‘á»“ Ă¡n

Äá»“ Ă¡n xĂ¢y dá»±ng há»‡ thá»‘ng quáº£n lĂ½ bĂ£i xe thĂ´ng minh nháº±m giáº£m thao tĂ¡c thá»§ cĂ´ng khi xe ra vĂ o, háº¡n cháº¿ sai sĂ³t trong ghi nháº­n lÆ°á»£t gá»­i xe vĂ  há»— trá»£ giĂ¡m sĂ¡t tĂ¬nh tráº¡ng quĂ¡ táº£i cá»§a bĂ£i Ä‘á»—. Há»‡ thá»‘ng sá»­ dá»¥ng ESP32 káº¿t há»£p Ä‘áº§u Ä‘á»c RFID MFRC522 Ä‘á»ƒ nháº­n diá»‡n tháº», cáº£m biáº¿n siĂªu Ă¢m Ä‘á»ƒ há»— trá»£ phĂ¡t hiá»‡n váº­t cáº£n, servo Ä‘á»ƒ Ä‘iá»u khiá»ƒn barrier, LCD vĂ  buzzer Ä‘á»ƒ pháº£n há»“i tráº¡ng thĂ¡i táº¡i cá»•ng. Dá»¯ liá»‡u quáº¹t tháº» Ä‘Æ°á»£c gá»­i qua Wi-Fi Ä‘áº¿n backend FastAPI, lÆ°u trá»¯ trong MongoDB vĂ  hiá»ƒn thá»‹ trĂªn dashboard web. Pháº§n má»m quáº£n lĂ½ cĂ¡c Ä‘á»‘i tÆ°á»£ng khĂ¡ch hĂ ng, phÆ°Æ¡ng tiá»‡n, tháº» RFID, phiĂªn gá»­i xe, sÆ¡ Ä‘á»“ chá»— Ä‘á»—, gĂ³i cÆ°á»›c vĂ  doanh thu. Khi xe vĂ o, há»‡ thá»‘ng kiá»ƒm tra tháº», táº¡o phiĂªn gá»­i xe vĂ  gĂ¡n chá»— trá»‘ng; khi xe ra, há»‡ thá»‘ng Ä‘Ă³ng phiĂªn, tĂ­nh thá»i gian gá»­i vĂ  phĂ­ Ä‘á»— xe. Há»‡ thá»‘ng cÅ©ng thá»‘ng kĂª sá»‘ chá»— cĂ²n trá»‘ng, tá»· lá»‡ láº¥p Ä‘áº§y vĂ  tá»« chá»‘i xe vĂ o khi bĂ£i khĂ´ng cĂ²n chá»—. Module ESP32-CAM/AI nháº­n diá»‡n biá»ƒn sá»‘ Ä‘Æ°á»£c Ä‘á» xuáº¥t tĂ­ch há»£p Ä‘á»ƒ chá»¥p áº£nh, phĂ¡t hiá»‡n vĂ¹ng biá»ƒn sá»‘ vĂ  nháº­n dáº¡ng kĂ½ tá»± nháº±m Ä‘á»‘i chiáº¿u vá»›i thĂ´ng tin phÆ°Æ¡ng tiá»‡n.

LÆ°u Ă½ trung thá»±c khi viáº¿t bĂ¡o cĂ¡o: trong mĂ£ nguá»“n hiá»‡n táº¡i Ä‘Ă£ cĂ³ RFID, ESP32 firmware, backend FastAPI/MongoDB vĂ  dashboard web; chÆ°a tháº¥y module ESP32-CAM hoáº·c code nháº­n diá»‡n biá»ƒn sá»‘. Náº¿u chÆ°a triá»ƒn khai ká»‹p, nĂªn trĂ¬nh bĂ y pháº§n nháº­n diá»‡n biá»ƒn sá»‘ lĂ  "thiáº¿t káº¿ Ä‘á» xuáº¥t", "thá»­ nghiá»‡m riĂªng" hoáº·c "hÆ°á»›ng phĂ¡t triá»ƒn", khĂ´ng ghi lĂ  chá»©c nÄƒng hoĂ n thiá»‡n.

---

## Báº£ng phĂ¢n cĂ´ng nhiá»‡m vá»¥

| Sinh viĂªn thá»±c hiá»‡n | CĂ¡c nhiá»‡m vá»¥ | Tá»± Ä‘Ă¡nh giĂ¡ |
| --- | --- | --- |
| [SV 1] | Thiáº¿t káº¿ máº¡ch ESP32; káº¿t ná»‘i RFID MFRC522, LCD I2C, servo, buzzer, cáº£m biáº¿n siĂªu Ă¢m; cáº¥u hĂ¬nh firmware MicroPython; kiá»ƒm thá»­ quáº¹t tháº» vĂ  Ä‘iá»u khiá»ƒn barrier. | ÄĂ£ hoĂ n thĂ nh |
| [SV 2] | XĂ¢y dá»±ng backend FastAPI; thiáº¿t káº¿ API quáº¹t tháº», khĂ¡ch hĂ ng, xe, phiĂªn gá»­i xe, chá»— Ä‘á»—, gĂ³i cÆ°á»›c, doanh thu; káº¿t ná»‘i MongoDB. | ÄĂ£ hoĂ n thĂ nh |
| [SV 3] | XĂ¢y dá»±ng giao diá»‡n dashboard web; quáº£n lĂ½ khĂ¡ch hĂ ng, xe, Ä‘Äƒng kĂ½ tháº», lá»‹ch sá»­, map chá»— Ä‘á»—, biá»ƒu Ä‘á»“ doanh thu vĂ  tá»· lá»‡ láº¥p Ä‘áº§y. | ÄĂ£ hoĂ n thĂ nh |
| [SV 4] | Thiáº¿t káº¿/kháº£o sĂ¡t module ESP32-CAM vĂ  AI nháº­n diá»‡n biá»ƒn sá»‘; xĂ¢y dá»±ng ká»‹ch báº£n kiá»ƒm thá»­, bĂ¡o cĂ¡o káº¿t quáº£, tá»•ng há»£p tĂ i liá»‡u. | ChÆ°a hoĂ n thĂ nh hoáº·c KhĂ´ng triá»ƒn khai náº¿u chÆ°a tĂ­ch há»£p |

---

## Má»¥c lá»¥c gá»£i Ă½

1. Giá»›i thiá»‡u
1.1. Bá»‘i cáº£nh vĂ  hiá»‡n tráº¡ng
1.2. Váº¥n Ä‘á» cáº§n giáº£i quyáº¿t
1.3. Má»¥c tiĂªu vĂ  pháº¡m vi Ä‘á»“ Ă¡n
1.4. Giáº£i phĂ¡p tá»•ng quan

2. Giáº£i phĂ¡p
2.1. Giáº£i phĂ¡p pháº§n cá»©ng vĂ  truyá»n thĂ´ng
2.2. Giáº£i phĂ¡p AI/KHDL
2.3. Giáº£i phĂ¡p pháº§n má»m

3. Káº¿t quáº£
3.1. MĂ´i trÆ°á»ng thá»±c nghiá»‡m
3.2. Dá»¯ liá»‡u vĂ  ká»‹ch báº£n kiá»ƒm thá»­
3.3. Káº¿t quáº£ chá»©c nÄƒng
3.4. ÄĂ¡nh giĂ¡ há»‡ thá»‘ng

4. Káº¿t luáº­n
4.1. Káº¿t quáº£ Ä‘áº¡t Ä‘Æ°á»£c
4.2. Háº¡n cháº¿
4.3. HÆ°á»›ng phĂ¡t triá»ƒn

5. Danh má»¥c tĂ i liá»‡u tham kháº£o

---

# 1. Giá»›i thiá»‡u

## 1.1. Bá»‘i cáº£nh vĂ  hiá»‡n tráº¡ng

Táº¡i cĂ¡c bĂ£i xe trÆ°á»ng há»c, chung cÆ°, siĂªu thá»‹ hoáº·c cÆ¡ quan, quĂ¡ trĂ¬nh ghi vĂ© thá»§ cĂ´ng thÆ°á»ng máº¥t thá»i gian, dá»… nháº§m láº«n biá»ƒn sá»‘, khĂ³ truy váº¿t lá»‹ch sá»­ gá»­i xe vĂ  khĂ³ thá»‘ng kĂª sá»‘ chá»— cĂ²n láº¡i theo thá»i gian thá»±c. CĂ¡c há»‡ thá»‘ng hiá»‡n Ä‘áº¡i thÆ°á»ng káº¿t há»£p tháº» RFID, camera nháº­n diá»‡n biá»ƒn sá»‘, cáº£m biáº¿n cá»•ng, pháº§n má»m quáº£n lĂ½ vĂ  cÆ¡ sá»Ÿ dá»¯ liá»‡u táº­p trung. Tuy nhiĂªn, cĂ¡c giáº£i phĂ¡p thÆ°Æ¡ng máº¡i cĂ³ chi phĂ­ cao, khĂ³ tĂ¹y biáº¿n cho mĂ´ hĂ¬nh nhá» hoáº·c má»¥c tiĂªu há»c thuáº­t. VĂ¬ váº­y, Ä‘á» tĂ i táº­p trung xĂ¢y dá»±ng má»™t mĂ´ hĂ¬nh bĂ£i xe thĂ´ng minh quy mĂ´ nhá», cĂ³ kháº£ nÄƒng tá»± Ä‘á»™ng hĂ³a quy trĂ¬nh xe vĂ o/ra vĂ  cung cáº¥p dashboard quáº£n trá»‹.

## 1.2. Váº¥n Ä‘á» cáº§n giáº£i quyáº¿t

Há»‡ thá»‘ng cáº§n giáº£i quyáº¿t cĂ¡c váº¥n Ä‘á» chĂ­nh: nháº­n diá»‡n nhanh ngÆ°á»i dĂ¹ng hoáº·c phÆ°Æ¡ng tiá»‡n báº±ng tháº» RFID; tá»± Ä‘á»™ng ghi nháº­n thá»i gian xe vĂ o/ra; tĂ­nh phĂ­ theo thá»i gian hoáº·c theo gĂ³i cÆ°á»›c; quáº£n lĂ½ khĂ¡ch hĂ ng, xe vĂ  tháº»; giĂ¡m sĂ¡t sá»‘ lÆ°á»£ng chá»— trá»‘ng; cáº£nh bĂ¡o hoáº·c tá»« chá»‘i khi bĂ£i Ä‘áº§y; lÆ°u lá»‹ch sá»­ giao dá»‹ch Ä‘á»ƒ tra cá»©u. Vá»›i pháº§n má»Ÿ rá»™ng AI, há»‡ thá»‘ng cáº§n chá»¥p áº£nh biá»ƒn sá»‘, nháº­n diá»‡n kĂ½ tá»± vĂ  Ä‘á»‘i chiáº¿u vá»›i biá»ƒn sá»‘ Ä‘Ă£ Ä‘Äƒng kĂ½ Ä‘á»ƒ tÄƒng Ä‘á»™ an toĂ n.

## 1.3. Má»¥c tiĂªu vĂ  pháº¡m vi

Má»¥c tiĂªu cá»§a Ä‘á»“ Ă¡n lĂ  xĂ¢y dá»±ng há»‡ thá»‘ng IoT hoĂ n chá»‰nh gá»“m thiáº¿t bá»‹ cá»•ng dĂ¹ng ESP32, backend API, cÆ¡ sá»Ÿ dá»¯ liá»‡u vĂ  giao diá»‡n web quáº£n trá»‹. Pháº¡m vi triá»ƒn khai hiá»‡n táº¡i gá»“m quáº¹t tháº» RFID, check-in/check-out tá»± Ä‘á»™ng, Ä‘iá»u khiá»ƒn barrier, quáº£n lĂ½ chá»— Ä‘á»—, tĂ­nh phĂ­, thá»‘ng kĂª doanh thu vĂ  hiá»ƒn thá»‹ dashboard. Pháº§n ESP32-CAM/nháº­n diá»‡n biá»ƒn sá»‘ Ä‘Æ°á»£c Ä‘Æ°a vĂ o nhÆ° module má»Ÿ rá»™ng: náº¿u nhĂ³m Ä‘Ă£ thá»­ nghiá»‡m riĂªng, trĂ¬nh bĂ y káº¿t quáº£ thá»­ nghiá»‡m; náº¿u chÆ°a, trĂ¬nh bĂ y thiáº¿t káº¿ vĂ  hÆ°á»›ng tĂ­ch há»£p.

## 1.4. Giáº£i phĂ¡p tá»•ng quan

Há»‡ thá»‘ng Ä‘Æ°á»£c chia thĂ nh ba lá»›p. Lá»›p thiáº¿t bá»‹ táº¡i cá»•ng gá»“m ESP32, Ä‘áº§u Ä‘á»c RFID, servo, LCD, buzzer vĂ  cáº£m biáº¿n siĂªu Ă¢m. Lá»›p dá»‹ch vá»¥ gá»“m backend FastAPI nháº­n dá»¯ liá»‡u quáº¹t tháº», xá»­ lĂ½ nghiá»‡p vá»¥ vĂ  lÆ°u MongoDB. Lá»›p giao diá»‡n gá»“m dashboard web hiá»ƒn thá»‹ thá»‘ng kĂª, chá»— Ä‘á»—, khĂ¡ch hĂ ng, xe, gĂ³i cÆ°á»›c, lá»‹ch sá»­ vĂ  doanh thu.

```mermaid
flowchart LR
    RFID[RFID MFRC522] --> ESP32[ESP32 MicroPython]
    Ultrasonic[HC-SR04] --> ESP32
    ESP32 --> Servo[Servo barrier]
    ESP32 --> LCD[LCD I2C + buzzer]
    ESP32 -- HTTP/Wi-Fi --> API[FastAPI backend]
    Cam[ESP32-CAM - thiáº¿t káº¿ bá»• sung] -- áº£nh biá»ƒn sá»‘ --> AI[AI/OCR nháº­n diá»‡n biá»ƒn sá»‘]
    AI --> API
    API --> DB[(MongoDB)]
    Web[Web Dashboard] -- REST API --> API
```

# 2. Giáº£i phĂ¡p

## 2.1. Giáº£i phĂ¡p pháº§n cá»©ng vĂ  truyá»n thĂ´ng

### ThĂ nh pháº§n pháº§n cá»©ng

| Linh kiá»‡n | Vai trĂ² | Giao tiáº¿p/tham sá»‘ chĂ­nh | Ghi chĂº |
| --- | --- | --- | --- |
| ESP32 DevKit | Vi Ä‘iá»u khiá»ƒn trung tĂ¢m táº¡i cá»•ng | Wi-Fi, SPI, I2C, PWM, GPIO | Cháº¡y MicroPython, gá»­i HTTP request Ä‘áº¿n backend |
| MFRC522 | Äá»c tháº» RFID | SPI, 13.56 MHz | Äá»c UID tháº» Ä‘á»ƒ xĂ¡c Ä‘á»‹nh khĂ¡ch/xe |
| Tháº» RFID | Äá»‹nh danh ngÆ°á»i gá»­i xe | UID duy nháº¥t | LiĂªn káº¿t vá»›i khĂ¡ch hĂ ng vĂ  xe trong database |
| Servo SG90/MG996R | Äiá»u khiá»ƒn barrier | PWM 50 Hz | GĂ³c Ä‘Ă³ng/má»Ÿ cáº¥u hĂ¬nh trong firmware |
| LCD 16x2 I2C | Hiá»ƒn thá»‹ tráº¡ng thĂ¡i | I2C, Ä‘á»‹a chá»‰ thÆ°á»ng 0x27 | Hiá»ƒn thá»‹ READY, SCANNING, WELCOME, DENIED |
| Buzzer + LED | Pháº£n há»“i Ă¢m thanh/Ă¡nh sĂ¡ng | GPIO/PWM | BĂ¡o thĂ nh cĂ´ng hoáº·c lá»—i |
| HC-SR04 | PhĂ¡t hiá»‡n váº­t cáº£n/gáº§n cá»•ng | Trigger/Echo | Há»— trá»£ tá»± Ä‘á»™ng Ä‘Ă³ng cá»•ng an toĂ n |
| ESP32-CAM | Chá»¥p áº£nh biá»ƒn sá»‘ | Wi-Fi, camera OV2640 | ChÆ°a tĂ­ch há»£p trong repo hiá»‡n táº¡i |

### Káº¿t ná»‘i chĂ¢n theo firmware hiá»‡n táº¡i

| Module | ChĂ¢n ESP32 |
| --- | --- |
| RFID SCK/MOSI/MISO/CS/RST | GPIO 18/23/19/5/4 |
| Servo | GPIO 14 |
| LED | GPIO 2 |
| Buzzer | GPIO 13 |
| HC-SR04 Trigger/Echo | GPIO 26/35 |
| LCD SDA/SCL | GPIO 21/22 |

### NguyĂªn lĂ½ hoáº¡t Ä‘á»™ng pháº§n cá»©ng

ESP32 khá»Ÿi Ä‘á»™ng, Ä‘Ă³ng barrier, káº¿t ná»‘i Wi-Fi vĂ  hiá»ƒn thá»‹ tráº¡ng thĂ¡i sáºµn sĂ ng trĂªn LCD. Khi ngÆ°á»i dĂ¹ng Ä‘Æ°a tháº» RFID vĂ o vĂ¹ng Ä‘á»c, MFRC522 tráº£ vá» UID tháº». ESP32 kiá»ƒm tra thá»i gian chá»‘ng quĂ©t láº·p, Ä‘o khoáº£ng cĂ¡ch náº¿u cáº§n, sau Ä‘Ă³ gá»­i UID, mĂ£ cá»•ng vĂ  khoáº£ng cĂ¡ch lĂªn API `/api/v1/rfid/scan`. Backend tráº£ vá» káº¿t quáº£ cho phĂ©p hoáº·c tá»« chá»‘i. Náº¿u thĂ nh cĂ´ng, ESP32 má»Ÿ barrier, phĂ¡t Ă¢m bĂ¡o thĂ nh cĂ´ng vĂ  hiá»ƒn thá»‹ thĂ´ng tin. Sau thá»i gian cáº¥u hĂ¬nh, ESP32 kiá»ƒm tra cáº£m biáº¿n siĂªu Ă¢m rá»“i Ä‘Ă³ng barrier.

```mermaid
flowchart TD
    A[Báº¯t Ä‘áº§u] --> B[Káº¿t ná»‘i Wi-Fi]
    B --> C[Hiá»ƒn thá»‹ READY]
    C --> D[QuĂ©t RFID]
    D --> E{Äá»c Ä‘Æ°á»£c UID?}
    E -- KhĂ´ng --> D
    E -- CĂ³ --> F[Gá»­i HTTP POST /rfid/scan]
    F --> G{Backend cho phĂ©p?}
    G -- KhĂ´ng --> H[Buzzer lá»—i, LCD DENIED]
    G -- CĂ³ --> I[Má»Ÿ barrier, LCD WELCOME]
    I --> J[Äá»£i vĂ  kiá»ƒm tra váº­t cáº£n]
    J --> K[ÄĂ³ng barrier]
    H --> C
    K --> C
```

### Truyá»n thĂ´ng IoT

ESP32 vĂ  backend giao tiáº¿p qua Wi-Fi báº±ng HTTP/REST. Dá»¯ liá»‡u gá»­i tá»« ESP32 cĂ³ dáº¡ng JSON gá»“m `card_uid`, `gate_id`, `distance_cm` vĂ  `timestamp`. Backend pháº£n há»“i JSON gá»“m `success`, `action`, `message`, `customer_name`, `vehicle_plate`, `session_id`, `parking_fee` hoáº·c `slot_id`. Khi máº¥t káº¿t ná»‘i, firmware cĂ³ cÆ¡ cháº¿ kiá»ƒm tra láº¡i Wi-Fi vĂ  cĂ³ danh sĂ¡ch tháº» offline Ä‘Æ°á»£c phĂ©p.

### Báº£ng chi phĂ­ linh kiá»‡n

Äiá»n giĂ¡ Ä‘Ăºng theo hĂ³a Ä‘Æ¡n mua thá»±c táº¿ cá»§a nhĂ³m. Báº£ng dÆ°á»›i Ä‘Ă¢y lĂ  khung trĂ¬nh bĂ y.

| STT | Linh kiá»‡n | Sá»‘ lÆ°á»£ng | ÄÆ¡n giĂ¡ thá»±c táº¿ | ThĂ nh tiá»n |
| --- | --- | ---: | ---: | ---: |
| 1 | ESP32 DevKit | 1 | [Ä‘iá»n] | [Ä‘iá»n] |
| 2 | MFRC522 + tháº» RFID | 1 bá»™ | [Ä‘iá»n] | [Ä‘iá»n] |
| 3 | Servo SG90/MG996R | 1 | [Ä‘iá»n] | [Ä‘iá»n] |
| 4 | LCD 16x2 I2C | 1 | [Ä‘iá»n] | [Ä‘iá»n] |
| 5 | Cáº£m biáº¿n HC-SR04 | 1 | [Ä‘iá»n] | [Ä‘iá»n] |
| 6 | Buzzer, LED, Ä‘iá»‡n trá»Ÿ, dĂ¢y jumper | 1 bá»™ | [Ä‘iá»n] | [Ä‘iá»n] |
| 7 | Nguá»“n 5V/2A hoáº·c module nguá»“n | 1 | [Ä‘iá»n] | [Ä‘iá»n] |
| 8 | ESP32-CAM + USB TTL | 1 bá»™ | [Ä‘iá»n] | [Ä‘iá»n] |
| 9 | MĂ´ hĂ¬nh barrier/bĂ£i xe | 1 | [Ä‘iá»n] | [Ä‘iá»n] |
|  | **Tá»•ng cá»™ng** |  |  | **[Ä‘iá»n]** |

## 2.2. Giáº£i phĂ¡p AI/KHDL

### BĂ i toĂ¡n nháº­n diá»‡n biá»ƒn sá»‘

Module AI nháº±m tá»± Ä‘á»™ng Ä‘á»c biá»ƒn sá»‘ tá»« áº£nh chá»¥p táº¡i cá»•ng. Quy trĂ¬nh Ä‘á» xuáº¥t gá»“m: ESP32-CAM chá»¥p áº£nh khi cĂ³ xe hoáº·c sau khi quáº¹t tháº»; áº£nh Ä‘Æ°á»£c gá»­i vá» server; server phĂ¡t hiá»‡n vĂ¹ng biá»ƒn sá»‘; vĂ¹ng biá»ƒn sá»‘ Ä‘Æ°á»£c tiá»n xá»­ lĂ½; mĂ´ hĂ¬nh OCR nháº­n dáº¡ng kĂ½ tá»±; káº¿t quáº£ Ä‘Æ°á»£c chuáº©n hĂ³a vĂ  Ä‘á»‘i chiáº¿u vá»›i biá»ƒn sá»‘ lÆ°u trong báº£ng `vehicles`.

```mermaid
flowchart LR
    Image[áº¢nh tá»« ESP32-CAM] --> Detect[PhĂ¡t hiá»‡n vĂ¹ng biá»ƒn sá»‘]
    Detect --> Crop[Cáº¯t vĂ  cÄƒn chá»‰nh biá»ƒn sá»‘]
    Crop --> Preprocess[Tiá»n xá»­ lĂ½: grayscale, threshold, resize]
    Preprocess --> OCR[OCR kĂ½ tá»±]
    OCR --> Normalize[Chuáº©n hĂ³a Ä‘á»‹nh dáº¡ng biá»ƒn sá»‘]
    Normalize --> Compare[Äá»‘i chiáº¿u database]
    Compare --> Result[Cho phĂ©p, cáº£nh bĂ¡o hoáº·c yĂªu cáº§u kiá»ƒm tra]
```

### PhÆ°Æ¡ng Ă¡n thuáº­t toĂ¡n

PhÆ°Æ¡ng Ă¡n Ä‘Æ¡n giáº£n lĂ  dĂ¹ng OpenCV Ä‘á»ƒ chuyá»ƒn áº£nh sang xĂ¡m, lá»c nhiá»…u, phĂ¡t hiá»‡n cáº¡nh/contour vĂ  chá»n vĂ¹ng cĂ³ tá»· lá»‡ gáº§n giá»‘ng biá»ƒn sá»‘. PhÆ°Æ¡ng Ă¡n á»•n Ä‘á»‹nh hÆ¡n lĂ  huáº¥n luyá»‡n hoáº·c dĂ¹ng mĂ´ hĂ¬nh YOLO Ä‘á»ƒ phĂ¡t hiá»‡n biá»ƒn sá»‘, sau Ä‘Ă³ dĂ¹ng PaddleOCR/EasyOCR/Tesseract Ä‘á»ƒ nháº­n dáº¡ng kĂ½ tá»±. Vá»›i Ä‘á»“ Ă¡n PBL, nĂªn trĂ¬nh bĂ y YOLO/OCR lĂ  hÆ°á»›ng chĂ­nh náº¿u cĂ³ dá»¯ liá»‡u gĂ¡n nhĂ£n; náº¿u chÆ°a cĂ³ dá»¯ liá»‡u Ä‘á»§ lá»›n, trĂ¬nh bĂ y OpenCV + OCR nhÆ° thá»­ nghiá»‡m nguyĂªn máº«u.

### Dá»¯ liá»‡u Ä‘á» xuáº¥t

Táº­p dá»¯ liá»‡u cĂ³ thá»ƒ thu tháº­p báº±ng ESP32-CAM hoáº·c Ä‘iá»‡n thoáº¡i á»Ÿ cá»•ng mĂ´ hĂ¬nh, gá»“m áº£nh xe mĂ¡y/Ă´ tĂ´ trong nhiá»u Ä‘iá»u kiá»‡n Ă¡nh sĂ¡ng, gĂ³c chá»¥p vĂ  khoáº£ng cĂ¡ch khĂ¡c nhau. Náº¿u dĂ¹ng YOLO, cáº§n gĂ¡n nhĂ£n bounding box cho lá»›p `license_plate`; náº¿u Ä‘Ă¡nh giĂ¡ OCR, cáº§n nhĂ£n text biá»ƒn sá»‘ tÆ°Æ¡ng á»©ng. CĂ¡ch chia dá»¯ liá»‡u nĂªn lĂ  70% huáº¥n luyá»‡n, 15% xĂ¡c nháº­n, 15% kiá»ƒm thá»­. Cáº§n loáº¡i bá» áº£nh quĂ¡ má», quĂ¡ tá»‘i hoáº·c biá»ƒn sá»‘ bá»‹ che khuáº¥t Ä‘á»ƒ trĂ¡nh lĂ m sai lá»‡ch Ä‘Ă¡nh giĂ¡.

### Äá»™ Ä‘o Ä‘Ă¡nh giĂ¡ AI

| NhĂ³m Ä‘Ă¡nh giĂ¡ | Äá»™ Ä‘o | Ă nghÄ©a |
| --- | --- | --- |
| PhĂ¡t hiá»‡n biá»ƒn sá»‘ | Precision, Recall, mAP@0.5 | ÄĂ¡nh giĂ¡ mĂ´ hĂ¬nh tĂ¬m Ä‘Ăºng vĂ¹ng biá»ƒn sá»‘ |
| OCR | Character Accuracy | Tá»· lá»‡ kĂ½ tá»± Ä‘á»c Ä‘Ăºng |
| OCR | Plate Exact Match | Tá»· lá»‡ biá»ƒn sá»‘ Ä‘á»c Ä‘Ăºng toĂ n bá»™ |
| Hiá»‡u nÄƒng | Inference time, FPS | Tá»‘c Ä‘á»™ xá»­ lĂ½ áº£nh |
| Há»‡ thá»‘ng | Tá»· lá»‡ Ä‘á»‘i chiáº¿u Ä‘Ăºng RFID - biá»ƒn sá»‘ | ÄĂ¡nh giĂ¡ kháº£ nÄƒng chá»‘ng nháº§m xe |

## 2.3. Giáº£i phĂ¡p pháº§n má»m

### Kiáº¿n trĂºc backend

Backend dĂ¹ng FastAPI, tá»• chá»©c theo cĂ¡c controller: RFID, khĂ¡ch hĂ ng, xe, phiĂªn gá»­i xe, chá»— Ä‘á»—, gĂ³i cÆ°á»›c vĂ  thá»‘ng kĂª. Dá»¯ liá»‡u lÆ°u trong MongoDB vá»›i cĂ¡c collection chĂ­nh: `customers`, `vehicles`, `rfid_cards`, `sessions`, `parking_slots`, `packages`, `transactions`, `pending_scans`. CĂ¡c chá»‰ má»¥c Ä‘Æ°á»£c táº¡o cho mĂ£ khĂ¡ch hĂ ng, mĂ£ xe, UID tháº», mĂ£ phiĂªn, tráº¡ng thĂ¡i phiĂªn vĂ  thá»i gian vĂ o Ä‘á»ƒ tÄƒng tá»‘c truy váº¥n.

### Luá»“ng xá»­ lĂ½ RFID

Khi backend nháº­n UID tháº», há»‡ thá»‘ng kiá»ƒm tra tháº» cĂ³ tá»“n táº¡i khĂ´ng. Náº¿u tháº» Ä‘Ă£ Ä‘Äƒng kĂ½ vĂ  Ä‘ang hoáº¡t Ä‘á»™ng, backend tĂ¬m phiĂªn gá»­i xe Ä‘ang má»Ÿ. Náº¿u cĂ³ phiĂªn Ä‘ang má»Ÿ, há»‡ thá»‘ng xá»­ lĂ½ check-out, cáº­p nháº­t thá»i gian ra, tĂ­nh phĂ­, giáº£i phĂ³ng chá»— Ä‘á»— vĂ  táº¡o giao dá»‹ch. Náº¿u khĂ´ng cĂ³ phiĂªn, há»‡ thá»‘ng xá»­ lĂ½ check-in, tĂ¬m chá»— trá»‘ng, táº¡o phiĂªn má»›i vĂ  Ä‘Ă¡nh dáº¥u chá»— Ä‘Ă£ sá»­ dá»¥ng. Náº¿u tháº» chÆ°a tá»“n táº¡i, há»‡ thá»‘ng cĂ³ hai cháº¿ Ä‘á»™: tá»± Ä‘á»™ng Ä‘Äƒng kĂ½ khĂ¡ch vĂ£ng lai hoáº·c ghi nháº­n tháº» chá» Ä‘Äƒng kĂ½ trĂªn web.

```mermaid
flowchart TD
    A[Nháº­n card_uid] --> B{Tháº» Ä‘Ă£ tá»“n táº¡i?}
    B -- KhĂ´ng --> C{Registration mode?}
    C -- CĂ³ --> D[LÆ°u pending scan]
    C -- KhĂ´ng --> E[Táº¡o khĂ¡ch, xe, tháº», phiĂªn Ä‘áº§u tiĂªn]
    B -- CĂ³ --> F{Tháº» active?}
    F -- KhĂ´ng --> G[Tá»« chá»‘i]
    F -- CĂ³ --> H{CĂ³ session in_progress?}
    H -- CĂ³ --> I[Check-out, tĂ­nh phĂ­, giáº£i phĂ³ng slot]
    H -- KhĂ´ng --> J{CĂ²n slot trá»‘ng?}
    J -- KhĂ´ng --> K[Tá»« chá»‘i vĂ¬ bĂ£i Ä‘áº§y]
    J -- CĂ³ --> L[Check-in, táº¡o session, gĂ¡n slot]
```

### TĂ­nh phĂ­ vĂ  gĂ³i cÆ°á»›c

PhĂ­ Ä‘á»— xe theo lÆ°á»£t Ä‘Æ°á»£c tĂ­nh báº±ng thá»i gian tá»« `entry_time` Ä‘áº¿n `exit_time`, lĂ m trĂ²n lĂªn theo giá» vĂ  nhĂ¢n vá»›i Ä‘Æ¡n giĂ¡ cáº¥u hĂ¬nh `FEE_PER_HOUR = 5000` VND. Náº¿u khĂ¡ch hĂ ng cĂ³ gĂ³i ngĂ y hoáº·c gĂ³i thĂ¡ng cĂ²n hiá»‡u lá»±c, phĂ­ gá»­i lÆ°á»£t Ä‘Æ°á»£c tĂ­nh báº±ng 0. Khi cĂ³ phĂ­ phĂ¡t sinh, backend táº¡o báº£n ghi giao dá»‹ch trong collection `transactions`.

### Quáº£n lĂ½ quĂ¡ táº£i

Backend quáº£n lĂ½ chá»— Ä‘á»— báº±ng collection `parking_slots`. Má»—i slot cĂ³ tráº¡ng thĂ¡i `available`, `occupied`, `reserved` hoáº·c `maintenance`. Khi xe vĂ o, há»‡ thá»‘ng tĂ¬m slot `available`; náº¿u khĂ´ng cĂ³ slot trá»‘ng, backend tráº£ vá» thĂ´ng bĂ¡o bĂ£i Ä‘áº§y vĂ  ESP32 khĂ´ng má»Ÿ barrier. Dashboard hiá»ƒn thá»‹ tá»•ng sá»‘ slot, sá»‘ slot trá»‘ng, sá»‘ slot Ä‘ang sá»­ dá»¥ng vĂ  tá»· lá»‡ láº¥p Ä‘áº§y. CĂ³ thá»ƒ bá»• sung cáº£nh bĂ¡o sá»›m khi tá»· lá»‡ láº¥p Ä‘áº§y vÆ°á»£t 80% hoáº·c 90%.

### Giao diá»‡n web

Frontend dĂ¹ng HTML/CSS/JavaScript, Bootstrap, Bootstrap Icons vĂ  Chart.js. CĂ¡c mĂ n hĂ¬nh chĂ­nh gá»“m Dashboard, ÄÄƒng kĂ½ tháº», KhĂ¡ch hĂ ng, Xe, Map chá»— Ä‘á»—, GĂ³i cÆ°á»›c, Lá»‹ch sá»­ vĂ  Doanh thu. Dashboard gá»i API Ä‘á»‹nh ká»³ Ä‘á»ƒ hiá»ƒn thá»‹ sá»‘ khĂ¡ch hĂ ng, xe Ä‘ang Ä‘á»—, chá»— trá»‘ng, doanh thu hĂ´m nay, biá»ƒu Ä‘á»“ doanh thu 7 ngĂ y vĂ  tá»· lá»‡ láº¥p Ä‘áº§y.

# 3. Káº¿t quáº£

## 3.1. MĂ´i trÆ°á»ng thá»±c nghiá»‡m

| ThĂ nh pháº§n | CĂ´ng cá»¥/cáº¥u hĂ¬nh |
| --- | --- |
| Firmware | MicroPython trĂªn ESP32 |
| Backend | Python, FastAPI, Uvicorn, Motor/PyMongo |
| Database | MongoDB, database `smart_parking` |
| Frontend | HTML, CSS, JavaScript, Bootstrap, Chart.js |
| Thiáº¿t bá»‹ cá»•ng | ESP32, MFRC522, LCD I2C, servo, buzzer, HC-SR04 |
| Camera/AI | ESP32-CAM, OpenCV/YOLO/OCR náº¿u nhĂ³m triá»ƒn khai thĂªm |

## 3.2. Chá»©c nÄƒng Ä‘Ă£ triá»ƒn khai

| Chá»©c nÄƒng | Tráº¡ng thĂ¡i trong repo | MĂ´ táº£ káº¿t quáº£ |
| --- | --- | --- |
| Quáº¹t tháº» RFID | ÄĂ£ cĂ³ | ESP32 Ä‘á»c UID vĂ  gá»­i API |
| Check-in/check-out | ÄĂ£ cĂ³ | Backend táº¡o/Ä‘Ă³ng phiĂªn gá»­i xe |
| Äiá»u khiá»ƒn barrier | ÄĂ£ cĂ³ firmware | Servo má»Ÿ/Ä‘Ă³ng theo pháº£n há»“i backend |
| LCD/buzzer/LED | ÄĂ£ cĂ³ firmware | Pháº£n há»“i tráº¡ng thĂ¡i thĂ nh cĂ´ng/lá»—i |
| Quáº£n lĂ½ khĂ¡ch hĂ ng, xe, tháº» | ÄĂ£ cĂ³ | CRUD vĂ  Ä‘Äƒng kĂ½ tháº» trĂªn web |
| Quáº£n lĂ½ chá»— Ä‘á»— | ÄĂ£ cĂ³ | GĂ¡n slot, giáº£i phĂ³ng slot, hiá»ƒn thá»‹ map |
| Cáº£nh bĂ¡o quĂ¡ táº£i | CĂ³ logic ná»n | Tá»« chá»‘i xe vĂ o khi khĂ´ng cĂ²n slot; nĂªn bá»• sung cáº£nh bĂ¡o UI rĂµ hÆ¡n náº¿u demo |
| GĂ³i cÆ°á»›c/doanh thu | ÄĂ£ cĂ³ | GĂ³i ngĂ y/thĂ¡ng, giao dá»‹ch, thá»‘ng kĂª doanh thu |
| Nháº­n diá»‡n biá»ƒn sá»‘ ESP32-CAM | ChÆ°a tháº¥y trong repo | ÄÆ°a vĂ o pháº§n thiáº¿t káº¿/hÆ°á»›ng phĂ¡t triá»ƒn náº¿u chÆ°a tĂ­ch há»£p |

## 3.3. Ká»‹ch báº£n kiá»ƒm thá»­

| Ká»‹ch báº£n | CĂ¡ch kiá»ƒm thá»­ | Káº¿t quáº£ mong Ä‘á»£i |
| --- | --- | --- |
| Tháº» má»›i | QuĂ©t UID chÆ°a cĂ³ trong database | Táº¡o khĂ¡ch/xe/tháº»/phiĂªn má»›i hoáº·c pending registration |
| Tháº» cÅ© vĂ o bĂ£i | QuĂ©t UID Ä‘Ă£ Ä‘Äƒng kĂ½ vĂ  chÆ°a cĂ³ session | Táº¡o session, gĂ¡n slot, má»Ÿ barrier |
| Tháº» cÅ© ra bĂ£i | QuĂ©t UID Ä‘ang cĂ³ session | ÄĂ³ng session, tĂ­nh phĂ­, giáº£i phĂ³ng slot |
| Tháº» inactive/lost | Äá»•i status tháº» rá»“i quĂ©t | Backend tá»« chá»‘i, barrier khĂ´ng má»Ÿ |
| BĂ£i Ä‘áº§y | Äáº·t toĂ n bá»™ slot thĂ nh occupied | API tráº£ vá» bĂ£i Ä‘áº§y |
| Máº¥t Wi-Fi/backend | Táº¯t backend hoáº·c Wi-Fi | Firmware bĂ¡o lá»—i/offline, khĂ´ng máº¥t vĂ²ng láº·p chĂ­nh |
| Dashboard | Má»Ÿ web vĂ  thao tĂ¡c cĂ¡c trang | Dá»¯ liá»‡u cáº­p nháº­t Ä‘Ăºng theo database |
| ESP32-CAM/AI | Chá»¥p áº£nh biá»ƒn sá»‘ vĂ  cháº¡y nháº­n dáº¡ng | Tráº£ vá» biá»ƒn sá»‘ vĂ  Ä‘á»™ tin cáº­y náº¿u Ä‘Ă£ triá»ƒn khai |

## 3.4. Chá»‰ sá»‘ Ä‘Ă¡nh giĂ¡ nĂªn Ä‘Æ°a vĂ o bĂ¡o cĂ¡o

| TiĂªu chĂ­ | CĂ¡ch Ä‘o | Máº«u ghi káº¿t quáº£ |
| --- | --- | --- |
| Tá»· lá»‡ Ä‘á»c RFID | Sá»‘ láº§n Ä‘á»c UID Ä‘Ăºng / tá»•ng sá»‘ láº§n quĂ©t | VĂ­ dá»¥: 48/50 = 96% |
| Äá»™ trá»… API | Thá»i gian tá»« lĂºc ESP32 gá»­i request Ä‘áº¿n lĂºc nháº­n response | VĂ­ dá»¥: trung bĂ¬nh 120 ms trong LAN |
| Äá»™ á»•n Ä‘á»‹nh barrier | Sá»‘ láº§n má»Ÿ/Ä‘Ă³ng Ä‘Ăºng / tá»•ng lÆ°á»£t | VĂ­ dá»¥: 30/30 lÆ°á»£t |
| Äá»™ Ä‘Ăºng nghiá»‡p vá»¥ | Check-in/check-out Ä‘Ăºng phiĂªn | VĂ­ dá»¥: 20/20 lÆ°á»£t |
| Cáº£nh bĂ¡o quĂ¡ táº£i | Kiá»ƒm thá»­ khi háº¿t slot | API tá»« chá»‘i vĂ  dashboard bĂ¡o háº¿t chá»— |
| OCR biá»ƒn sá»‘ | Plate Exact Match | Äiá»n náº¿u Ä‘Ă£ cĂ³ AI |
| Tá»‘c Ä‘á»™ AI | Thá»i gian xá»­ lĂ½ 1 áº£nh | Äiá»n náº¿u Ä‘Ă£ cĂ³ AI |

# 4. Káº¿t luáº­n

Äá»“ Ă¡n Ä‘Ă£ xĂ¢y dá»±ng Ä‘Æ°á»£c mĂ´ hĂ¬nh bĂ£i xe thĂ´ng minh cĂ³ kháº£ nÄƒng tá»± Ä‘á»™ng ghi nháº­n lÆ°á»£t xe vĂ o/ra báº±ng tháº» RFID, Ä‘iá»u khiá»ƒn barrier báº±ng ESP32, lÆ°u dá»¯ liá»‡u táº­p trung vĂ  hiá»ƒn thá»‹ thĂ´ng tin quáº£n lĂ½ qua dashboard web. Backend FastAPI vĂ  MongoDB giĂºp há»‡ thá»‘ng cĂ³ cáº¥u trĂºc dá»¯ liá»‡u rĂµ rĂ ng, dá»… má»Ÿ rá»™ng. Giao diá»‡n web há»— trá»£ quáº£n lĂ½ khĂ¡ch hĂ ng, xe, tháº» RFID, phiĂªn gá»­i xe, sÆ¡ Ä‘á»“ chá»— Ä‘á»—, gĂ³i cÆ°á»›c vĂ  doanh thu. Há»‡ thá»‘ng Ä‘Ă£ thá»ƒ hiá»‡n Ä‘Æ°á»£c tĂ­nh IoT thĂ´ng qua káº¿t ná»‘i giá»¯a thiáº¿t bá»‹ pháº§n cá»©ng, API server vĂ  giao diá»‡n quáº£n trá»‹.

Háº¡n cháº¿ cá»§a phiĂªn báº£n hiá»‡n táº¡i lĂ  module ESP32-CAM/nháº­n diá»‡n biá»ƒn sá»‘ chÆ°a Ä‘Æ°á»£c tĂ­ch há»£p trong mĂ£ nguá»“n, cÆ¡ cháº¿ cáº£nh bĂ¡o quĂ¡ táº£i chá»§ yáº¿u dá»«ng á»Ÿ viá»‡c thá»‘ng kĂª vĂ  tá»« chá»‘i khi háº¿t chá»—, báº£o máº­t API cĂ²n Ä‘Æ¡n giáº£n vĂ  chÆ°a cĂ³ xĂ¡c thá»±c ngÆ°á»i dĂ¹ng Ä‘áº§y Ä‘á»§. Náº¿u cĂ³ thĂªm thá»i gian, nhĂ³m cĂ³ thá»ƒ bá»• sung camera chá»¥p biá»ƒn sá»‘, huáº¥n luyá»‡n mĂ´ hĂ¬nh phĂ¡t hiá»‡n biá»ƒn sá»‘, thĂªm OCR, so khá»›p biá»ƒn sá»‘ vá»›i tháº» RFID, thĂªm cáº£nh bĂ¡o qua email/Telegram, phĂ¢n quyá»n tĂ i khoáº£n quáº£n trá»‹, thanh toĂ¡n Ä‘iá»‡n tá»­ vĂ  triá»ƒn khai backend lĂªn server/cloud.

# 5. Danh má»¥c tĂ i liá»‡u tham kháº£o gá»£i Ă½

1. Espressif Systems, ESP32 Series Datasheet: https://documentation.espressif.com/esp32_datasheet_en.html
2. Espressif, ESP32 Camera Driver: https://components.espressif.com/components/espressif/esp32-camera
3. NXP Semiconductors, MFRC522 Standard performance MIFARE and NTAG frontend: https://www.nxp.com/products/rfid-nfc/nfc-hf/nfc-readers/standard-performance-mifare-and-ntag-frontend%3AMFRC52202HN1
4. MicroPython Documentation, Quick reference for ESP32: https://docs.micropython.org/en/latest/esp32/quickref.html
5. FastAPI Documentation: https://fastapi.tiangolo.com/
6. MongoDB Motor Async Driver Documentation: https://www.mongodb.com/docs/drivers/motor/
7. OpenCV Documentation, Contours: https://docs.opencv.org/3.4/d4/d73/tutorial_py_contours_begin.html
8. Ultralytics Documentation, Object Detection/YOLO: https://docs.ultralytics.com/tasks/detect/
9. PaddleOCR Documentation, OCR Pipeline: https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
