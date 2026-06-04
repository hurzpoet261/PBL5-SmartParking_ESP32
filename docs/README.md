# Smart Parking Documentation

## Read First

- [CURRENT_FLOW.md](CURRENT_FLOW.md): active production flow and business rules.
- [../HUONG_DAN_CHAY.md](../HUONG_DAN_CHAY.md): how to run the current system.
- [../HUONG_DAN_SU_DUNG.md](../HUONG_DAN_SU_DUNG.md): how to use the current system.

## Current Gate Flow

The active gate flow is:

```text
ESP32 RFID -> MQTT -> camera_bridge.py -> ESP32-CAM
           -> POST /api/v1/access-events/rfid-camera
           -> Backend decision + DB write
           -> MQTT open-gate command
```

`POST /api/v1/rfid/scan` is registration/test only and must not be used for
entry/exit operation.

## Historical Documents

The older files in this folder are kept for project analysis and report history.
Some of them still describe the old HTTP firmware flow using
`/api/v1/rfid/scan`; treat those sections as legacy reference.
