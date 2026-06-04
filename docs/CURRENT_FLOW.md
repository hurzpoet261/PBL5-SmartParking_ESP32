# Current Production Flow

This project currently uses the camera/OCR access-event flow as the only gate
operation flow.

## Main Gate Flow

```text
ESP32 RFID -> MQTT -> camera_bridge.py -> ESP32-CAM capture
           -> POST /api/v1/access-events/rfid-camera
           -> OCR + card/vehicle validation + DB write
           -> MQTT open-gate command
           -> ESP32 opens barrier
```

## Locked Legacy Endpoint

`POST /api/v1/rfid/scan` is registration/test only.

It must not be used for entry/exit demos because it does not:

- create sessions
- update parking slots
- calculate fees
- publish gate-open commands

The endpoint intentionally returns `success: false` and `open_gate: false` so
legacy HTTP firmware cannot open the barrier by mistake.

## Firmware

Use:

- `firmware/main.py`
- `firmware/esp32_config.py`
- `firmware/mfrc522.py`
- `firmware/lcd_i2c.py`

Upload `firmware/main.py` to ESP32 as `main.py`.

Do not upload `firmware/legacy_esp32_main.py` for the current flow. It is the
old HTTP firmware kept only as reference.

## Package/Fee Rule

- `per_use`: billing mode only, no package document is created.
- `daily`, `monthly`: stored package for one active vehicle.
- Exit fee is zero only when the exiting vehicle has an active, unexpired
  `daily/monthly` package.

## Relationship Validation

Registration and package creation validate:

- customer exists and is active
- vehicle exists, is active, and belongs to the customer
- RFID card UID is unique
- one vehicle has at most one active RFID card
- one vehicle has at most one active daily/monthly package at a time
