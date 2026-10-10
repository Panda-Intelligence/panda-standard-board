#ifndef PANDA_SEVEN_MM_QUALITY_BOARD_PINS_H
#define PANDA_SEVEN_MM_QUALITY_BOARD_PINS_H

/* Revision B quality floorplan only. Do not combine this header with the
 * historical board_pins.h (revision A). Native pin mappings are independently
 * checked against both the saved schematic and PCB. Target firmware/USB/SD
 * waveforms have NOT been qualified by these declarations. */
#ifdef PANDA_SEVEN_MM_BOARD_PINS_H
#error "Select one physical board revision; A and B pin maps differ"
#endif
#define PANDA7_QUALITY_REVISION_B 1
#define PANDA7B_DISPLAY_SCLK_GPIO 38
#define PANDA7B_DISPLAY_SCLK_PACKAGE_PIN 43
#define PANDA7B_I2C_SCL_GPIO 16
#define PANDA7B_I2C_SDA_GPIO 15
#define PANDA7B_SDMMC_CLK_GPIO 7
#define PANDA7B_SDMMC_CMD_GPIO 8
#define PANDA7B_SDMMC_D0_GPIO 6
#define PANDA7B_SDMMC_D1_GPIO 5
#define PANDA7B_SDMMC_D2_GPIO 10
#define PANDA7B_SDMMC_D3_GPIO 9
#define PANDA7B_HARDWARE_ARM_GPIO 2
#define PANDA7B_USB_DM_GPIO 19
#define PANDA7B_USB_DP_GPIO 20
#define PANDA7B_FLASH_MB 16
#define PANDA7B_OCTAL_PSRAM_MB 8

/* Set all SDMMC slot GPIO fields explicitly; do not use default pin locations.
 * Same for the display SPI clock and I2C bus. Host allocation follows the
 * ESP32-S3 GPIO matrix. External pullups, reset logic and reserved PSRAM pins
 * remain hardware contracts, not options to waive to obtain a boot. */
#if PANDA7B_DISPLAY_SCLK_GPIO < 38 || PANDA7B_DISPLAY_SCLK_GPIO > 48
#error "Display SCLK must stay on the reviewed revision-B GPIO"
#endif
#endif
