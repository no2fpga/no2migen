#!/usr/bin/env python3

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from migen.genlib.fsm import *
from migen.build.generic_platform import *


import no2migen


class LoopbackTest(Module):

    def __init__(self, platform):
        self.rst = Signal()
        self.clock_domains.cd_sys    = ClockDomain()
        self.clock_domains.cd_por    = ClockDomain(reset_less=True)
        self.clock_domains.cd_usb_48 = ClockDomain()

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
        
        usb_pads = platform.request("usb")

        self.submodules.muacm = muacm = no2migen.NitroMuAcmBuffered(platform, usb_pads, fifo_depth=256)

        self.comb += [
            muacm.in_data.eq(muacm.out_data),
            muacm.in_last.eq(0),
            muacm.in_valid.eq(muacm.out_valid),
            muacm.out_ready.eq(muacm.in_ready),
            muacm.in_flush_time.eq(1),
            muacm.in_flush_now.eq(0),
        ]

usb_tnt = [
    ("usb", 0,
        Subsignal("d_p",    Pins("PMOD1B:3")),
        Subsignal("d_n",    Pins("PMOD1B:2")),
        Subsignal("pullup", Pins("PMOD1B:1")),
        IOStandard("LVCMOS33"),
    )
]

if __name__ == "__main__":
    from migen.build.generic_platform import *
    from migen.build.platforms import icebreaker
    plat = icebreaker.Platform()
    plat.add_extension(usb_tnt)
    plat.build(LoopbackTest(plat))
    plat.create_programmer().flash(0, "build/top.bin")
