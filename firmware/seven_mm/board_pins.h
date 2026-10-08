#ifndef PANDA_SEVEN_MM_BOARD_PINS_H
#define PANDA_SEVEN_MM_BOARD_PINS_H

/* Native <=7mm board contract, NOT the historical Split-C1.
 * Use PANDA7_DISPLAY_SCLK_GPIO for spi_bus_config_t.sclk_io_num when integrating
 * the actual ESP-IDF display driver. GPIO38 no longer drives HOST_SCLK.
 * This header is not proof of target-firmware or clock-waveform qualification.
 */
#define PANDA7_DISPLAY_SCLK_GPIO 21
#define PANDA7_DISPLAY_SCLK_PACKAGE_PIN 27
#define PANDA7_DISPLAY_SCLK_OLD_GPIO 38
#define PANDA7_HARDWARE_ARM_GPIO 2
#define PANDA7_USB_DM_GPIO 19
#define PANDA7_USB_DP_GPIO 20

#if PANDA7_DISPLAY_SCLK_GPIO == PANDA7_HARDWARE_ARM_GPIO || \
    PANDA7_DISPLAY_SCLK_GPIO == PANDA7_USB_DM_GPIO || \
    PANDA7_DISPLAY_SCLK_GPIO == PANDA7_USB_DP_GPIO
#error "Display clock must not consume hardware inhibit or USB pins"
#endif
#if PANDA7_DISPLAY_SCLK_GPIO >= 26 && PANDA7_DISPLAY_SCLK_GPIO <= 37
#error "Display clock must not consume SPI flash or octal PSRAM pins"
#endif
#endif
