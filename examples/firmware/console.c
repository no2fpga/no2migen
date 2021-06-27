/*
 * console.c
 *
 * Copyright (C) 2019 Sylvain Munaut
 * SPDX-License-Identifier: MIT
 */

#include <stdint.h>

#include "mini-printf.h"
#include "console.h"

#include <generated/csr.h>
#include <base/uart.h>



static char _printf_buf[128];

void console_init(void)
{
}

int getchar(void)
{
	char c;
	while (uart_rxempty_read());
	c = uart_rxtx_read();
	uart_ev_pending_write(UART_EV_RX);
	return c;
}

int getchar_nowait(void)
{
	if (uart_rxempty_read() != 0)
		return -1;

	return getchar();
}

int putchar(int c)
{
	while (uart_txfull_read());
	uart_rxtx_write(c);
	uart_ev_pending_write(UART_EV_TX);
	return c;
}

int puts(const char *p)
{
	char c;
	int n;
	while ((c = *(p++)) != 0x00) {
		if (c == '\n')
			putchar('\r');
		putchar(c);
		n++;
	}
	return n;
}

int printf(const char *fmt, ...)
{
        va_list va;
        int l;

        va_start(va, fmt);
        l = mini_vsnprintf(_printf_buf, 128, fmt, va);
        va_end(va);

	puts(_printf_buf);

	return l;
}
