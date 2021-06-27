/*
 * The MIT License (MIT)
 *
 * Copyright (c) 2019 Ha Thach (tinyusb.org)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 *
 */

#ifndef _TUSB_CONFIG_H_
#define _TUSB_CONFIG_H_

#ifdef __cplusplus
 extern "C" {
#endif

//--------------------------------------------------------------------
// COMMON CONFIGURATION
//--------------------------------------------------------------------

// Device
#define CFG_TUSB_MCU OPT_MCU_no2usb

// RHPort number used for device
#define BOARD_DEVICE_RHPORT_NUM     0

// RHPort max operational speed
#define BOARD_DEVICE_RHPORT_SPEED   OPT_MODE_FULL_SPEED

// Device mode with rhport and speed defined by board.mk
#define CFG_TUSB_RHPORT0_MODE     (OPT_MODE_DEVICE | BOARD_DEVICE_RHPORT_SPEED)

// This example doesn't use an RTOS
#define CFG_TUSB_OS               OPT_OS_NONE

// CFG_TUSB_DEBUG is defined by compiler in DEBUG build
// #define CFG_TUSB_DEBUG           0

// Memory requirements
#define CFG_TUSB_MEM_SECTION
#define CFG_TUSB_MEM_ALIGN          __attribute__ ((aligned(4)))

//--------------------------------------------------------------------
// DEVICE CONFIGURATION
//--------------------------------------------------------------------

#define CFG_TUD_ENDPOINT0_SIZE    64

//------------- CLASS -------------//
#define CFG_TUD_CDC              1
#define CFG_TUD_MSC              1
#define CFG_TUD_HID              0
#define CFG_TUD_MIDI             0
#define CFG_TUD_VENDOR           0

// CDC FIFO size of TX and RX
#define CFG_TUD_CDC_RX_BUFSIZE   64
#define CFG_TUD_CDC_TX_BUFSIZE   64

// CDC Endpoint transfer buffer size, more is faster
#define CFG_TUD_CDC_EP_BUFSIZE   64

// MSC Buffer size of Device Mass storage
#define CFG_TUD_MSC_EP_BUFSIZE   512

#ifdef __cplusplus
 }
#endif

#endif /* _TUSB_CONFIG_H_ */
