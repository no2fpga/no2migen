#!/usr/bin/env python3

# Copyright (c) 2019 Sean Cross <sean@xobs.io>
# Copyright (c) 2018 David Shah <dave@ds0.me>
# Copyright (c) 2020 Piotr Esden-Tempski <piotr@esden.net>
# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Sylvain Munaut <tnt@246tNt.com>
# SPDX-License-Identifier: BSD-2-Clause

# The iCEBreaker is the first open source iCE40 FPGA development board designed for teachers and
# students: https://www.crowdsupply.com/1bitsquared/icebreaker-fpga

# This target file provides a minimal LiteX SoC for the iCEBreaker
# with a CPU, its ROM (in SPI Flash), its SRAM, and a USB Device core,
# close to the others LiteX targets.
#
# For more complete example of LiteX SoC for the iCEBreaker with
# more features and documentation can be found, refer to :
# https://github.com/icebreaker-fpga/icebreaker-litex-examples

import argparse
import os

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex_boards.platforms import icebreaker

from litex.soc.cores.ram import Up5kSPRAM
from litex.soc.cores.spi_flash import SpiFlash
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.builder import *

from no2migen.litex import NitroUSB

kB = 1024
mB = 1024*kB

# CRG ----------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform):
        self.rst = Signal()
        self.clock_domains.cd_sys    = ClockDomain()
        self.clock_domains.cd_por    = ClockDomain(reset_less=True)
        self.clock_domains.cd_usb_48 = ClockDomain()

        # # #

        # Clk/Rst
        clk12 = platform.request("clk12")
        rst_n = platform.request("user_btn_n")

        # Power On Reset
        por_count = Signal(16, reset=2**16-1)
        por_done  = Signal()
        self.comb += self.cd_por.clk.eq(ClockSignal())
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # PLL
        pll_locked = Signal()

        self.specials += Instance("SB_PLL40_2F_PAD",
            p_DIVR                  = 0,
            p_DIVF                  = 63,
            p_DIVQ                  = 4,
            p_FILTER_RANGE          = 1,
            p_FEEDBACK_PATH         = "SIMPLE",
            p_PLLOUT_SELECT_PORTA   = "GENCLK",
            p_PLLOUT_SELECT_PORTB   = "GENCLK_HALF",
            i_PACKAGEPIN            = clk12,
            o_PLLOUTGLOBALA         = self.cd_usb_48.clk,
            o_PLLOUTGLOBALB         = self.cd_sys.clk,
            i_RESETB                = rst_n,
            o_LOCK                  = pll_locked,
        )

        self.specials += [
            AsyncResetSynchronizer(self.cd_sys,    ~por_done | ~pll_locked),
            AsyncResetSynchronizer(self.cd_usb_48, ~por_done | ~pll_locked),
        ]

        platform.add_period_constraint(self.cd_sys.clk,    1e9/24e6)
        platform.add_period_constraint(self.cd_usb_48.clk, 1e9/48e6)


# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    mem_map = {**SoCCore.mem_map, **{"spiflash": 0x80000000}}
    def __init__(self, bios_flash_offset, usb_type, **kwargs):
        platform = icebreaker.Platform()
        platform.add_extension(icebreaker.break_off_pmod)

        # Disable Integrated ROM/SRAM since too large for iCE40 and UP5K has specific SPRAM.
        kwargs["integrated_sram_size"] = 0
        kwargs["integrated_rom_size"]  = 0

        # Set CPU variant / reset address
        kwargs["cpu_variant"] = "minimal"
        kwargs["cpu_reset_address"] = self.mem_map["spiflash"] + bios_flash_offset

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, int(24e6),
            ident          = "LiteX SoC on iCEBreaker",
            ident_version  = True,
            **kwargs)

        # CRG --------------------------------------------------------------------------------------
        self.submodules.crg = _CRG(platform)

        # 128KB SPRAM (used as SRAM) ---------------------------------------------------------------
        self.submodules.spram = Up5kSPRAM(size=128*kB)
        self.bus.add_slave("sram", self.spram.bus, SoCRegion(size=128*kB))

        # SPI Flash --------------------------------------------------------------------------------
        self.add_spi_flash(mode="1x", dummy_cycles=8)

        # USB -------------------------------------------------------------------------------------
        USB_TYPES = {
            'usb_pmod_1a':  icebreaker.usb_pmod_1a,
            'usb_pmod_1b':  icebreaker.usb_pmod_1b,
            'usb_pmod_2':   icebreaker.usb_pmod_2,
            'usb_tnt':      icebreaker.usb_tnt,
            'usb_kbeckman': icebreaker.usb_kbeckmann,
        }
        platform.add_extension(USB_TYPES[usb_type])
        self.submodules.usb = NitroUSB(platform, platform.request("usb"))
        self.bus.add_slave("usb", self.usb.bus, SoCRegion(size=128*kB, cached=False))

        # Add ROM linker region --------------------------------------------------------------------
        self.bus.add_region("rom", SoCRegion(
            origin = self.mem_map["spiflash"] + bios_flash_offset,
            size   = 32*kB,
            linker = True)
        )

# Flash --------------------------------------------------------------------------------------------

def flash(build_dir, build_name, bios_flash_offset):
    from litex.build.lattice.programmer import IceStormProgrammer
    prog = IceStormProgrammer()
    #prog.flash(bios_flash_offset, f"{build_dir}/software/bios/bios.bin")
    prog.flash(bios_flash_offset, f"{build_dir}/software/firmware/firmware.bin")
    prog.flash(0x00000000,        f"{build_dir}/gateware/{build_name}.bin")

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on iCEBreaker")
    parser.add_argument("--build",             action="store_true", help="Build bitstream")
    parser.add_argument("--load",              action="store_true", help="Load bitstream")
    parser.add_argument("--flash",             action="store_true", help="Flash bitstream and bios")
    parser.add_argument("--bios-flash-offset", default=0x40000,     help="BIOS offset in SPI Flash (default: 0x40000)")
    parser.add_argument("--usb-type",          default='usb_tnt',   help="USB pinout selection",
        choices=['usb_pmod_1a', 'usb_pmod_1b', 'usb_pmod_2', 'usb_tnt', 'usb_kbeckmann'])

    builder_args(parser)
    soc_core_args(parser)
    args = parser.parse_args()

    soc = BaseSoC(
        bios_flash_offset = args.bios_flash_offset,
        usb_type          = args.usb_type,
        **soc_core_argdict(args)
    )
    builder = Builder(soc, **builder_argdict(args))
    soc.usb.add_gateware_dir_files(builder.gateware_dir)
    builder.add_software_package("firmware", "{}/firmware".format(os.getcwd()))
    builder.build(run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bin"))

    if args.flash:
        flash(builder.output_dir, soc.build_name, args.bios_flash_offset)

if __name__ == "__main__":
    main()
