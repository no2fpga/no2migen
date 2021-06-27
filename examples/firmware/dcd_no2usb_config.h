/*
 * dcd_no2usb_config.h
 *
 * Copyright (C) 2019-2021  Sylvain Munaut <tnt@246tNt.com>
 * SPDX-License-Identifier: MIT
 */

#pragma once

#include <generated/mem.h>

#define NO2USB_CORE_BASE	(USB_BASE)
#define NO2USB_DATA_TX_BASE	(USB_BASE + 0x8000)
#define NO2USB_DATA_RX_BASE	(USB_BASE + 0x8000)

// We don't care about SoF
#undef NO2USB_WITH_SOF

// We don't have even FIFO
#undef NO2USB_WITH_EVENT_FIFO

