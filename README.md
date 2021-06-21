Nitro cores migen/litex wrappers
================================

This repository contains wrappers to allow to use some of the Nitro FPGA cores
in a Migen and/or LiteX environment.


Wrapped Cores
-------------

### `no2usb`: USB device core

This core is wrapped as `no2migen.litex.NitroUSB`.

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


Limitations
-----------

Some of the cores have limited FPGA architecture supports and will only work
on some FPGA target. If you need support for another, adaptation is often not
too complex (mostly IO buffers / BRAM primitives), you can open an issue
on the appropriate core tracker.


License
-------

See LICENSE.md for the licenses of the various components in this repository
