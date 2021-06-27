#!/usr/bin/env python3

# Copyright (c) 2019 Sean Cross <sean@xobs.io>
# Copyright (c) 2018 David Shah <dave@ds0.me>
# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2021 Sylvain Munaut <tnt@246tNt.com>
# SPDX-License-Identifier: BSD-2-Clause

import argparse
import os

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex_boards.platforms import fomu_pvt

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
        clk48 = platform.request("clk48")

        # Power On Reset
        por_count = Signal(16, reset=2**16-1)
        por_done  = Signal()
        self.comb += self.cd_por.clk.eq(ClockSignal())
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # PLL
        pll_locked = Signal()

        self.specials += Instance("SB_PLL40_2F_CORE",
            p_DIVR                  = 0,
            p_DIVF                  = 15,
            p_DIVQ                  = 4,
            p_FILTER_RANGE          = 4,
            p_FEEDBACK_PATH         = "SIMPLE",
            p_PLLOUT_SELECT_PORTA   = "GENCLK",
            p_PLLOUT_SELECT_PORTB   = "GENCLK_HALF",
            i_REFERENCECLK          = clk48,
            o_PLLOUTGLOBALA         = self.cd_usb_48.clk,
            o_PLLOUTGLOBALB         = self.cd_sys.clk,
            i_RESETB                = 1,
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
    def __init__(self, bios_flash_offset, **kwargs):
        platform = fomu_pvt.Platform()

        # Disable Integrated ROM/SRAM since too large for iCE40 and UP5K has specific SPRAM.
        kwargs["integrated_sram_size"] = 0
        kwargs["integrated_rom_size"]  = 0

        # Set CPU variant / reset address
        kwargs["cpu_variant"] = "minimal"
        kwargs["cpu_reset_address"] = self.mem_map["spiflash"] + bios_flash_offset

        # Disable auto-uart add
        kwargs["with_uart"] = False

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, int(24e6),
            ident          = "LiteX SoC on Fomu",
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
    from litex.build.dfu import DFUProg
    prog = DFUProg(vid="1209", pid="5bf0")
    bitstream  = open(f"{build_dir}/gateware/{build_name}.bin",  "rb")
    #bios       = open(f"{build_dir}/software/bios/bios.bin", "rb")
    bios       = open(f"{build_dir}/software/firmware/firmware.bin", "rb")
    image      = open(f"{build_dir}/image.bin", "wb")
    # Copy bitstream at 0x00000000
    for i in range(0x00000000, 0x0020000):
        b = bitstream.read(1)
        if not b:
            image.write(0xff.to_bytes(1, "big"))
        else:
            image.write(b)
    # Copy bios at 0x00020000
    for i in range(0x00000000, 0x00010000):
        b = bios.read(1)
        if not b:
            image.write(0xff.to_bytes(1, "big"))
        else:
            image.write(b)
    bitstream.close()
    bios.close()
    image.close()
    prog.load_bitstream(f"{build_dir}/image.bin")

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on Fomu")
    parser.add_argument("--build",             action="store_true", help="Build bitstream")
    parser.add_argument("--flash",             action="store_true", help="Flash bitstream and bios")
    parser.add_argument("--bios-flash-offset", default=0x60000,     help="BIOS offset in SPI Flash (default: 0x60000)")
    builder_args(parser)
    soc_core_args(parser)
    args = parser.parse_args()

    soc = BaseSoC(
        bios_flash_offset = args.bios_flash_offset,
        **soc_core_argdict(args)
    )
    builder = Builder(soc, **builder_argdict(args))
    soc.usb.add_gateware_dir_files(builder.gateware_dir)
    builder.add_software_package("firmware", "{}/firmware".format(os.getcwd()))
    builder.build(run=args.build)

    if args.flash:
        flash(builder.output_dir, soc.build_name, args.bios_flash_offset)

if __name__ == "__main__":
    main()
