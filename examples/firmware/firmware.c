#include <stdint.h>
#include <stdbool.h>

#include "console.h"
#include "tusb.h"

//--------------------------------------------------------------------+
// Device callbacks
//--------------------------------------------------------------------+

// Invoked when device is mounted
void tud_mount_cb(void)
{
}

// Invoked when device is unmounted
void tud_umount_cb(void)
{
}

// Invoked when usb bus is suspended
// remote_wakeup_en : if host allow us  to perform remote wakeup
// Within 7ms, device must draw an average of current less than 2.5 mA from bus
void tud_suspend_cb(bool remote_wakeup_en)
{
  (void) remote_wakeup_en;
}

// Invoked when usb bus is resumed
void tud_resume_cb(void)
{
}


//--------------------------------------------------------------------+
// USB CDC
//--------------------------------------------------------------------+

static void
cdc_task(void)
{
  // connected() check for DTR bit
  // Most but not all terminal client set this when making connection
  // if ( tud_cdc_connected() )
  {
    // connected and there are data available
    if ( tud_cdc_available() )
    {
      // read datas
      char buf[64];
      uint32_t count = tud_cdc_read(buf, sizeof(buf));
      (void) count;

      // Echo back
      // Note: Skip echo by commenting out write() and write_flush()
      // for throughput test e.g
      //    $ dd if=/dev/zero of=/dev/ttyACM0 count=10000
      tud_cdc_write(buf, count);
      tud_cdc_write_flush();
    }
  }
}

// Invoked when cdc when line state changed e.g connected/disconnected
void tud_cdc_line_state_cb(uint8_t itf, bool dtr, bool rts)
{
  (void) itf;
  (void) rts;

  // TODO set some indicator
  if ( dtr )
  {
    // Terminal connected
  }else
  {
    // Terminal disconnected
  }
}

// Invoked when CDC interface received data from host
void tud_cdc_rx_cb(uint8_t itf)
{
  (void) itf;
}


//--------------------------------------------------------------------+
// Main
//--------------------------------------------------------------------+



extern void dcd_edpt_debug(uint8_t rhport, uint8_t ep_addr);

void main(void)
{
	console_init();

	/* Delay to ensure the hosts detects the detach/reattach ... */
	for (int i=0; i<10000000; i++)
		asm("nop");

	puts("\n");
	puts("==========================================================\n");
	puts("\n");
	puts("Booting TinyUSB image..\n");
	puts("\n");

	tusb_init();

	int cmd;

	while (1)
	{
		/* Prompt ? */
		if (cmd >= 0)
			printf("Command> ");

		/* Poll for command */
		cmd = getchar_nowait();

		if (cmd >= 0) {
			if (cmd > 32 && cmd < 127)
				putchar(cmd);
			putchar('\r');
			putchar('\n');

			switch (cmd)
			{
			case 'S':
				dcd_edpt_debug(0, 0x81);
				dcd_edpt_debug(0, 0x02);
				dcd_edpt_debug(0, 0x82);
				break;
			case 'D':
				dcd_edpt_debug(0, 0x03);
				dcd_edpt_debug(0, 0x83);
				break;
			}
		}

		dcd_int_handler(0);	// Poll Mode
		tud_task();
		cdc_task();
	}
}
