Nitro cores Migen/LiteX wrappers
================================

This repository contains wrappers to allow to use some of the Nitro FPGA cores
in a Migen and/or LiteX environment.


Wrapped Cores
-------------

### `no2usb`: USB device core

This core is wrapped as `no2migen.litex.NitroUSB` for use as a wishbone
LiteX peripheral.

The core can be added as such (in the `__init__` of your `SoCCore`) :

```python
self.submodules.usb = NitroUSB(platform, platform.request("usb"))
self.bus.add_slave("usb", self.usb.bus, SoCRegion(size=64*kB, cached=False))
```

The `usb` resource must define the pads for `d_p`, `d_n` and `pullup`.
Clocking wise, the core works at any `sys` frequency for its interface to
the SoC but needs a `usb_48` `ClockDomain` to be defined and running at
48 MHz for the USB SIE part.

You also need to add a small work around just after constructing your `Builder`
and before calling its `build` method. This is required because of
https://github.com/enjoy-digital/litex/issues/951

```python
soc.usb.add_gateware_dir_files(builder.gateware_dir)
```

The options available for the core are :

 * `evt_fifo=True/False`: Enables or disable the event fifo which can be
   used by the driver to speed up operations slightly.

 * `irq=True/False`: Enables the `o_irq` output of the core so it can generate
   interrupt on activity rather than using polling mode in the driver.

 * `sync=True/False`: If your `sys` domain is the same as the `usb_48` domain,
   both running at the same 48 MHz clock, then some CDC circuitry can be
   omitted.


### `no2muacm`: USB CDC ACM core

#### LiteX variant

This core is wrapped as `no2migen.litex.NitroMuAcmUart` for use as a standard
LiteX UART (compatible with other UART options).

If you just want your SoC to have an UART / Console over USB and don't
want to run a USB stack yourself in your core, you can use this as an
alternative to having a raw USB device core that you must drive yourself.

To use it, you must first disable the built-in UART added by passing
`with_uart = False` to the `SoCCore.__init__` call, usually using
`kwargs["with_uart"] = False` to overwrite the default options.

And then create the UART module and add it yourself in the `__init__` of
your `SoCCore`:

```python
from no2migen.litex import NitroMuAcmUart

usb_pads = self.platform.request("usb")
self.submodules.uart = NitroMuAcmUart(platform, usb_pads)
self.add_constant("UART_POLLING")
```

The `usb` resource must define the pads for `d_p`, `d_n` and `pullup`.
Clocking wise, the core works at any `sys` frequency for its interface to
the SoC but needs a `usb_48` `ClockDomain` to be defined and running at
48 MHz for the USB SIE part.

The core also offers a `bootloader_req` that generates a pulse if the
hosts requests a reboot to bootloader using a `DFU_DETACH` request. This
should be tied to whatever logic you have to reboot your FPGA to its
bootloader (assuming there is one).

The options available for the core are :

 * `vid` / `pid`: Sets customs USB PID/VID for the core.

 * `vendor` / `product` / `serial`: Sets the corresponding string descriptors
   (length limited to 16).

 * `no_dfu_rt`: Disables the DFU runtime function of the core.

 * `sync=True/False`: If your `sys` domain is the same as the `usb_48` domain,
   both running at the same 48 MHz clock, then some CDC circuitry can be
   omitted.

#### Pure Migen variant

This core is also wrapped as `no2migen.NitroMuAcmSync`,
`no2migen.NitroMuAcmAsync` and `no2migen.NitroMuAcmBuffered`.

Theses 3 variants expose the same kind of data interface, derived from
AXI-Stream. Refer to the python docstring for the details. The `Sync` variant
is meant to run entirely in one clock domain and it must be 48 MHz. The `Async`
variant uses a `usb_48` clock domain for the USB part but all user interfacing
is done in the `sys` doman and this can be anything. The `Buffered` variant
can use either clocking strategy (depending on `sync` parameter) but it adds
some FIFO to increase efficiency.

For all variants the customizations options are the same as explained in the
LiteX variant above.


Limitations
-----------

Some of the cores have limited FPGA architecture supports and will only work
on some FPGA target. If you need support for another, adaptation is often not
too complex (mostly IO buffers / BRAM primitives), you can open an issue
on the appropriate core tracker.


License
-------

See LICENSE.md for the licenses of the various components in this repository
