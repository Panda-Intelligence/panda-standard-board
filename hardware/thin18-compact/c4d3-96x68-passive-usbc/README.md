# Thin18 Compact C4D-3 — passive USB-C sink

The legacy Type-C controller/LDO/comparator/buffer status chain is removed from the product netlist and PCB. R206/R207 become 5.1k Rd from CC1/CC2 to GND. USB D+/D-, VBUS, ESD and tuning remain intact. Charging status comes from SGM41513. U601 P16/P17 and ESP32 IO2 are explicitly no-connected in this D3 candidate; C4D4 will reclaim P16/P17 for the touch connector. Not a manufacturing release.
