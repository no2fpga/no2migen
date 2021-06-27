/*
 * start.S
 *
 * Startup code taken from picosoc/picorv32 and adapted for use here
 *
 * Copyright (C) 2017 Clifford Wolf <clifford@clifford.at>
 * Copyright (C) 2019 Sylvain Munaut <tnt@246tNt.com>
 *
 * Permission to use, copy, modify, and/or distribute this software for any
 * purpose with or without fee is hereby granted, provided that the above
 * copyright notice and this permission notice appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
 * WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
 * MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
 * ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
 * WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
 * ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
 * OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

#define UART_BASE 0x8200000

	.section .text.start
	.global _start
_start:

	li	a0, UART_BASE
	li	a1, 65
	sw	a1, 0(a0)

	// Init .data section from flash
	la	a0, _sidata
	la	a1, _sdata
	la	a2, _edata
	bge	a1, a2, end_init_data
loop_init_data:
	lw	a3, 0(a0)
	sw	a3, 0(a1)
	addi	a0, a0, 4
	addi	a1, a1, 4
	blt	a1, a2, loop_init_data
end_init_data:

	// Clear .bss section
	la	a0, _sbss
	la	a1, _ebss
	bge	a0, a1, end_init_bss
loop_init_bss:
	sw	zero, 0(a0)
	addi	a0, a0, 4
	blt	a0, a1, loop_init_bss
end_init_bss:

	// Set stack pointer
	la	sp, __stacktop

	li	a0, UART_BASE
	li	a1, 66
	sw	a1, 0(a0)

	// call main
	call	main

	.global	_exit
_exit:
	j	_exit


