#!/usr/bin/env python3

#
# Wrappers specifically meant for cores integrating in LiteX SoCs.
#
# Copyright (C) 2021  Sylvain Munaut <tnt@246tNt.com>
# SPDX-License-Identifier: CERN-OHL-P-2.0
#

import importlib
import math
import os
import pkg_resources

from migen import *
from migen.genlib.cdc import MultiReg, PulseSynchronizer

from litex.soc.interconnect import wishbone


__all__ = [ 'NitroUSB' ]



class NitroUSB(Module):

	def __init__(self, platform, pads, width=32, evt_fifo=False, irq=False, sync=False):

		# Exposed signals
		self.bus = wishbone.Interface(width)
		self.o_irq = Signal()
		self.o_sof = Signal()

		# Internal signals
		b_rdata_ep   = Signal(width)
		b_rdata_core = Signal(width)
		b_cyc_ep     = Signal()
		b_cyc_core   = Signal()
		b_ack_ep     = Signal()
		b_ack_core   = Signal()

		# Signals in the USB domains
		ub_addr  = Signal(12)
		ub_rdata = Signal(16)
		ub_wdata = Signal(16)
		ub_we    = Signal()
		ub_cyc   = Signal()
		ub_ack   = Signal()

		u_irq    = Signal()
		u_sof    = Signal()

		if sync:
			# Just wires
			self.comb += [
				# Bus
				ub_addr.eq(self.bus.adr[0:12]),
				ub_wdata.eq(self.bus.dat_w[0:16]),
				ub_we.eq(self.bus.we),
				ub_cyc.eq(b_cyc_core),
				b_rdata_core[0:16].eq(ub_rdata),
				b_ack_core.eq(ub_ack),

				# Aux
				self.o_irq.eq(u_irq),
				self.o_sof.eq(u_sof),
			]

		else:
			# Cross-clock domain
				# Wishbone
					# Those are stable for some time until the handshake signal
					# cross the to the other domain so we can use them as-is in 'usb_48'
			self.comb += [
				ub_addr.eq(self.bus.adr[0:12]),
				ub_wdata.eq(self.bus.dat_w[0:16]),
				ub_we.eq(self.bus.we),
			]

					# Still need to capture during ack though but it'll be
					# stable long enough to be used in 'sys'
			self.sync.usb_48 += If(ub_ack, b_rdata_core[0:16].eq(ub_rdata))

					# Handshake is more complex
			ps_req = PulseSynchronizer("sys", "usb_48")
			ps_ack = PulseSynchronizer("usb_48", "sys")
			self.submodules += [ ps_req, ps_ack ]

			hs_cyc   = Signal()
			hs_cyc_d = Signal()
			hs_ack   = Signal()
			hs_ack_d = Signal()

			self.sync.sys += [
				hs_cyc_d.eq(hs_cyc),
				hs_ack_d.eq(hs_ack),
			]

			self.sync.usb_48 += [
				ub_cyc.eq((ub_cyc | ps_req.o) & ~ub_ack),
			]

			self.comb += [
				hs_cyc.eq(b_cyc_core),
				ps_req.i.eq(hs_cyc & (~hs_cyc_d | hs_ack_d)),
				ps_ack.i.eq(ub_ack),
				hs_ack.eq(ps_ack.o),
				b_ack_core.eq(hs_ack),
			]

				# IRQ
			self.specials += MultiReg(u_irq, self.o_irq)

				# SoF pulse
			ps_sof = PulseSynchronizer("usb_48", "sys")
			self.submodules += ps_sof
			self.comb += [
				ps_sof.i.eq(u_sof),
				self.o_sof.eq(ps_sof.o),
			]

		# EP interface
		EPAW = 11 - int(math.log2(width / 8))

		ep_tx_addr_0 = Signal(EPAW)
		ep_tx_data_0 = Signal(width)
		ep_tx_we_0   = Signal()
		ep_rx_addr_0 = Signal(EPAW)
		ep_rx_data_1 = Signal(width)

		self.comb += [
			ep_tx_addr_0.eq(self.bus.adr[0:EPAW]),
			ep_tx_data_0.eq(self.bus.dat_w),
			ep_tx_we_0.eq(b_ack_ep & self.bus.we),
			ep_rx_addr_0.eq(self.bus.adr[0:EPAW]),
			b_rdata_ep.eq(ep_rx_data_1),
		]

		self.sync.sys += [
			b_ack_ep.eq(b_cyc_ep & ~b_ack_ep),
		]

		# USB Core instance
			# Add required sources
		no2usb_path  = pkg_resources.resource_filename('no2migen', 'cores/no2usb/rtl/')
		no2usb_files = pkg_resources.resource_listdir('no2migen', 'cores/no2usb/rtl/')
		no2usb_srcs  = [f for f in no2usb_files if f.endswith('.v')]

		platform.add_verilog_include_path(no2usb_path)
		platform.add_sources(no2usb_path, *no2usb_srcs)

			# Instanciate
		self.specials += Instance("usb",
			p_EPDW          = width,
			p_EVT_DEPTH     = 4 if (evt_fifo is True) else 0,
			p_IRQ           = int(irq),
			io_pad_dp       = pads.d_p,
			io_pad_dn       = pads.d_n,
			o_pad_pu        = pads.pullup,
			i_ep_tx_addr_0  = ep_tx_addr_0,
			i_ep_tx_data_0  = ep_tx_data_0,
			i_ep_tx_we_0    = ep_tx_we_0,
			i_ep_rx_addr_0  = ep_rx_addr_0,
			o_ep_rx_data_1  = ep_rx_data_1,
			i_ep_rx_re_0    = b_cyc_ep,
			i_ep_clk        = ClockSignal("sys"),
			i_wb_addr       = ub_addr,
			o_wb_rdata      = ub_rdata,
			i_wb_wdata      = ub_wdata,
			i_wb_we         = ub_we,
			i_wb_cyc        = ub_cyc,
			o_wb_ack        = ub_ack,
			o_irq           = u_irq,
			o_sof           = u_sof,
			i_clk           = ClockSignal("sys" if sync else "usb_48"),
			i_rst           = ResetSignal("sys" if sync else "usb_48"),
		)

		# Bus muxing
		self.comb += [
			b_cyc_ep.eq(self.bus.cyc & self.bus.stb & self.bus.adr[13]),
			b_cyc_core.eq(self.bus.cyc & self.bus.stb & ~self.bus.adr[13]),
			self.bus.ack.eq(b_ack_core | b_ack_ep),
			self.bus.dat_r.eq(Mux(b_ack_ep, b_rdata_ep, b_rdata_core)),
		]

		if width > 16:
			self.comb += b_rdata_core[16:width].eq(0)

	def gen_microcode(self):
		# Load the microcode compiler as module
		mod_spec = importlib.util.spec_from_file_location(
			'no2migen.no2usb_microcode',
			pkg_resources.resource_filename('no2migen', 'cores/no2usb/utils/microcode.py')
		)
		no2usb_microcode = importlib.util.module_from_spec(mod_spec)
		mod_spec.loader.exec_module(no2usb_microcode)

		# Assemble microcode and return it
		return no2usb_microcode.assemble(no2usb_microcode.mc)[0]

	def add_gateware_dir_files(self, gateware_dir):
		os.makedirs(os.path.realpath(gateware_dir), exist_ok=True)
		with open(os.path.join(gateware_dir, 'usb_trans_mc.hex'), 'w') as fh:
			for v in self.gen_microcode():
				fh.write(f'{v:04x}\n')
