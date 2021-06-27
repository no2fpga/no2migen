/*
 * console.h
 *
 * Copyright (C) 2019 Sylvain Munaut
 * SPDX-License-Identifier: MIT
 */

#pragma once

void console_init(void);

int  getchar(void);
int  getchar_nowait(void);
int  putchar(int c);
int  puts(const char *p);
int  printf(const char *fmt, ...);
