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
import tempfile

from migen import *
from migen.genlib.cdc import MultiReg, PulseSynchronizer

from litex.soc.cores.uart import UART
from litex.soc.interconnect import stream, wishbone


__all__ = [ 'NitroUSB', 'NitroMuAcmUart' ]



class NitroUSB(Module):
	"""Wrapper for the Nitro FPGA USB Core

	Interface signal are in the 'sys' clock domain.
	A 'usb_48' domain is required to run all the USB logic at 48 MHz.
	If both domains are identical, some CDC logic can be simplified and the
	'sync' argument should be set to True when creating the core.

	Attributes
    ----------

	bus : wishbone.Interface(width)
		Wishbone interface to both the CSRs and the EP buffers

	irq : Signal(), out
		IRQ level output to the CPU (assuming IRQ are enabled in the core)

	sof : Signal(), out
		Start-of-Frame pulse emitted every time a SoF packet is received
	"""

	def __init__(self, platform, pads, width=32, evt_fifo=False, irq=False, sync=False):

		# Exposed signals
		self.bus = wishbone.Interface(width)
		self.irq = Signal()
		self.sof = Signal()

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
				self.irq.eq(u_irq),
				self.sof.eq(u_sof),
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
			self.specials += MultiReg(u_irq, self.irq)

				# SoF pulse
			ps_sof = PulseSynchronizer("usb_48", "sys")
			self.submodules += ps_sof
			self.comb += [
				ps_sof.i.eq(u_sof),
				self.sof.eq(ps_sof.o),
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


class NitroMuAcmCore(Module):
	"""Wrapper for the Nitro FPGA ??ACM Core

	Attributes
    ----------

	sink : stream.Endpoint([("data", 8)])
		Stream sink to send characters to the host. The 'last' signal can
		be used to force a packet flush after a given char. The 'first'
		signal is ignored.

	source : stream.Endpoint([("data", 8)])
		Stream source providing characters sent from the host. The 'last'
		signal marks packet boundaries (although for ACM those should be
		ignored). The 'first' signal is not used and fixed to 0.

	bootloader_req : Signal(), out
		Pulse signal when a DFU_DETACH request is received, requesting a reboot
		to bootloader mode
	"""

	def __init__(self, platform, pads, **kwargs):

		self.sink   = sink   = stream.Endpoint([("data", 8)])
		self.source = source = stream.Endpoint([("data", 8)])

		self.bootloader_req = Signal()

		platform.add_source(self.gen_customized_ip(**kwargs), language='verilog')

		self.specials += Instance("muacm",
			io_usb_dp       = pads.d_p,
			io_usb_dn       = pads.d_n,
			o_usb_pu        = pads.pullup,
			i_in_data       = sink.data,
			i_in_last       = sink.last,
			i_in_valid      = sink.valid,
			o_in_ready      = sink.ready,
			i_in_flush_now  = 0,
			i_in_flush_time = 1,
			o_out_data      = source.data,
			o_out_last      = source.last,
			o_out_valid     = source.valid,
			i_out_ready     = source.ready,
			o_bootloader    = self.bootloader_req,
			i_clk           = ClockSignal(),
			i_rst           = ResetSignal()
		)

	def gen_customized_ip(self, **kwargs):
		# Load the customizer as module
		mod_spec = importlib.util.spec_from_file_location(
			'no2migen.no2muacm_customize',
			pkg_resources.resource_filename('no2migen', 'cores/no2muacm-bin/muacm_customize.py')
		)
		no2muacm_customize = importlib.util.module_from_spec(mod_spec)
		mod_spec.loader.exec_module(no2muacm_customize)

		# Load source
		sf = no2muacm_customize.MuAcmPatcher()
		sf.load(pkg_resources.resource_filename('no2migen', 'cores/no2muacm-bin/muacm.v'))

		# Apply requested customization
		if kwargs.get('vid') is not None:
			sf.set_vid(kwargs['vid'])

		if kwargs.get('pid') is not None:
			sf.set_pid(kwargs['pid'])

		if kwargs.get('vendor') is not None:
			sf.set_vendor(kwargs['vendor'])

		if kwargs.get('product') is not None:
			sf.set_product(kwargs['product'])

		if kwargs.get('serial') is not None:
			sf.set_serial(kwargs['serial'])

		if bool(kwargs.get('no_dfu_rt')) is True:
			sf.disable_dfu_rt()

		# Save to temporary file
		self.ip_file = tempfile.NamedTemporaryFile(suffix='.v')
		sf.save(self.ip_file.name)

		return self.ip_file.name


class NitroMuAcmXClk(Module):
	"""Lightweight clock crossing for the data interface of NitroMuAcmCore

	Use ClockDomainsRenamer to assign to the right domains.

	Attributes
    ----------

	sink : stream.Endpoint([("data", 8)])
		Stream sink in the 'sink' clock domain

	source : stream.Endpoint([("data", 8)])
		Stream source in the 'source' clock domain
	"""

	def __init__(self):
		# Endpoints and associated domains
		self.sink   = sink   = stream.Endpoint([("data", 8)])
		self.source = source = stream.Endpoint([("data", 8)])

		# Signals
		send_snk      = Signal()
		send_sync_src = Signal(2)

		ack_src       = Signal()
		ack_sync_snk  = Signal(2)

		# Data is straight across
		self.comb += [
			source.data.eq  (sink.data),
			source.first.eq (sink.first),
			source.last.eq  (sink.last),
		]

		# Handshaking
		self.sync.sink += [
			send_snk.eq( (send_snk | (sink.valid & ~sink.ready) ) & ~ack_sync_snk[0] ),
			ack_sync_snk[1].eq( ack_sync_snk[0] ),
			ack_sync_snk[0].eq( ack_src ),
			sink.ready.eq( ack_sync_snk[0] & ~ack_sync_snk[1] ),
		]

		self.sync.source += [
			send_sync_src[1].eq( send_sync_src[0] ),
			send_sync_src[0].eq( send_snk ),
			source.valid.eq( (source.valid & ~source.ready) | (send_sync_src[0] & ~send_sync_src[1]) ),
			ack_src.eq( (ack_src & send_sync_src[0]) | (source.valid & source.ready) ),
		]


class NitroMuAcmUart(UART):
	"""
	UART core compatible with the standard LiteX UART interface and that uses
	the Nitro FPGA no2muacm core to provide uart of USB connection.

	Attributes
    ----------

    In addition to the standard "Uart" interface signals:

	bootloader_req : Signal(), out
		Pulse signal when a DFU_DETACH request is received, requesting a reboot
		to bootloader mode
	"""

	def __init__(self, platform, pads, sync=False, **kwargs):
		assert kwargs.get("phy", None) == None
		ckw = dict([(k,kwargs.pop(k)) for k in ['vid', 'pid', 'vendor', 'product', 'serial', 'no_dfu_rt'] if k in kwargs])
		UART.__init__(self, **kwargs)

		self.bootloader_req = Signal()

		if sync:
			# Synchronous case
			self.submodules.muacm = NitroMuAcmCore(platform, pads, **ckw)

			self.comb += self.muacm.source.connect(self.sink)
			self.comb += self.source.connect(self.muacm.sink)
			self.comb += self.bootloader_req.eq(self.muacm.bootloader_req)

		else:
			# Async case
			self.submodules.x_rx = x_rx = ClockDomainsRenamer({"sink": "usb_48", "source": "sys"   })(NitroMuAcmXClk())
			self.submodules.x_tx = x_tx = ClockDomainsRenamer({"sink": "sys",    "source": "usb_48"})(NitroMuAcmXClk())

			self.comb += x_rx.source.connect(self.sink)
			self.comb += self.source.connect(x_tx.sink)

			self.submodules.muacm = ClockDomainsRenamer('usb_48')(NitroMuAcmCore(platform, pads, **ckw))

			self.comb += self.muacm.source.connect(x_rx.sink)
			self.comb += x_tx.source.connect(self.muacm.sink)

			boot_req_xclk = PulseSynchronizer("usb_48", "sys")
			self.submodules += boot_req_xclk
			self.comb += [
				boot_req_xclk.i.eq(self.muacm.bootloader_req),
				self.bootloader_req.eq(boot_req_xclk.o),
			]
